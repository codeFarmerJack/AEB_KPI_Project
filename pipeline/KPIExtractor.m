classdef KPIExtractor
    % KPIExtractor class for processing AEB data and calculating KPIs
    properties
        kpiTable
        signalMatChunk
        calibratables
        fileList

        % Constant Parameter 
        PB_TGT_DECEL = -6       % Target deceleration for PB in m/s²  
        FB_TGT_DECEL = -15      % Target deceleration for FB in m/s²
        TGT_TOL = 0.2           % Tolerance for target deceleration
        AEB_END_THD = -4.9      % Threshold to determine AEB end event in m/s²
                                % above this value AEB is considered ended
        TIME_IDX_OFFSET = 300   % Time offset to account for latAccel, yawRate and steering
        CUTOFF_FREQ = 10        % cutoff frequency used for filtering
    end
    
    methods
        function obj = KPIExtractor(cfg)
            % Constructor: Initialize with configuration object
            % Select folder and get file list
            [seldatapath, fileList] = obj.selectFolder();
            obj.fileList = fileList;
            
            % Initialize kpiTable
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
            for i = 1:length(obj.fileList)
                filename = obj.fileList(i).name;
                try
                    data = load(filename); % Loads signalMatChunk
                    obj.signalMatChunk = data.signalMatChunk;
                catch e
                    warning('Failed to load file %s: %s', filename, e.message);
                    continue;
                end
                
                % Preprocess signals
                obj.signalMatChunk.VehicleSpeed = round(obj.signalMatChunk.VehicleSpeed * 3.6, 1);
                obj.signalMatChunk.A2_Filt = utils.accelFilter(obj.signalMatChunk.Time, obj.signalMatChunk.A2, obj.CUTOFF_FREQ);
                obj.signalMatChunk.A1_Filt = utils.accelFilter(obj.signalMatChunk.Time, obj.signalMatChunk.A1, obj.CUTOFF_FREQ);
                
                % Logging
                obj.kpiTable.label(i) = filename;
                obj.kpiTable.condTrue(i) = true;
                obj.kpiTable.logTime(i) = round(seconds(obj.signalMatChunk.Time(1)), 2);
                
                % Locate AEB intervention start - M0
                [aebStartIdx, M0] = utils.findAEBInterventionStart(obj);
                if isempty(aebStartIdx)
                    warning('No AEB intervention start found in file %s. Skipping KPI calculations.', filename);
                    obj.kpiTable.condTrue(i) = false;
                    continue;
                end

                obj.kpiTable.m0IntvStart(i) = round(seconds(M0), 2);            
                vehSpd = obj.signalMatChunk.VehicleSpeed(aebStartIdx(1));
                obj.kpiTable.vehSpd(i) = vehSpd;

                % Locate AEB intervention end - M2
                [isVehStopped, aebEndIdx, M2] = utils.findAEBInterventionEnd(obj, aebStartIdx(1));

                obj.kpiTable.m2IntvEnd(i) = round(seconds(M2), 2);
                obj.kpiTable.isVehStopped(i) = isVehStopped;

                %% Calculate Intervention Duration
                intvDur = M2 - M0;
                obj.kpiTable.intvDur(i) = round(seconds(intvDur), 2);

                %% Longitudinal Clearance
                longGap = round(obj.signalMatChunk.Long_Clearance(aebEndIdx), 2);
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

                % KPI calculations
                obj.kpiTable = kpiThrottle(obj, i, aebStartIdx, pedalPosIncTh);
                obj.kpiTable = kpiSteeringWheel(obj, i, aebStartIdx, steerAngTh, steerAngRateTh);
                obj.kpiTable = kpiLatAccel(obj, i, aebStartIdx, latAccelTh);
                obj.kpiTable = kpiYawRate(obj, i, aebStartIdx, yawRateSuspTh);
                obj.kpiTable = kpiBrakeMode(obj, i, aebStartIdx);
                obj.kpiTable = kpiLatency(obj, i, aebStartIdx);

            end
            % Notify user when done
            disp('✅ All KPI extraction and processing completed successfully.');
        end
        
        function exportToCSV(obj)
            % Export kpiTable to CSV
            outputFilename = 'AEB_KPI_Results.csv';
            try
                % Clean and sort the table
                RowsToDelete = ismissing(obj.kpiTable.label);
                obj.kpiTable(RowsToDelete, :) = [];
                obj.kpiTable = sortrows(obj.kpiTable, 'vehSpd');

                % Write to CSV
                writetable(obj.kpiTable, outputFilename);

                % Notify user
                fprintf('✅ KPI results exported successfully to %s\n', outputFilename);
            catch e
                warning('⚠️ Failed to export KPI results: %s', e.message);
            end
        end

    end
end