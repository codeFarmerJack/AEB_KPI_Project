function kpiSteeringWheel(obj, i, aebStartIdx, steerAngTh, steerAngRateTh)
    % Steering wheel analysis
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Current index in the kpiTable
    % aebStartIdx    - Index of AEB request event
    % steerAngTh     - Threshold for steering angle in degrees
    % steerAngRateTh - Threshold for steering angle rate in degrees per second

    % Use obj.kpiTable and obj.signalMatChunk directly
    kpiTable = obj.kpiTable;
    signalMatChunk = obj.signalMatChunk;
    offset = obj.TIME_IDX_OFFSET;

    % Ensure required columns exist
    if ~ismember('steerMax', kpiTable.Properties.VariableNames)
        obj.kpiTable.steerMax = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('absSteerMaxDeg', kpiTable.Properties.VariableNames)
        obj.kpiTable.absSteerMaxDeg = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('isSteerHigh', kpiTable.Properties.VariableNames)
        obj.kpiTable.isSteerHigh = false(height(obj.kpiTable), 1);
    end
    if ~ismember('steerRateMax', kpiTable.Properties.VariableNames)
        obj.kpiTable.steerRateMax = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('absSteerRateMaxDeg', kpiTable.Properties.VariableNames)
        obj.kpiTable.absSteerRateMaxDeg = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('isSteerAngRateHigh', kpiTable.Properties.VariableNames)
        obj.kpiTable.isSteerAngRateHigh = false(height(obj.kpiTable), 1);
    end

    % Steering angle
    [~, idx] = max(abs(signalMatChunk.steerWheelAngle(aebStartIdx - offset:end)));
    steerMax = signalMatChunk.steerWheelAngle(aebStartIdx - offset + idx - 1);
    absSteerMaxDeg = round(abs(steerMax * 180 / pi()), 2);

    obj.kpiTable.steerMax(i) = steerMax;
    obj.kpiTable.absSteerMaxDeg(i) = absSteerMaxDeg;
    obj.kpiTable.isSteerHigh(i) = absSteerMaxDeg > steerAngTh;

    % Steering angle rate
    [~, idxRate] = max(abs(signalMatChunk.steerWheelAngleSpeed(aebStartIdx - offset:end)));
    steerRateMax = signalMatChunk.steerWheelAngleSpeed(aebStartIdx - offset + idxRate - 1);
    absSteerRateMaxDeg = round(abs(steerRateMax * 180 / pi()), 2);

    obj.kpiTable.steerRateMax(i) = steerRateMax;
    obj.kpiTable.absSteerRateMaxDeg(i) = absSteerRateMaxDeg;
    obj.kpiTable.isSteerAngRateHigh(i) = absSteerRateMaxDeg > steerAngRateTh;
end