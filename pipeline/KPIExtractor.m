classdef KPIExtractor < handle
    % < handle class to allow in-place modification of properties
    %  
    % KPIExtractor class for processing AEB data and calculating KPIs
    properties
        kpiTable
        signalMatChunk
        calibratables
        fileList

        % Constant Parameters
        PB_TGT_DECEL = -6       % Target deceleration for PB in m/s²  
        FB_TGT_DECEL = -15      % Target deceleration for FB in m/s²
        TGT_TOL = 0.2           % Tolerance for target deceleration
        AEB_END_THD = -4.9      % Threshold to determine AEB end event in m/s²
        TIME_IDX_OFFSET = 300   % Time offset to account for latAccel, yawRate, and steering
        CUTOFF_FREQ = 10        % Cutoff frequency used for filtering
    end
    
    methods
        function obj = KPIExtractor(cfg)
            % Constructor: Initialize with configuration object
            [seldatapath, fileList] = obj.selectFolder();
            obj.fileList = fileList;
            
            % Initialize kpiTable using updated createKpiTableFromJson with unit support
            obj.kpiTable = utils.createKpiTableFromJson(cfg.kpiSchemaPath, length(fileList));
            
            % Load and store calibratables
            obj.calibratables.SteeringWheelAngle_Th = cfg.calibratables.SteeringWheelAngle_Th;
            obj.calibratables.AEB_SteeringAngleRate_Override = cfg.calibratables.AEB_SteeringAngleRate_Override;
            obj.calibratables.PedalPosProIncrease_Th = cfg.calibratables.PedalPosProIncrease_Th;
            obj.calibratables.PedalPosProIncrease_Th{2, :} = obj.calibratables.PedalPosProIncrease_Th{2, :} * 100;
            obj.calibratables.YawrateSuspension_Th = cfg.calibratables.YawrateSuspension_Th;
            obj.calibratables.LateralAcceleration_th = cfg.calibratables.LateralAcceleration_th;
        end
        
        function [seldatapath, fileList] = selectFolder(~)
            % Select folder containing .mat files
            originpath = pwd;                   % Store current folder
            seldatapath = uigetdir(originpath); % Select folder containing log files
            if seldatapath == 0
                error('No folder selected. Please select a valid folder containing .mat files.');
            end
            cd(seldatapath);            % Navigate to selected folder
            fileList = dir('*.mat');    % Get all .mat files in the folder
            if isempty(fileList)
                error('No .mat files found in the selected folder.');
            end
        end
        
        function obj = processAllMatFiles(obj)
            % Process all .mat files and calculate KPIs
            dataFolder = pwd; % Assume current directory from selectFolder
            aebStartIdxList = zeros(length(obj.fileList), 1); % Store aebStartIdx per file

            for i = 1:length(obj.fileList)
                filename = fullfile(dataFolder, obj.fileList(i).name);
        
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
                obj.signalMatChunk.A2_Filt = utils.accelFilter(obj.signalMatChunk.time, obj.signalMatChunk.longActAccel, obj.CUTOFF_FREQ);
                obj.signalMatChunk.A1_Filt = utils.accelFilter(obj.signalMatChunk.time, obj.signalMatChunk.latActAccel, obj.CUTOFF_FREQ);
                
                % Logging
                if isa(obj.kpiTable.label, 'cell')
                    obj.kpiTable.label{i} = filename; % Assign char to cell
                    warning('label column is cell. Assigned char directly. Consider updating schema to string.');
                else
                    obj.kpiTable.label(i) = string(filename); % Assign string to string column
                end
                obj.kpiTable.condTrue(i) = true;
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

                % Longitudinal Clearance
                longGap = obj.signalMatChunk.longGap(aebEndIdx);
                obj.kpiTable.longGap(i) = longGap;
                
                % Interpolate calibratables
                steerAngTh = utils.interpolateThresholdClamped(obj.calibratables.SteeringWheelAngle_Th, vehSpd);
                steerAngRateTh = utils.interpolateThresholdClamped(obj.calibratables.AEB_SteeringAngleRate_Override, vehSpd);
                pedalPosIncTh = utils.interpolateThresholdClamped(obj.calibratables.PedalPosProIncrease_Th, vehSpd);
                yawRateSuspTh = utils.interpolateThresholdClamped(obj.calibratables.YawrateSuspension_Th, vehSpd);
                latAccelTh = utils.interpolateThresholdClamped(obj.calibratables.LateralAcceleration_th, vehSpd);
                
                obj.kpiTable.steerAngTh(i) = steerAngTh;
                obj.kpiTable.steerAngRateTh(i) = steerAngRateTh;
                obj.kpiTable.pedalPosIncTh(i) = pedalPosIncTh;
                obj.kpiTable.yawRateSuspTh(i) = yawRateSuspTh;      
                obj.kpiTable.latAccelTh(i) = latAccelTh;
                
                % KPI calculations - update the kpiTable in place
                kpiThrottle(obj, i, aebStartIdx, pedalPosIncTh);
                kpiSteeringWheel(obj, i, aebStartIdx, steerAngTh, steerAngRateTh);
                kpiLatAccel(obj, i, aebStartIdx, latAccelTh);
                kpiYawRate(obj, i, aebStartIdx, yawRateSuspTh);
                kpiBrakeMode(obj, i, aebStartIdx);
                kpiLatency(obj, i, aebStartIdx);
            end % for each file

            % Notify user when done
            disp('✅ All KPI extraction and processing completed successfully.');
        end % processAllMatFiles    
        
        function exportToCSV(obj)
            % Export kpiTable to CSV with headers including units
            outputFilename = 'AEB_KPI_Results.csv';
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

                % Notify user
                fprintf('✅ KPI results exported successfully to %s\n', outputFilename);
            catch e
                % Restore original VariableNames in case of error
                if exist('originalVarNames', 'var')
                    obj.kpiTable.Properties.VariableNames = originalVarNames;
                end
                warning('⚠️ Failed to export KPI results: %s', e.message);
            end
        end % exportToCSV
    end
end