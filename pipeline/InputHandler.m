classdef InputHandler
    properties
        jsonConfigPath      % Path to JSON config file
        rawDataPath         % Path to raw data folder - *.mf4, set during processing
        % Mirrored Config properties
        signalMap
        graphSpec          % Table from sheet 'graphSpec'
        lineColors         % Table from sheet 'lineColors'
        % Additional properties for convenience
        signalPlotSpecPath
        signalPlotSpecName
    end

    methods
        function obj = InputHandler(config)
            % Constructor: accepts a Config object
            obj.jsonConfigPath      = config.jsonConfigPath;

            % Mirror Config properties
            obj.graphSpec           = config.graphSpec;
            obj.lineColors          = config.lineColors;
            obj.signalMap           = config.signalMap;
        
            obj.signalPlotSpecPath  = config.signalPlotSpecPath;
            obj.signalPlotSpecName  = config.signalPlotSpecName;
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

            % Set rawDataPath to the selected folder
            obj.rawDataPath = seldatapath;

            % Verify if folder contains MF4 files
            files = dir(fullfile(seldatapath, '*.mf4'));
            if isempty(files)
                fprintf('No MF4 files found in selected folder: %s\n', seldatapath);
                cd(curFolder);
                processedData = {};
                return;
            end

            % Get path to signal mapping Excel file
            % mapFile = obj.signalPlotSpecPath;

            mapFile = uigetfile({'*.csv;*.xlsx','Signal DB Files (*.csv,*.xlsx)'}, 'Select Signal Database');
            if mapFile == 0
                fprintf('No signal database file selected. Operation cancelled.\n');
                processedData = {};
                return;
            end
            % Ensure mapFile is a file, not a directory
            if ~isfile(fullfile(obj.rawDataPath, mapFile))
                fprintf('Error: Selected signal database is not a valid file: %s\n', mapFile);
                processedData = {};
                return;
            end
            disp('Selected Signal DB file:');
            disp(mapFile);
            

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
            % Process MF4 file with Docker + Python
            %
            % Inputs:
            %   filePath     - Full path to the .mf4 file
            %   mapFile      - Path to signalDatabase.csv or .xlsx
            %   resampleRate - Resampling interval in seconds (e.g., 0.01 for 100 Hz)
            %
            % Outputs:
            %   datVars - Data loaded from the generated .mat file

            if nargin < 3
                error('Usage: processMF4FileInternally(filePath, mapFile, resampleRate)');
            end
            if nargin < 4
                resampleRate = 0.01; % Default 10 ms
            end
            validateattributes(resampleRate, {'numeric'}, {'positive','scalar'}, ...
                'processMF4FileInternally', 'resampleRate');

            % Verify the .mf4 file exists
            if ~isfile(filePath)
                error('MF4 file not found: %s', filePath);
            end

            % Extract folder and base name
            [folder, baseName, ~] = fileparts(filePath);
            matFullPath = fullfile(folder, [baseName '.mat']);

            % Build Docker command
            dockerBin   = '/usr/local/bin/docker';
            projectRoot = fileparts(folder); % Go up from rawdata to project root

            dockerCmd = sprintf([ ...
                '%s run --rm -v "%s":/data mdf-python:latest ' ...
                'python /data/AEB_KPI_Project/pipeline/mdf2matSim.py "/data/rawdata/%s.mf4" ' ...
                '--signal_db "/data/%s" --resample %g' ...
            ], dockerBin, projectRoot, baseName, mapFile, resampleRate);

            dockerCmd = strtrim(dockerCmd);

            % Run Docker
            status = system(dockerCmd);
            if status ~= 0
                error('Docker failed to process %s', filePath);
            end

            % Load the generated .mat file
            if ~isfile(matFullPath)
                error('MAT file not generated: %s', matFullPath);
            end

            loaded = load(matFullPath);

            if isfield(loaded, 'data')
                datVars = loaded.data;
            else
                error('MAT file did not contain expected variable "data".');
            end
        end % processMF4FileInternally

    end % methods
end