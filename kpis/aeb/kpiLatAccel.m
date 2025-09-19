function kpiLatAccel(obj, i, aebStartIdx, latAccelTh)
    % Lateral acceleration
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Current index in the kpiTable
    % aebStartIdx    - Index of AEB request event
    % latAccelTh     - Threshold for lateral acceleration in m/s²

    % Use obj.kpiTable and obj.signalMatChunk directly
    kpiTable        = obj.kpiTable;
    signalMatChunk  = obj.signalMatChunk;
    offset          = obj.TIME_IDX_OFFSET;

    % Ensure required columns exist
    if ~ismember('latAccelMax', kpiTable.Properties.VariableNames)
        obj.kpiTable.latAccelMax = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('absLatAccelMax', kpiTable.Properties.VariableNames)
        obj.kpiTable.absLatAccelMax = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('isLatAccelHigh', kpiTable.Properties.VariableNames)
        obj.kpiTable.isLatAccelHigh = false(height(obj.kpiTable), 1);
    end

    % Calculate lateral acceleration KPIs
    [~, idx] = max(abs(signalMatChunk.A1_Filt(aebStartIdx - offset:end)));
    latAccelMax = signalMatChunk.A1_Filt(aebStartIdx - offset + idx - 1);
    absLatAccelMax = abs(latAccelMax);

    obj.kpiTable.latAccelMax(i) = latAccelMax;
    obj.kpiTable.absLatAccelMax(i) = absLatAccelMax;
    obj.kpiTable.isLatAccelHigh(i) = absLatAccelMax > latAccelTh;
end