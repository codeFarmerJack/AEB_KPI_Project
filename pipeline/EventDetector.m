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
            mode = int8(signalMat.DADCAxLmtIT4);
            modeChange = diff(mode);

            % Transition 5 -> 8 (start of patial braking or full braking)
            locateStart = find(diff(modeChange < -30));
            locateStartReq = signalMat.DADCAxLmtIT4(locateStart + 1, 1) < -5.9;
            locateStartTime = signalMat.Time(locateStart, 1) .* locateStartReq;
            locateStartTime = seconds(nonzeros(seconds(locateStartTime)));

            % Transition 8 -> 5 (end of AEB intervention)
            locateEnd = find(modeChange > 20);
            locateEndStat = signalMat.DADCAxLmtIT4(locateEnd + 1, 1) > 20;
            locateEndTime = signalMat.Time(locateEnd, 1) .* locateEndStat;
            locateEndTime = seconds(nonzeros(seconds(locateEndTime)));
        end
        
        %% Extract AEB events (-preTime to +postTime) and save chunks
        function extractAEBEvents(obj, signalMat, locateStartTime, locateEndTime, name)
            loopRun = length(locateStartTime);
            n = 0;
            stop = 0;

            for j = 1:loopRun
                startT = locateStartTime(j) - obj.preTime;
                [~, start] = utils.findDuration(signalMat.Time, startT);

                if j + 1 <= loopRun
                    [~, startNext] = utils.findDuration(signalMat.Time, locateStartTime(j + 1) - obj.preTime);
                else
                    startNext = length(signalMat.Time);
                end

                if j + n <= length(locateEndTime)
                    while stop < start
                        stopT = locateEndTime(j + n) + obj.postTime;
                        [~, stop] = utils.findDuration(signalMat.Time, stopT);

                        if stop < start
                            n = n + 1;
                        end

                        if j + n > length(locateEndTime) || stop > startNext || ...
                           (stopT - startT - obj.preTime - obj.postTime) > seconds(30)
                            start = 1;
                            stop = 1;
                        end
                    end
                end

                if stop > start
                    signalMatChunk = signalMat(start:stop, :);
                    extractFileName = fullfile(obj.destFolder, 'PostProcessing', sprintf('%s_%d.mat', name, j));
                    save(extractFileName, 'signalMatChunk');
                end
            end
        end
    end
end
