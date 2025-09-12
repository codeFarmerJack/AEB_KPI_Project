classdef Config
    properties
        graphSpec             % Table from sheet 'graphSpec'
        lineColors            % Table from sheet 'lineColors'
        calibratables         % Struct of calibration tables
        jsonConfigPath        % Path to JSON config file
        signalMap             % Name of signal mapping Excel file
        signalPlotSpecPath    % Full path to SignalPlotSpec Excel file
        signalPlotSpecName    % File name of SignalPlotSpec Excel file
        calibrationFilePath   % Full path to Calibration Excel file
        calibrationFileName   % File name of Calibration Excel file
        kpiSchemaPath         % Full path to kpiSchema JSON file
        kpiSchemaFileName     % File name of kpiSchema JSON file
    end

    methods
        function obj = Config()
            % Empty constructor; use fromJSON to populate
        end
    end

    methods (Static)
        function obj = fromJSON(jsonConfigPath)
            % Create Config object from JSON file
            configStruct = Config.loadConfig(jsonConfigPath);

            % Create empty object
            obj = Config();
            obj.jsonConfigPath = jsonConfigPath;

            % Load kpiSchema path and filename if present
            if isfield(configStruct, 'kpiSchema') && isfield(configStruct.kpiSchema, 'FilePath')
                kpiSchemaPath = configStruct.kpiSchema.FilePath;
                if isstring(kpiSchemaPath) || ischar(kpiSchemaPath)
                    if ~isempty(kpiSchemaPath)  % Additional check for empty path
                        obj.kpiSchemaPath = kpiSchemaPath;
                        [~, kpiName, kpiExt] = fileparts(kpiSchemaPath);  % Extracts name and ext safely
                        obj.kpiSchemaFileName = string([kpiName, kpiExt]);  % Combine name + extension
                    else
                        warning('kpiSchema.FilePath is empty. Setting defaults.');
                        obj.kpiSchemaPath = '';
                        obj.kpiSchemaFileName = '';
                    end
                else
                    warning('kpiSchema.FilePath should be a string. Ignoring invalid entry.');
                    obj.kpiSchemaPath = '';
                    obj.kpiSchemaFileName = '';
                end
            else
                obj.kpiSchemaPath = '';
                obj.kpiSchemaFileName = '';
            end

            % Load SignalPlotSpec sheets
            specPath  = configStruct.SignalPlotSpec.FilePath;
            sheetList = configStruct.SignalPlotSpec.Sheets;
            signalMapPlotSpec = Config.loadSignalMapPlotSpec(specPath, sheetList);

            obj.signalMap          = signalMapPlotSpec.vbRcSignals;
            obj.graphSpec          = signalMapPlotSpec.graphSpec;
            obj.lineColors         = signalMapPlotSpec.lineColors;
            obj.signalPlotSpecPath = specPath;                   % <<< store full path
            [~, specName, specExt] = fileparts(specPath);
            obj.signalPlotSpecName = [specName, specExt];        % <<< store file name only

            % Load calibratables
            calibFile = configStruct.Calibration.FilePath;
            sheetDefs = configStruct.Calibration.Sheets;
            obj.calibratables       = Config.loadCalibratables(calibFile, sheetDefs);
            obj.calibrationFilePath = calibFile;                 % <<< store full path
            [~, calibName, calibExt] = fileparts(calibFile);
            obj.calibrationFileName = [calibName, calibExt];     % <<< store file name only
        end
    end

    methods (Static, Access = private)
        function params = loadConfig(filePath)
            % Load JSON config and extract paths and sheet definitions
            if ~isfile(filePath)
                error('Config file not found: %s', filePath);
            end
            
            cfgText = fileread(filePath);
            params = jsondecode(cfgText);
        
            % Validate SignalPlotSpec
            if ~isfield(params, 'SignalPlotSpec') || ~isfield(params.SignalPlotSpec, 'FilePath')
                error('Missing SignalPlotSpec.FilePath in config.');
            end
            if ~isfield(params.SignalPlotSpec, 'Sheets') || ~iscell(params.SignalPlotSpec.Sheets)
                error('SignalPlotSpec.Sheets must be a cell array of sheet names.');
            end
        
            % Validate Calibration
            if ~isfield(params, 'Calibration') || ~isfield(params.Calibration, 'FilePath')
                error('Missing Calibration.FilePath in config.');
            end
            if ~isstring(params.Calibration.FilePath) && ~ischar(params.Calibration.FilePath)
                error('Calibration.FilePath must be a string, got %s', class(params.Calibration.FilePath));
            end
            if ~isfield(params.Calibration, 'Sheets') || ~isstruct(params.Calibration.Sheets)
                error('Calibration.Sheets must be a struct of sheet definitions.');
            end
            
            % Normalize sheet names for calibration
            sheetNames = fieldnames(params.Calibration.Sheets);
            normSheets = struct();
            for i = 1:numel(sheetNames)
                s = sheetNames{i};
                normSheets.(matlab.lang.makeValidName(s)) = params.Calibration.Sheets.(s);
            end
            params.Calibration.SheetsNormalized = normSheets;
        end % loadConfig
        
        function signalMapPlotSpec = loadSignalMapPlotSpec(filePath, sheetList)
            % Load specified sheets from SignalPlotSpec Excel file
        
            if ~isfile(filePath)
                error('SignalPlotSpec file not found: %s', filePath);
            end
            if ~iscell(sheetList)
                error('Sheet list must be a cell array of sheet names.');
            end
        
            signalMapPlotSpec = struct();
            for i = 1:numel(sheetList)
                sheetName = sheetList{i};
                try
                    tbl = readtable(filePath, 'Sheet', sheetName, 'PreserveVariableNames', true);
                    signalMapPlotSpec.(matlab.lang.makeValidName(sheetName)) = tbl;
                catch ME
                    warning('Failed to read sheet "%s": %s', sheetName, ME.message);
                end
            end % for
        end % loadSignalMapPlotSpec


        function calibratables = loadCalibratables(calibFile, sheetMap)
            % Load calibration ranges from Excel file into a 2-level struct
            % with only .Data tables
            
            if ~isstring(calibFile) && ~ischar(calibFile)
                error('calibFile must be a string, got %s', class(calibFile));
            end
            if ~isfile(calibFile)
                error('Calibration file not found: %s', calibFile);
            end

            calibratables = struct();
            sheetNames = fieldnames(sheetMap);

            for i = 1:numel(sheetNames)
                sheet = sheetNames{i};
                calDefs = sheetMap.(sheet);

                calNames = fieldnames(calDefs);
                for j = 1:numel(calNames)
                    calName = calNames{j};
                    range = calDefs.(calName);

                    try
                        tbl = readtable(calibFile, 'Sheet', sheet, ...
                            'Range', range, 'PreserveVariableNames', true);

                        calKey   = matlab.lang.makeValidName(calName);

                        % Store ONLY the Data table
                        calibratables.(calKey) = tbl;

                    catch ME
                        warning('Failed to load "%s" from sheet "%s" range "%s": %s', ...
                                calName, sheet, range, ME.message);
                        calibratables.(calKey) = [];
                    end
                end
            end
        end % loadCalibratables
    end % methods
end % classdef Config
