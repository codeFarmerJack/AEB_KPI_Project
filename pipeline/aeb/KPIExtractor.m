classdef KPIExtractor < handle
    % < handle class to allow in-place modification of properties
    %  
    % KPIExtractor class for processing AEB data and calculating KPIs
    properties
        kpiTable                % Table to hold KPI results
        signalMatChunk          % Struct to hold the loaded signal data chunk
        calibratables           % Struct to hold calibratable thresholds
        fileList                % List of .mat files to process
        pathToCsv               % Path to save CSV results

        % Constant Parameters
        PB_TGT_DECEL = -6       % Target deceleration for PB in m/s²  
        FB_TGT_DECEL = -15      % Target deceleration for FB in m/s²
        TGT_TOL = 0.2           % Tolerance for target deceleration
        AEB_END_THD = -4.9      % Threshold to determine AEB end event in m/s²
        TIME_IDX_OFFSET = 300   % Time offset to account for latAccel, yawRate, and steering
        CUTOFF_FREQ = 10        % Cutoff frequency used for filtering
    end
    
    methods
        function obj = KPIExtractor(config, eventDetector)
            
            % Constructor: Initialize with configuration object and EventDetector
            % Initialize pathToCsv with eventDetector.pathToMatChunks and fileList from that directory
            if nargin < 2
                error('Configuration object and EventDetector are required for initialization.');
            end
            
            % Validate input is an EventDetector instance
            if ~isa(eventDetector, 'EventDetector')
                error('Second argument must be an instance of EventDetector.');
            end
            
            % Set pathToCsv to eventDetector.pathToMatChunks
            obj.pathToCsv = eventDetector.pathToMatChunks;
            
            % Get fileList from pathToCsv
            fileList = dir(fullfile(obj.pathToCsv, '*.mat')); % Get all .mat files in the folder
            if isempty(fileList)
                error('No .mat files found in the folder: %s', obj.pathToCsv);
            end
            obj.fileList = fileList;
            
            % Initialize kpiTable using updated createKpiTableFromJson with unit support
            obj.kpiTable = utils.createKpiTableFromJson(config.kpiSchemaPath, length(fileList));
            
            % Load and store calibratables
            obj.calibratables.SteeringWheelAngle_Th          = config.calibratables.SteeringWheelAngle_Th;
            obj.calibratables.AEB_SteeringAngleRate_Override = config.calibratables.AEB_SteeringAngleRate_Override;
            obj.calibratables.PedalPosProIncrease_Th         = config.calibratables.PedalPosProIncrease_Th;
            obj.calibratables.PedalPosProIncrease_Th{2, :}   = obj.calibratables.PedalPosProIncrease_Th{2, :} * 100;
            obj.calibratables.YawrateSuspension_Th           = config.calibratables.YawrateSuspension_Th;
            obj.calibratables.LateralAcceleration_th         = config.calibratables.LateralAcceleration_th;
        end
        
        function obj = processAllMatFiles(obj)
            % Process all .mat files and calculate KPIs
            originpath = pwd; % Store current directory
            cd(obj.pathToCsv); % Navigate to pathToCsv
            aebStartIdxList = zeros(length(obj.fileList), 1); % Store aebStartIdx per file

            for i = 1:length(obj.fileList)
                filename = fullfile(obj.pathToCsv, obj.fileList(i).name);
        
                % Load data and set signalMatChunk
                try
                    data = load(filename);
                    if isfield(data, 'signalMatChunk')
                        obj.signalMatChunk = data.signalMatChunk;
                    elseif isstruct(data) && numel(fieldnames(data)) == 1
                        fn = fieldnames(data);
                        obj.signalMatChunk = data.(fn{1});
                        warning('Using %s as signalMatChunk for %s. Expected signalMatChunk.', fn{1}, filename);
                    else
                        warning('No signalMatChunk found in %s. Available variables: %s. Skipping file.', ...
                                filename, strjoin(fieldnames(data), ', '));
                        continue;
                    end
                catch e
                    warning('Failed to load file %s: %s. Skipping file.', filename, e.message);
                    continue;
                end
                
                % Preprocess signals
                obj.signalMatChunk.egoSpeed = obj.signalMatChunk.egoSpeed * 3.6;
                obj.signalMatChunk.A2_Filt  = utils.accelFilter(obj.signalMatChunk.time, obj.signalMatChunk.longActAccel, obj.CUTOFF_FREQ);
                obj.signalMatChunk.A1_Filt  = utils.accelFilter(obj.signalMatChunk.time, obj.signalMatChunk.latActAccel, obj.CUTOFF_FREQ);
                
                % Logging
                if isa(obj.kpiTable.label, 'cell')
                    obj.kpiTable.label{i} = filename; % Assign char to cell
                    warning('label column is cell. Assigned char directly. Consider updating schema to string.');
                else
                    obj.kpiTable.label(i) = string(obj.fileList(i).name); % Assign file name to label column
                end
                if isduration(obj.signalMatChunk.time)
                    time_value = seconds(obj.signalMatChunk.time(1));
                else
                    time_value = double(obj.signalMatChunk.time(1));
                end
                if ~isnan(time_value) && isfinite(time_value)
                    obj.kpiTable.logTime(i) = round(time_value, 2);
                else
                    warning('Invalid time value for %s: %s. Setting logTime to NaN.', filename, string(obj.signalMatChunk.time(1)));
                    obj.kpiTable.logTime(i) = NaN;
                end
                
                % Locate AEB intervention start - M0
                [aebStartIdx, M0] = utils.findAEBInterventionStart(obj);
                aebStartIdxList(i) = aebStartIdx(1);

                % Assign m0IntvStart and vehSpd
                if isduration(M0)
                    m0Value = seconds(M0);
                else
                    m0Value = double(M0);
                end
                if ~isnan(m0Value) && isfinite(m0Value)
                    obj.kpiTable.m0IntvStart(i) = round(m0Value, 2);
                else
                    warning('Invalid M0 value for %s: %s. Setting m0IntvStart to NaN.', filename, string(M0));
                    obj.kpiTable.m0IntvStart(i) = NaN;
                end            
                vehSpd = obj.signalMatChunk.egoSpeed(aebStartIdx(1));
                obj.kpiTable.vehSpd(i) = vehSpd;

                % Locate AEB intervention end - M2
                [isVehStopped, aebEndIdx, M2] = utils.findAEBInterventionEnd(obj, aebStartIdx(1));
                obj.kpiTable.isVehStopped(i) = isVehStopped;

                % Assign m2IntvEnd
                if isduration(M2)
                    m2Value = seconds(M2);
                else
                    m2Value = double(M2);
                end
                if ~isnan(m2Value) && isfinite(m2Value)
                    obj.kpiTable.m2IntvEnd(i) = round(m2Value, 2);
                else
                    warning('Invalid M2 value for %s: %s. Setting m2IntvEnd to NaN.', filename, string(M2));
                    obj.kpiTable.m2IntvEnd(i) = NaN;
                end

                % Calculate Intervention Duration
                intvDur = M2 - M0;
                if isduration(intvDur)
                    intvDurValue = seconds(intvDur);
                else
                    intvDurValue = double(intvDur);
                end
                if ~isnan(intvDurValue) && isfinite(intvDurValue)
                    obj.kpiTable.intvDur(i) = round(intvDurValue, 2);
                else
                    warning('Invalid intvDur value for %s: %s. Setting intvDur to NaN.', filename, string(intvDur));
                    obj.kpiTable.intvDur(i) = NaN;
                end
                
                % Interpolate calibratables
                steerAngTh      = utils.interpolateThresholdClamped(obj.calibratables.SteeringWheelAngle_Th, vehSpd);
                steerAngRateTh  = utils.interpolateThresholdClamped(obj.calibratables.AEB_SteeringAngleRate_Override, vehSpd);
                pedalPosIncTh   = utils.interpolateThresholdClamped(obj.calibratables.PedalPosProIncrease_Th, vehSpd);
                yawRateSuspTh   = utils.interpolateThresholdClamped(obj.calibratables.YawrateSuspension_Th, vehSpd);
                latAccelTh      = utils.interpolateThresholdClamped(obj.calibratables.LateralAcceleration_th, vehSpd);
                
                obj.kpiTable.steerAngTh(i)      = steerAngTh;
                obj.kpiTable.steerAngRateTh(i)  = steerAngRateTh;
                obj.kpiTable.pedalPosIncTh(i)   = pedalPosIncTh;
                obj.kpiTable.yawRateSuspTh(i)   = yawRateSuspTh;      
                obj.kpiTable.latAccelTh(i)      = latAccelTh;
                
                % KPI calculations - update the kpiTable in place
                kpiDistance(obj, i, aebStartIdx, aebEndIdx)
                kpiThrottle(obj, i, aebStartIdx, pedalPosIncTh);
                kpiSteeringWheel(obj, i, aebStartIdx, steerAngTh, steerAngRateTh);
                kpiLatAccel(obj, i, aebStartIdx, latAccelTh);
                kpiYawRate(obj, i, aebStartIdx, yawRateSuspTh);
                kpiBrakeMode(obj, i, aebStartIdx);
                kpiLatency(obj, i, aebStartIdx);
            end % for each file

            cd(originpath); % Return to original directory
            
        end % processAllMatFiles    
        
        function exportToCSV(obj)
            % Export kpiTable to CSV with headers including units
            outputFilename = fullfile(obj.pathToCsv, 'AEB_KPI_Results.csv');
            try
                % Clean and sort the table
                RowsToDelete = ismissing(obj.kpiTable.label);
                obj.kpiTable(RowsToDelete, :) = [];
                obj.kpiTable = sortrows(obj.kpiTable, 'vehSpd');

                % Temporarily set VariableNames to display names with units for export
                originalVarNames = obj.kpiTable.Properties.VariableNames;
                obj.kpiTable.Properties.VariableNames = obj.kpiTable.Properties.UserData.displayNames;

                % Write to CSV with display names (including units)
                writetable(obj.kpiTable, outputFilename, 'WriteVariableNames', true, ...
                    'WriteMode', 'overwrite');

                % Restore original VariableNames
                obj.kpiTable.Properties.VariableNames = originalVarNames;

            catch e
                % Restore original VariableNames in case of error
                if exist('originalVarNames', 'var')
                    obj.kpiTable.Properties.VariableNames = originalVarNames;
                end
                warning('⚠️ Failed to export KPI results: %s', e.message);
            end 
        end % exportToCSV
    end % methods
end