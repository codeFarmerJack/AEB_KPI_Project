classdef InputHandler
    properties
        Config          % Instance of Config class
        RawDataPath     % Path to raw data folder - *.mf4, set during processing
    end

    methods
        function obj = InputHandler(config)
            % Constructor: accepts a Config object
            obj.Config = config;
        end

        function visConfig = loadVisualizationConfig(obj)
            % Load visualization configuration from Config instance
            visConfig.Graphs = obj.Config.Graphs;               % All the graphs to be plotted
            visConfig.LineColors = obj.Config.LineColors;       % Line colors of these graphs
            visConfig.Calibratables = obj.Config.Calibratables; % struct of calibratables 
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
            if isempty(map)
                fprintf('No signals specified in Config for extraction.\n');
                cd(curFolder);
                processedData = {};
                return;
            end

            disp('map:');
            disp(map);

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
                    datVars = obj.processMF4FileInternally(fullPath, map);

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
        function datVars = processMF4FileInternally(~, filePath, map, resample_rate)
            % Use Docker + Python to process MF4 file with selected signals
            %
            % Inputs:
            %   filePath - Path to the input MF4 file (e.g., 'rawdata/roadcast_debug_converted.mf4')
            %   map - Struct or containers.Map with signal names as fields
            %   resample_rate - Resampling interval in seconds (e.g., 0.01 for 100 Hz)
            %
            % Outputs:
            %   datVars - Data loaded from the generated .mat file

            % Validate inputs
            if nargin < 4
                resample_rate = 0.01; % Default to 10ms (100 Hz), adjust as needed
            end
            validateattributes(resample_rate, {'numeric'}, {'positive', 'scalar'}, ...
                'processMF4FileInternally', 'resample_rate');

            % Extract folder and base name from filePath
            [folder, baseName, ~] = fileparts(filePath);
            matFullPath = fullfile(folder, [baseName '.mat']);

            % Convert signal map (Config.Signals) into a list
            signalNames = fieldnames(map); % Assuming map is a struct or containers.Map
            signalArgs = strjoin(signalNames, ' ');
            
            % Debug: Display signalNames and signalArgs
            disp('signalNames:');
            disp(signalNames);
            disp('signalArgs:');
            disp(signalArgs);

            % Build Docker command
            dockerBin = '/usr/local/bin/docker';
            projectRoot = fileparts(fileparts(filePath)); % Go up from rawdata to project root

            dockerCmd = sprintf([ ...
                '%s run --rm -v "%s":/data mdf-python:latest ' ...
                'python3 /data/utils/mdf2mat.py "/data/rawdata/%s.mf4" "/data/rawdata/%s.mat" %s %s' ...
            ], dockerBin, projectRoot, baseName, baseName, num2str(resample_rate), signalArgs);

            % Run Docker
            status = system(dockerCmd);

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