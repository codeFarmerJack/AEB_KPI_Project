function kpiDistance(obj, i, aebStartIdx, aebEndIdx)
    % Determine if PB and FB are activated during AEB event
    % Assuming PB is indicated by aebTargetDecel dropping below -6 and FB below -12
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Index of the file in kpiTable
    % aebStartIdx    - Index of AEB request event
    % aebEndIdx      - Index of AEB end event
    %% Outputs:
    % kpiTable       - Updated table with distance KPIs (for consistency)   

    % Bind signal data and longGap
    longGap = obj.signalMatChunk.longGap;

    % Ensure required columns exist in obj.kpiTable
    if ~ismember('firstDetDist', obj.kpiTable.Properties.VariableNames)
        obj.kpiTable.firstDetDist = NaN(height(obj.kpiTable), 1);    
    end
    if ~ismember('stableDetDist', obj.kpiTable.Properties.VariableNames)
        obj.kpiTable.stableDetDist = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('aebIntvDist', obj.kpiTable.Properties.VariableNames)
        obj.kpiTable.aebIntvDist = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('aebStopGap', obj.kpiTable.Properties.VariableNames)
        obj.kpiTable.aebStopGap = NaN(height(obj.kpiTable), 1);
    end

    % Consider the segment up to end of AEB event
    segment = longGap(1:aebEndIdx);

    % Calculate firstDetDist: First non-zero distance
    firstNonZeroIdx = find(segment ~= 0, 1, 'first');
    if ~isempty(firstNonZeroIdx)
        obj.kpiTable.firstDetDist(i) = longGap(firstNonZeroIdx);
    else
        obj.kpiTable.firstDetDist(i) = NaN;
    end

    % Calculate stableDetDist: Distance at the satrt of the last continuous non-zero segment before aebEndIdx
    lastNonZeroIdx = find(segment ~= 0, 1, 'last');
    if ~isempty(lastNonZeroIdx)
        trimmed = segment(1:lastNonZeroIdx);
        lastZeroIdx = find(trimmed == 0, 1, 'last');
        if isempty(lastZeroIdx)
            stableIdx = firstNonZeroIdx;
        else
            stableIdx = lastZeroIdx + 1;
        end
        obj.kpiTable.stableDetDist(i) = segment(stableIdx);
    else
        obj.kpiTable.stableDetDist(i) = NaN;
    end

    obj.kpiTable.aebIntvDist(i) = longGap(aebStartIdx);
    obj.kpiTable.aebStopGap(i) = longGap(aebEndIdx);
end