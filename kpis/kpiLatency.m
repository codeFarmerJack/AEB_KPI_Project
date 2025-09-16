function kpiLatency(obj, i, aebStartIdx)
    % AEB system latency
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Current index in the kpiTable
    % aebStartIdx    - Index of AEB request event

    % Use obj.kpiTable and obj.signalMatChunk directly
    kpiTable = obj.kpiTable;
    signalMatChunk = obj.signalMatChunk;
    cutoffFreq = obj.CUTOFF_FREQ;

    % Ensure required columns exist
    if ~ismember('m1IntvSysResp', kpiTable.Properties.VariableNames)
        obj.kpiTable.m1IntvSysResp = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('m1DeadTime', kpiTable.Properties.VariableNames)
        obj.kpiTable.m1DeadTime = NaN(height(obj.kpiTable), 1);
    end

    % Validate data range
    startIdx = aebStartIdx;
    endIdx = min(aebStartIdx + 30, length(signalMatChunk.time));
    if startIdx > endIdx
        warning('Invalid range for kneepoint detection at index %d. Setting m1IntvSysResp and m1DeadTime to NaN.', i);
        obj.kpiTable.m1IntvSysResp(i) = NaN;
        obj.kpiTable.m1DeadTime(i) = NaN;
        return;
    end

    % Detect kneepoint for AEB response
    [AEB_Resp, ~, ~] = utils.detectKneepoint_v4( ...
        signalMatChunk.time(startIdx:endIdx), ...
        signalMatChunk.longActAccel(startIdx:endIdx), ...
        'negative', cutoffFreq, 'curvature');
   
    % Calculate M0 and M1 with bounds check
    M0 = signalMatChunk.time(aebStartIdx);
    M1_idx = min(aebStartIdx + max(0, AEB_Resp), length(signalMatChunk.time) - 1);
    M1 = signalMatChunk.time(M1_idx);
    
    % Assign m1IntvSysResp with validation
    if isduration(M1)
        m1_value = seconds(M1);
    else
        m1_value = double(M1); % Handle numeric input
    end
    if ~isnan(m1_value) && isfinite(m1_value)
        obj.kpiTable.m1IntvSysResp(i) = round(m1_value, 2);
    else
        warning('Invalid M1 value for file index %d: %s. Setting m1IntvSysResp to NaN.', i, string(M1));
        obj.kpiTable.m1IntvSysResp(i) = NaN;
    end

    % Assign m1DeadTime with validation
    deadTime = M1 - M0;

    if isduration(deadTime)
        deadTime_value = seconds(deadTime);
    else
        deadTime_value = double(deadTime); % Handle numeric input
    end
    if ~isnan(deadTime_value) && isfinite(deadTime_value)
        obj.kpiTable.m1DeadTime(i) = round(deadTime_value, 2);
    else
        warning('Invalid deadTime value for file index %d: %s. Setting m1DeadTime to NaN.', i, string(deadTime));
        obj.kpiTable.m1DeadTime(i) = NaN;
    end

    % Display table row after assignment (convert to array first)
    rowData = table2array(obj.kpiTable(i, {'m1IntvSysResp', 'm1DeadTime'}));
end