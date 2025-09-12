function kpiTable = kpiLatAccel(obj, i, aebStartIdx, latAccelTh)
    % Lateral acceleration
    %% Inputs:
    % kpiTable       - Table to store KPI results
    % i              - Current index in the kpiTable
    % signalMatChunk - Struct containing signal data with fields:
    %                  Time, A1_Filt
    % aebStartIdx    - Index of AEB request event
    % latAccelTh     - Threshold for lateral acceleration in m/s²
    % offset         - Offset to consider before aebStartIdx for analysis   
    %% Outputs:
    % kpiTable       - Updated table with lateral acceleration KPIs

    % bind variables from object
    kpiTable = obj.kpiTable;
    signalMatChunk = obj.signalMatChunk;
    offset = obj.TIME_IDX_OFFSET;    

    [~, idx] = max(abs(signalMatChunk.A1_Filt(aebStartIdx - offset:end)));
    latAccelMax = signalMatChunk.A1_Filt(aebStartIdx - offset + idx - 1);
    absLatAccelMax = abs(latAccelMax);

    kpiTable.latAccelMax(i) = latAccelMax;
    kpiTable.absLatAccelMax(i) = absLatAccelMax;
    kpiTable.isLatAccelHigh(i) = absLatAccelMax > latAccelTh;
end
