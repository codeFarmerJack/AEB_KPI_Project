classdef KPIExtractor
    % KPIExtractor class for processing AEB data and calculating KPIs
    properties
        kpiTable
        signalMatChunk
        cutoffFreq = 10
        timeSampleOffset
        thresholds
        fileList
    end
    
    methods
        function obj = KPIExtractor(cfg)
            % Constructor: Initialize with configuration object
            % Select folder and get file list
            [seldatapath, fileList] = obj.selectFolder();
            obj.fileList = fileList;
            
            % Initialize kpiTable
            obj.kpiTable = utils.createKpiTableFromJson(cfg.kpiSchemaPath, length(fileList));
            obj.timeSampleOffset = 3000 / obj.cutoffFreq;
            
            % Load and store thresholds
            obj.thresholds.SteeringWheelAngle_Th = cfg.Calibratables.SteeringWheelAngle_Th;
            obj.thresholds.AEB_SteeringAngleRate_Override = cfg.Calibratables.AEB_SteeringAngleRate_Override;
            obj.thresholds.PedalPosProIncrease_Th = cfg.Calibratables.PedalPosProIncrease_Th;
            obj.thresholds.PedalPosProIncrease_Th{2, :} = obj.thresholds.PedalPosProIncrease_Th{2, :} * 100;
            obj.thresholds.YawrateSuspension_Th = cfg.Calibratables.YawrateSuspension_Th;
            obj.thresholds.LateralAcceleration_th = cfg.Calibratables.LateralAcceleration_th;
        end
        
        function [seldatapath, fileList] = selectFolder(~)
            % Select folder containing .mat files
            originpath = pwd; % Store current folder
            seldatapath = uigetdir(originpath); % Select folder containing log files
            if seldatapath == 0
                error('No folder selected. Please select a valid folder containing .mat files.');
            end
            cd(seldatapath); % Navigate to selected folder
            fileList = dir('*.mat'); % Get all .mat files in the folder
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
                obj.signalMatChunk.A2_Filt = utils.accelFilter(obj.signalMatChunk.Time, obj.signalMatChunk.A2, obj.cutoffFreq);
                obj.signalMatChunk.A1_Filt = utils.accelFilter(obj.signalMatChunk.Time, obj.signalMatChunk.A1, obj.cutoffFreq);
                
                % Logging
                obj.kpiTable.label(i) = filename;
                obj.kpiTable.condTrue(i) = true;
                obj.kpiTable.logTime(i) = round(seconds(obj.signalMatChunk.Time(1)), 2);
                
                % Locate intervention start (M0)
                [AEB_Req, ~, ~] = utils.findFirstLastIndicesAdvanced(obj.signalMatChunk.DADCAxLmtIT4, -6, 'less', 0.1);
                if isempty(AEB_Req)
                    warning('No AEB intervention detected in file %s', filename);
                    continue;
                end
                
                M0 = obj.signalMatChunk.Time(AEB_Req(1));
                obj.kpiTable.m0IntvStart(i) = round(seconds(M0), 2);
                vehSpd = obj.signalMatChunk.VehicleSpeed(AEB_Req(1));
                obj.kpiTable.vehSpd(i) = vehSpd;
                
                % Interpolate thresholds
                steerAngTh = utils.interpolateThresholdClamped(obj.thresholds.SteeringWheelAngle_Th, vehSpd);
                steerAngRateTh = utils.interpolateThresholdClamped(obj.thresholds.AEB_SteeringAngleRate_Override, vehSpd);
                pedalPosIncTh = utils.interpolateThresholdClamped(obj.thresholds.PedalPosProIncrease_Th, vehSpd);
                yawRateSuspTh = utils.interpolateThresholdClamped(obj.thresholds.YawrateSuspension_Th, vehSpd);
                latAccelTh = utils.interpolateThresholdClamped(obj.thresholds.LateralAcceleration_th, vehSpd);
                
                % KPI calculations
                obj.kpiTable = kpiThrottle(obj.kpiTable, i, obj.signalMatChunk, AEB_Req, pedalPosIncTh);
                obj.kpiTable = kpiSteeringWheel(obj.kpiTable, i, obj.signalMatChunk, AEB_Req, steerAngTh, steerAngRateTh, obj.timeSampleOffset);
                obj.kpiTable = kpiLatAccel(obj.kpiTable, i, obj.signalMatChunk, AEB_Req, latAccelTh, obj.timeSampleOffset);
                obj.kpiTable = kpiYawRate(obj.kpiTable, i, obj.signalMatChunk, AEB_Req, yawRateSuspTh, obj.timeSampleOffset);
                obj.kpiTable = kpiBrakeMode(obj.kpiTable, i, obj.signalMatChunk, AEB_Req, obj.cutoffFreq);
                obj.kpiTable = kpiLatency(obj.kpiTable, i, obj.signalMatChunk, AEB_Req, obj.cutoffFreq);

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