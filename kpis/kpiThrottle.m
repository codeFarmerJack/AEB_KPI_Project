function kpiTable = kpiThrottle(obj, i, aebStartIdx, pedalPosIncTh)
    
    % Throttle pedal analysis
    %% Inputs:
    % kpiTable       - Table to store KPI results
    % i                  - Current index in the kpiTable
    % signalMatChunk - Struct containing signal data with fields:
    %                  Time, PedalPosPro
    % aebStartIdx    - Index of AEB request event
    % pedalPosIncTh  - Threshold for pedal position increase   
    %% Outputs:
    % kpiTable       - Updated table with throttle pedal KPIs

    % bind variables from object
    kpiTable = obj.kpiTable; 
    signalMatChunk = obj.signalMatChunk;    

    pedalStart = signalMatChunk.PedalPosPro(aebStartIdx);
    kpiTable.pedalStart(i) = pedalStart;
    kpiTable.isPedalOnAtStrt(i) = pedalStart ~= 0;

    pedalMax = max(signalMatChunk.PedalPosPro(aebStartIdx:end));
    kpiTable.pedalMax(i) = pedalMax;

    isPedalHigh = (pedalMax - pedalStart) > pedalPosIncTh;
    kpiTable.isPedalHigh(i) = isPedalHigh;
    kpiTable.pedalInc(i) = pedalMax - pedalStart;
end
