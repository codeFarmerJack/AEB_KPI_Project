function kpiTable = kpiSteeringWheel(obj, i, aebStartIdx, steerAngTh, steerAngRateTh)
    
    % Steering wheel analysis
    %% Inputs:
    % kpiTable       - Table to store KPI results
    % i              - Current index in the kpiTable
    % signalMatChunk - Struct containing signal data with fields:
    %                  Time, SteerAngle, SteerAngle_Rate
    % aebStartIdx    - Index of AEB request event
    % steerAngTh     - Threshold for steering angle in degrees
    % steerAngRateTh - Threshold for steering angle rate in degrees per second
    % offset         - Offset to consider before aebStartIdx for analysis   
    %% Outputs:
    % kpiTable       - Updated table with steering wheel KPIs

    % bind variables from object
    kpiTable = obj.kpiTable;
    signalMatChunk = obj.signalMatChunk;
    offset = obj.TIME_IDX_OFFSET;


    % Steering angle
    [~, idx] = max(abs(signalMatChunk.SteerAngle(aebStartIdx - offset:end)));
    steerMax = signalMatChunk.SteerAngle(aebStartIdx - offset + idx - 1);
    absSteerMaxDeg = round(abs(steerMax * 180 / pi()), 2);

    kpiTable.steerMax(i) = steerMax;
    kpiTable.absSteerMaxDeg(i) = absSteerMaxDeg;
    kpiTable.isSteerHigh(i) = absSteerMaxDeg > steerAngTh;

    % Steering angle rate
    [~, idxRate] = max(abs(signalMatChunk.SteerAngle_Rate(aebStartIdx - offset:end)));
    steerRateMax = signalMatChunk.SteerAngle_Rate(aebStartIdx - offset + idxRate - 1);
    absSteerRateMaxDeg = round(abs(steerRateMax * 180 / pi()), 2);

    kpiTable.steerRateMax(i) = steerRateMax;
    kpiTable.absSteerRateMaxDeg(i) = absSteerRateMaxDeg;
    kpiTable.isSteerAngRateHigh(i) = absSteerRateMaxDeg > steerAngRateTh;
end
