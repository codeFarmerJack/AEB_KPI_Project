function kpiTable = kpiLatency(obj, i, aebStartIdx)
    
    % AEB system latency
    %% Inputs:
    % kpiTable       - Table to store KPI results
    % i              - Current index in the kpiTable
    % signalMatChunk - Struct containing signal data with fields:
    %                  Time, A2
    % aebStartIdx    - Index of AEB request event
    % cutoffFreq     - Frequency for filtering (if needed)   
    %% Outputs:
    % kpiTable       - Updated table with latency KPIs

    % bind variables from object
    kpiTable = obj.kpiTable;  
    signalMatChunk = obj.signalMatChunk;    
    cutoffFreq = obj.CUTOFF_FREQ; 

    [AEB_Resp, ~, ~] = utils.detectKneepoint_v4( ...
        signalMatChunk.Time(aebStartIdx:aebStartIdx+30), ...
        signalMatChunk.A2(aebStartIdx:aebStartIdx+30), ...
        'negative', cutoffFreq, 'curvature');

    M0 = signalMatChunk.Time(aebStartIdx);
    M1 = signalMatChunk.Time(aebStartIdx + AEB_Resp);

    kpiTable.m1IntvSysResp(i) = round(seconds(M1), 2);
    kpiTable.m1DeadTime(i)    = round(seconds(M1 - M0), 2);
end
