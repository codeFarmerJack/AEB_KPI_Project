function kpiTable = kpiYawRate(obj, i, aebStartIdx, yawRateSuspTh)
    
    % KPI Yaw Rate Analysis
    % This function analyzes the yaw rate signal to determine the maximum yaw rate
    % and whether it exceeds a specified threshold after an AEB request event.
    %% Inputs:
    % kpiTable       - Table to store KPI results
    % i              - Current index in the kpiTable
    % signalMatChunk - Struct containing signal data with fields:
    %                  Time, YawRate
    % aebStartIdx    - Index of AEB request event
    % yawRateSuspTh  - Threshold for yaw rate suspension in degrees per second
    % offset         - Offset to consider before aebStartIdx for analysis

    %% Outputs:
    % kpiTable       - Updated table with yaw rate KPIs 

    % bind variables from object
    kpiTable = obj.kpiTable;  
    signalMatChunk = obj.signalMatChunk;    
    offset = obj.TIME_IDX_OFFSET;

    [~, idx] = max(abs(signalMatChunk.YawRate(aebStartIdx - offset:end)));
    yawRateMax = signalMatChunk.YawRate(aebStartIdx - offset + idx - 1);
    absYawRateMaxDeg = round(abs(yawRateMax * 180 / pi()), 2);

    kpiTable.yawRateMax(i) = yawRateMax;
    kpiTable.absYawRateMaxDeg(i) = absYawRateMaxDeg;
    kpiTable.isYawRateHigh(i) = absYawRateMaxDeg > yawRateSuspTh;
end
