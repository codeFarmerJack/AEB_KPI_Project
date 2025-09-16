classdef EventDetector
    properties
        currFolder   % original working directory
        destFolder   % destination folder for PostProcessing
        preTime      % time before event (duration)
        postTime     % time after event (duration)
    end
    
    methods
        %% Constructor
        function obj = EventDetector(destFolder, preTime, postTime)
            if nargin < 1
                obj.currFolder = pwd;
                seldatapath = uigetdir(obj.currFolder, 'Select folder with *.mat files');
                obj.destFolder = seldatapath;
            else
                obj.currFolder = pwd;
                obj.destFolder = destFolder;
            end

            if nargin < 2, preTime = seconds(4); end
            if nargin < 3, postTime = seconds(3); end
            obj.preTime = preTime;
            obj.postTime = postTime;

            % Ensure PostProcessing directory exists
            if ~exist(fullfile(obj.destFolder, 'PostProcessing'), 'dir')
                mkdir(fullfile(obj.destFolder, 'PostProcessing'));
            end
        end
        
        %% Main function to process all .mat files
        % Expects each .mat file to contain a variable 'signalMat'  
        % which is a timetable with required signals
        % Calls detectEvents and extractAEBEvents   
        % Saves extracted chunks to PostProcessing folder
        % Each chunk is saved as <original_filename>_<event_index>.mat
        function processAllFiles(obj)
            cd(obj.destFolder);
            files = dir('*.mat');
            N = length(files);

            for i = 1:N
                filePath = fullfile(files(i).folder, files(i).name);
                [~, name, ~] = fileparts(filePath);
                
                % Load the mat file (expects variable signalMat inside)
                load(filePath, "signalMat");

                % Process this file
                obj.processFile(signalMat, name);
            end
            cd(obj.currFolder);
        end
        
        %% Process a single file
        function processFile(obj, signalMat, name)
            % Run event detection
            [locateStartTime, locateEndTime] = obj.detectEvents(signalMat);

            % Extract AEB chunks
            obj.extractAEBEvents(signalMat, locateStartTime, locateEndTime, name);
        end
        
        %% Detect start and end times of AEB events
        function [locateStartTime, locateEndTime] = detectEvents(~, signalMat)
            mode = int8(signalMat.aebTargetDecel);
            modeChange = diff(mode);
            locateStart = find(diff(modeChange < -30));
            locateStartReq = signalMat.aebTargetDecel(locateStart + 1, 1) < -5.9;
            locateStartTime = signalMat.time(locateStart, 1) .* locateStartReq;
            nonZeroTimes = nonzeros(locateStartTime);
            if isempty(nonZeroTimes)
                locateStartTime = duration.empty;
            else
                locateStartTime = seconds(nonZeroTimes);
            end
            
            locateEnd = find(modeChange > 20);
            locateEndStat = signalMat.aebTargetDecel(locateEnd + 1, 1) > 20;
            locateEndTime = signalMat.time(locateEnd, 1) .* locateEndStat;
            nonZeroEndTimes = nonzeros(locateEndTime);
            if isempty(nonZeroEndTimes)
                if ~isempty(locateStartTime)
                    locateEndTime = locateStartTime + seconds(7);
                else
                    locateEndTime = duration.empty;
                end
            else
                locateEndTime = seconds(nonZeroEndTimes);
            end
        end % detectEvents
        
        %% Extract AEB events (-preTime to +postTime) and save chunks
        function extractAEBEvents(obj, signalMat, locateStartTime, locateEndTime, name)
            loopRun = length(locateStartTime);
            fields = fieldnames(signalMat);
            
            % Validate field sizes
            expectedRows = size(signalMat.time, 1);
            for f = 1:length(fields)
                if size(signalMat.(fields{f}), 1) ~= expectedRows
                    error('Field %s has %d rows, expected %d', fields{f}, size(signalMat.(fields{f}), 1), expectedRows);
                end
            end
            
            for j = 1:loopRun
                % Convert startT to numeric seconds
                startT = locateStartTime(j) - obj.preTime;
                startT_seconds = seconds(startT);
                [~, start] = utils.findDuration(signalMat.time, startT_seconds);

                % Compute startNext
                if j + 1 <= loopRun
                    startNextT = locateStartTime(j + 1) - obj.preTime;
                    startNextT_seconds = seconds(startNextT);
                    [~, startNext] = utils.findDuration(signalMat.time, startNextT_seconds);
                else
                    startNext = length(signalMat.time);
                end

                % Initialize stop
                stop = 0;
                n = 0;

                % Try to find a valid end time
                if j + n <= length(locateEndTime)
                    while stop < start && j + n <= length(locateEndTime)
                        stopT = locateEndTime(j + n) + obj.postTime;
                        stopT_seconds = seconds(stopT);
                        [~, stop] = utils.findDuration(signalMat.time, stopT_seconds);
                        if stop < start || stop > startNext
                            n = n + 1;
                        else
                            break;
                        end
                    end
                end

                % Fallback if no valid end time found
                if stop < start || j + n > length(locateEndTime)
                    stopT = locateStartTime(j) + obj.postTime;
                    stopT_seconds = seconds(stopT);
                    [~, stop] = utils.findDuration(signalMat.time, stopT_seconds);
                end

                % Ensure stop doesn't exceed signal length
                stop = min(stop, length(signalMat.time));

                if stop > start
                    % Create signalMatChunk as a struct
                    signalMatChunk = struct();
                    for f = 1:length(fields)
                        try
                            signalMatChunk.(fields{f}) = signalMat.(fields{f})(start:stop);
                        catch e
                            error('Error indexing field %s: %s', fields{f}, e.message);
                        end
                    end
                    extractFileName = fullfile(obj.destFolder, 'PostProcessing', sprintf('%s_%d.mat', name, j));
                    try
                        save(extractFileName, 'signalMatChunk');
                    catch e
                        error('Error saving %s: %s', extractFileName, e.message);
                    end
                end
            end
        end % extractAEBEvents
    end % methods
end
