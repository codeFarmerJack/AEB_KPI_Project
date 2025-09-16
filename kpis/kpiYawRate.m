function kpiYawRate(obj, i, aebStartIdx, yawRateSuspTh)
    % KPI Yaw Rate Analysis
    % This function analyzes the yaw rate signal to determine the maximum yaw rate
    % and whether it exceeds a specified threshold after an AEB request event.
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Current index in the kpiTable
    % aebStartIdx    - Index of AEB request event
    % yawRateSuspTh  - Threshold for yaw rate suspension in degrees per second

    % Use obj.kpiTable and obj.signalMatChunk directly
    kpiTable = obj.kpiTable;
    signalMatChunk = obj.signalMatChunk;
    offset = obj.TIME_IDX_OFFSET;

    % Ensure required columns exist
    if ~ismember('yawRateMax', kpiTable.Properties.VariableNames)
        obj.kpiTable.yawRateMax = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('absYawRateMaxDeg', kpiTable.Properties.VariableNames)
        obj.kpiTable.absYawRateMaxDeg = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('isYawRateHigh', kpiTable.Properties.VariableNames)
        obj.kpiTable.isYawRateHigh = false(height(obj.kpiTable), 1);
    end

    % Calculate yaw rate KPIs
    [~, idx] = max(abs(signalMatChunk.yawRate(aebStartIdx - offset:end)));
    yawRateMax = signalMatChunk.yawRate(aebStartIdx - offset + idx - 1);
    absYawRateMaxDeg = round(abs(yawRateMax * 180 / pi()), 2);

    obj.kpiTable.yawRateMax(i) = yawRateMax;
    obj.kpiTable.absYawRateMaxDeg(i) = absYawRateMaxDeg;
    obj.kpiTable.isYawRateHigh(i) = absYawRateMaxDeg > yawRateSuspTh;
end