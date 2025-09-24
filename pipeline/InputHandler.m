classdef InputHandler < handle
    % InputHandler: Handles input configuration and processing of MF4 files
    
    properties
        jsonConfigPath      % Path to JSON config file
        pathToRawData       % Path to raw data folder - *.mf4, set in constructor
        % Mirrored Config properties
        signalMap
        graphSpec           % Table from sheet 'graphSpec'
        lineColors          % Table from sheet 'lineColors'
        % Additional properties for convenience
        signalPlotSpecPath
        signalPlotSpecName
    end

    methods
        function obj = InputHandler(config)
            % Constructor: accepts a Config object and sets pathToRawData
            if nargin < 1
                error('Configuration object is required for initialization.');
            end
            
            % Validate input is a Config instance
            if ~isa(config, 'Config')
                error('Input argument must be an instance of Config.');
            end
            
            % Mirror Config properties
            obj.jsonConfigPath      = config.jsonConfigPath;
            obj.graphSpec           = config.graphSpec;
            obj.lineColors          = config.lineColors;
            obj.signalMap           = config.signalMap;
            obj.signalPlotSpecPath  = config.signalPlotSpecPath;
            obj.signalPlotSpecName  = config.signalPlotSpecName;

            % Prompt user to select folder with MF4 files
            curFolder = pwd;
            pathToRawData = uigetdir(curFolder, 'Select folder containing MF4 files');
            if pathToRawData == 0
                error('No folder selected. Operation cancelled.');
            end

            % Set pathToRawData to the selected folder
            obj.pathToRawData = pathToRawData;

            % Verify if folder contains MF4 files
            files = dir(fullfile(obj.pathToRawData, '*.mf4'));
            if isempty(files)
                error('No MF4 files found in selected folder: %s', obj.pathToRawData);
            end

            % Verify if folder contains MF4 files
            files = dir(fullfile(obj.pathToRawData, '*.mf4'));
            if isempty(files)
                error('No MF4 files found in folder: %s', obj.pathToRawData);
            end
        end

        function processedData = processMF4Files(obj)
            % Process MF4 files: extract specified signals, save to MAT, and return processed data
            curFolder = pwd;
            
            % Use pre-set pathToRawData
            pathToRawData = obj.pathToRawData;

            % Verify if folder contains MF4 files
            files = dir(fullfile(pathToRawData, '*.mf4'));
            if isempty(files)
                fprintf('No MF4 files found in selected folder: %s\n', pathToRawData);
                cd(curFolder);
                processedData = {};
                return;
            end

            % Initialize cell array to store processed data
            processedData = cell(1, length(files));
            N = length(files);
            fprintf('    Found %d MF4 file(s) to process...\n', N);

            % Process each MF4 file
            cd(pathToRawData);
            for i = 1:N
                fullPath = fullfile(files(i).folder, files(i).name);
                [~, name, ~] = fileparts(fullPath);
                
                try
                    % Call internal method to process MF4 file, passing signalMap as table
                    signalMat = obj.processMF4FileInternally(fullPath, obj.signalMap, 0.01); % Resample to 100 Hz

                    % Save to .mat file in the same folder as MF4 files
                    matFileName = fullfile(pathToRawData, [name '.mat']);
                    save(matFileName, 'signalMat');
                    % fprintf('Processed: %s, saved to %s\n', files(i).name, matFileName);

                    % Store processed data
                    processedData{i} = signalMat;
                catch err
                    fprintf('Error processing %s: %s\n', files(i).name, err.message);
                    processedData{i} = [];
                end
            end

            cd(curFolder);
        end
    end

    methods (Access = private)
        function signalMats = processMF4FileInternally(~, filePath, signalMap, resampleRate)
            % Process MF4 file with Docker + Python
            %
            % Inputs:
            %   filePath     - Full path to the .mf4 file
            %   signalMap    - Table containing signal mapping data
            %   resampleRate - Resampling interval in seconds (e.g., 0.01 for 100 Hz)
            %
            % Outputs:
            %   signalMats - Data loaded from the generated .mat file

            if nargin < 3
                error('Usage: processMF4FileInternally(filePath, signalMap, resampleRate)');
            end
            if nargin < 4
                resampleRate = 0.01; % Default 10 ms
            end
            validateattributes(resampleRate, {'numeric'}, {'positive','scalar'}, ...
                'processMF4FileInternally', 'resampleRate');
            validateattributes(signalMap, {'table'}, {}, ...
                'processMF4FileInternally', 'signalMap');

            % Verify the .mf4 file exists
            if ~isfile(filePath)
                error('MF4 file not found: %s', filePath);
            end

            % Extract folder and base name
            [folder, baseName, ~] = fileparts(filePath);
            matFullPath = fullfile(folder, [baseName '.mat']);

            % Save signalMap table as a temporary CSV file
            tempCsvPath = fullfile(folder, 'tempSignalMap.csv');
            try
                writetable(signalMap, tempCsvPath);
            catch err
                error('Failed to write signalMap to temporary CSV: %s', err.message);
            end

            % Build Docker command
            dockerBin   = '/usr/local/bin/docker';
            projectRoot = fileparts(folder); % Go up from rawdata to project root

            dockerCmd = sprintf([ ...
                '%s run --rm -v "%s":/data mdf-python:latest ' ...
                'python /data/AEB_KPI_Project/docker/mdf2matConv.py "/data/rawdata/%s.mf4" ' ...
                '--signal_db "/data/rawdata/%s" --resample %g' ...
            ], dockerBin, projectRoot, baseName, 'tempSignalMap.csv', resampleRate);

            dockerCmd = strtrim(dockerCmd);

            % Run Docker
            status = system(dockerCmd);
            % Clean up temporary CSV file
            if isfile(tempCsvPath)
                delete(tempCsvPath);
            end
            if status ~= 0
                error('Docker failed to process %s', filePath);
            end

            % Load the generated .mat file
            if ~isfile(matFullPath)
                error('MAT file not generated: %s', matFullPath);
            end

            loaded = load(matFullPath);

            if isfield(loaded, 'signalMat')
                signalMats = loaded.signalMat;
            else
                error('MAT file did not contain expected variable "signalMat".');
            end
        end % processMF4FileInternally
    end
end