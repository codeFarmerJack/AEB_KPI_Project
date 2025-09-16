function kpiThrottle(obj, i, aebStartIdx, pedalPosIncTh)
    % Throttle pedal analysis
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Current index in the kpiTable
    % aebStartIdx    - Index of AEB request event
    % pedalPosIncTh  - Threshold for pedal position increase   
    %% Outputs:
    % kpiTable       - Updated table with throttle pedal KPIs (for consistency)

    % Use obj.kpiTable directly
    kpiTable = obj.kpiTable;

    % Ensure required columns exist
    if ~ismember('pedalStart', kpiTable.Properties.VariableNames)
        obj.kpiTable.pedalStart = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('pedalMax', kpiTable.Properties.VariableNames)
        obj.kpiTable.pedalMax = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('pedalInc', kpiTable.Properties.VariableNames)
        obj.kpiTable.pedalInc = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('isPedalHigh', kpiTable.Properties.VariableNames)
        obj.kpiTable.isPedalHigh = false(height(obj.kpiTable), 1);
    end
    if ~ismember('isPedalOnAtStrt', kpiTable.Properties.VariableNames)
        obj.kpiTable.isPedalOnAtStrt = false(height(obj.kpiTable), 1);
    end

    % Bind signal data
    signalMatChunk = obj.signalMatChunk;

    % Validate throttleValue
    if ~isfield(signalMatChunk, 'throttleValue')
        obj.kpiTable.pedalStart(i) = NaN;
        obj.kpiTable.pedalMax(i) = NaN;
        obj.kpiTable.pedalInc(i) = NaN;
        obj.kpiTable.isPedalHigh(i) = false;
        obj.kpiTable.isPedalOnAtStrt(i) = false;
        return;
    end

    if isempty(aebStartIdx) || aebStartIdx < 1 || aebStartIdx > length(signalMatChunk.throttleValue)
        obj.kpiTable.pedalStart(i) = NaN;
        obj.kpiTable.pedalMax(i) = NaN;
        obj.kpiTable.pedalInc(i) = NaN;
        obj.kpiTable.isPedalHigh(i) = false;
        obj.kpiTable.isPedalOnAtStrt(i) = false;
        return;
    end

    % Calculate and assign throttle KPIs
    pedalStart = signalMatChunk.throttleValue(aebStartIdx);
    obj.kpiTable.pedalStart(i) = pedalStart;
    obj.kpiTable.isPedalOnAtStrt(i) = logical(pedalStart ~= 0);

    % Check for non-zero throttle values after aebStartIdx
    throttleRange = signalMatChunk.throttleValue(aebStartIdx:end);
    pedalMax = max(throttleRange);
    obj.kpiTable.pedalMax(i) = pedalMax;

    pedalInc = pedalMax - pedalStart;
    obj.kpiTable.pedalInc(i) = pedalInc;
    isPedalHigh = pedalInc > pedalPosIncTh;
    obj.kpiTable.isPedalHigh(i) = isPedalHigh;
end