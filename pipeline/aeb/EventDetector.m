classdef EventDetector
    properties
        pathToMat                 % original working directory
        pathToMatChunks           % destination folder for PostProcessing
        
        % Parameters for event extraction
        PRE_TIME = seconds(4)     % time before event (duration)
        POST_TIME = seconds(3)    % time after event (duration)
    end
    
    methods
        %% Constructor
        function obj = EventDetector(inputHandler)
            % Constructor: accepts an InputHandler instance
            % Parameters PRE_TIME and POST_TIME are set to defaults
            
            if nargin < 1
                error('InputHandler instance required for initialization.');
            end
            
            % Validate input is an InputHandler instance
            if ~isa(inputHandler, 'InputHandler')
                error('Input argument must be an instance of InputHandler.');
            end
            
            % Set paths using InputHandler's pathToRawData
            obj.pathToMat       = inputHandler.pathToRawData;
            obj.pathToMatChunks = fullfile(obj.pathToMat, 'PostProcessing');
            
            % Create PostProcessing directory if it doesn't exist
            if ~exist(obj.pathToMatChunks, 'dir')
                mkdir(obj.pathToMatChunks);
            end
            
            % Set default parameters (already set as property defaults, but explicit for clarity)
            obj.PRE_TIME  = seconds(4);
            obj.POST_TIME = seconds(3);
        end % constructor
        
        %% Main function to process all .mat files
        % Expects each .mat file to contain a variable 'signalMat'  
        % which is a timetable with required signals
        % Calls detectEvents and extractAEBEvents   
        % Saves extracted chunks to PostProcessing folder
        % Each chunk is saved as <original_filename>_<event_index>.mat
        function processAllFiles(obj)
            
            cd(obj.pathToMat);
            files = dir('*.mat');
            N = length(files);

            for i = 1:N
                filePath = fullfile(files(i).folder, files(i).name);
                [~, name, ~] = fileparts(filePath);
                % Load the .mat file
                matFile = load(filePath, 'signalMat');
               
                signalMat = matFile.signalMat;

                % Force every field into a column vector
                fields = fieldnames(signalMat);
                for f = 1:numel(fields)
                    signalMat.(fields{f}) = signalMat.(fields{f})(:);
                end


                % Process this file
                obj.processSingleFileInternally(signalMat, name);
            end
            cd(obj.pathToMat);
        end
        
        %% Process a single file
        function processSingleFileInternally(obj, signalMat, name)
            % Run event detection
            [locateStartTime, locateEndTime] = obj.detectEvents(signalMat);

            % Extract AEB chunks
            obj.extractAEBEvents(signalMat, locateStartTime, locateEndTime, name);
        end
        
        %% Detect start and end times of AEB events
        function [locateStartTime, locateEndTime] = detectEvents(~, signalMat)
            modeChange      = diff(signalMat.aebTargetDecel);
            locateStart     = find(diff(modeChange < -30));
            locateStartReq  = signalMat.aebTargetDecel(locateStart + 1, 1) < -5.9;
            locateStartTime = signalMat.time(locateStart, 1) .* locateStartReq;
            nonZeroTimes    = nonzeros(locateStartTime);
            if isempty(nonZeroTimes)
                locateStartTime = duration.empty;
            else
                locateStartTime = seconds(nonZeroTimes);
            end
            
            locateEnd       = find(modeChange > 20);
            locateEndStat   = signalMat.aebTargetDecel(locateEnd + 1, 1) > 20;
            locateEndTime   = signalMat.time(locateEnd, 1) .* locateEndStat;
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
        
        %% Extract AEB events (-PRE_TIME to +POST_TIME) and save chunks
        function extractAEBEvents(obj, signalMat, locateStartTime, locateEndTime, name)
            loopRun = length(locateStartTime);
            fields  = fieldnames(signalMat);
            
            % Validate field sizes
            expectedRows = size(signalMat.time, 1);
            for f = 1:length(fields)
                if size(signalMat.(fields{f}), 1) ~= expectedRows
                    error('Field %s has %d rows, expected %d', fields{f}, size(signalMat.(fields{f}), 1), expectedRows);
                end
            end
            
            for j = 1:loopRun
                % Convert startT to numeric seconds
                startT          = locateStartTime(j) - obj.PRE_TIME;
                startT_seconds  = seconds(startT);
                [~, start]      = utils.findDuration(signalMat.time, startT_seconds);

                % Compute startNext
                if j + 1 <= loopRun
                    startNextT          = locateStartTime(j + 1) - obj.PRE_TIME;
                    startNextT_seconds  = seconds(startNextT);
                    [~, startNext]      = utils.findDuration(signalMat.time, startNextT_seconds);
                else
                    startNext = length(signalMat.time);
                end

                % Initialize stop
                stop = 0;
                n = 0;

                % Try to find a valid end time
                if j + n <= length(locateEndTime)
                    while stop < start && j + n <= length(locateEndTime)
                        stopT = locateEndTime(j + n) + obj.POST_TIME;
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
                    stopT         = locateStartTime(j) + obj.POST_TIME;
                    stopT_seconds = seconds(stopT);
                    [~, stop]     = utils.findDuration(signalMat.time, stopT_seconds);
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

                    % Save directly into pathToMatChunks, overwrite if exists
                    extractFileName = fullfile(obj.pathToMatChunks, sprintf('%s_%d.mat', name, j));
                    try
                        save(extractFileName, 'signalMatChunk');
                    catch e
                        error('Error saving %s: %s', extractFileName, e.message);
                    end
                end

            end % for j = 1:loopRun
        end % extractAEBEvents
    end % methods
end % classdef
