classdef InputHandler
    properties
        % Config file reference
        jsonConfigPath      % Path to JSON config file

        % Data input
        RawDataPath         % Path to raw data folder - *.mf4, set during processing

        % Mirrored Config properties
        Signals
        Graphs
        LineColors
        Calibratables
        signalMapExcel

        signalPlotSpecPath
        signalPlotSpecName
        calibrationFilePath
        calibrationFileName
    end

    methods
        function obj = InputHandler(config)
            % Constructor: accepts a Config object
            obj.jsonConfigPath      = config.jsonConfigPath;

            % Mirror Config properties
            obj.Signals             = config.Signals;
            obj.Graphs              = config.Graphs;
            obj.LineColors          = config.LineColors;
            obj.Calibratables       = config.Calibratables;
            obj.signalMapExcel      = config.signalMapExcel;

            obj.signalPlotSpecPath  = config.signalPlotSpecPath;
            obj.signalPlotSpecName  = config.signalPlotSpecName;
            obj.calibrationFilePath = config.calibrationFilePath;
            obj.calibrationFileName = config.calibrationFileName;
        end
    end

        function processedData = processMF4Files(obj)
            % Process MF4 files: extract specified signals, save to MAT, and return processed data
            curFolder = pwd;
            
            % Prompt user to select folder with MF4 files
            seldatapath = uigetdir(curFolder, 'Select folder containing MF4 files');
            if seldatapath == 0
                fprintf('No folder selected. Operation cancelled.\n');
                processedData = {};
                return;
            end

            % Set RawDataPath to the selected folder
            obj.RawDataPath = seldatapath;

            % Verify if folder contains MF4 files
            files = dir(fullfile(seldatapath, '*.mf4'));
            if isempty(files)
                fprintf('No MF4 files found in selected folder: %s\n', seldatapath);
                cd(curFolder);
                processedData = {};
                return;
            end

            % Get signals to extract from Config
            map = obj.Config.Signals; 
            mapFile = fullfile(obj.jsonConfigPath, ); % Use JSON config path for mapping

            if isempty(map)
                fprintf('No signals specified in Config for extraction.\n');
                cd(curFolder);
                processedData = {};
                return;
            end

            % Initialize cell array to store processed data
            processedData = cell(1, length(files));
            N = length(files);
            fprintf('Found %d MF4 files to process...\n', N);

            % Process each MF4 file
            cd(seldatapath);
            for i = 1:N
                fullPath = fullfile(files(i).folder, files(i).name);
                [~, name, ~] = fileparts(fullPath);
                
                try
                    % Call internal method to process MF4 file
                    datVars = obj.processMF4FileInternally(fullPath, mapFile, 0.01); % Resample to 100 Hz

                    % Save to .mat file in the same folder as MF4 files
                    matFileName = fullfile(seldatapath, [name '.mat']);
                    save(matFileName, 'datVars');
                    fprintf('Processed: %s, saved to %s\n', files(i).name, matFileName);

                    % Store processed data
                    processedData{i} = datVars;
                catch err
                    fprintf('Error processing %s: %s\n', files(i).name, err.message);
                    processedData{i} = [];
                end
            end

            cd(curFolder);
            fprintf('✅ Processed %d MF4 files and saved to %s\n', N, seldatapath);
        end
    end

    methods (Access = private)
        function datVars = processMF4FileInternally(~, filePath, mapFile, resampleRate)
            % Use Docker + Python to process MF4 file with selected signals
            %
            % Inputs:
            %   filePath - Path to the input MF4 file (e.g., 'rawdata/roadcast_debug_converted.mf4')
            %   map - Struct with fields A2LName, TactName, and Raster 
            %   resampleRate - Resampling interval in seconds (e.g., 0.01 for 100 Hz)
            %
            % Outputs:
            %   datVars - Data loaded from the generated .mat file

            % Validate inputs
            if nargin < 4
                resampleRate = 0.01; % Default to 10ms (100 Hz), adjust as needed
            end
            validateattributes(resampleRate, {'numeric'}, {'positive', 'scalar'}, ...
                'processMF4FileInternally', 'resampleRate');

            % Extract folder and base name from filePath
            [folder, baseName, ~] = fileparts(filePath);
            matFullPath = fullfile(folder, [baseName '.mat']);

            disp('before docker run');

            % Build Docker command
            dockerBin = '/usr/local/bin/docker';
            projectRoot = fileparts(fileparts(filePath)); % Go up from rawdata to project root

            dockerCmd = sprintf([ ...
                '%s run --rm -v "%s":/data mdf-python:latest ' ...
                'python3 /data/utils/mdf2mat.py "/data/rawdata/%s.mf4" "/data/rawdata/%s.mat" %s %s' ...
            ], dockerBin, projectRoot, baseName, baseName, resampleRate, mapFile);

            % Run Docker
            status = system(dockerCmd);

            disp('after docker run');

            if status ~= 0
                error('Docker failed to process %s', filePath);
            end

            % Load the generated .mat file
            loaded = load(matFullPath);

            % Expect "data" variable from Python
            if isfield(loaded, 'data')
                datVars = loaded.data;
            else
                error('MAT file did not contain expected variable "data".');
            end
        end % processMF4FileInternally
    end % methods
end