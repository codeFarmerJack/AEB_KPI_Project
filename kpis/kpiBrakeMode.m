function kpiBrakeMode(obj, i, aebStartIdx)
    % Determine if PB and FB are activated during AEB event
    % Assuming PB is indicated by aebTargetDecel dropping below -6 and FB below -12
    %% Inputs:
    % obj            - KPIExtractor object
    % i              - Index of the file in kpiTable
    % aebStartIdx    - Index of AEB request event

    % Use obj.kpiTable and obj.signalMatChunk directly
    kpiTable        = obj.kpiTable;
    signalMatChunk  = obj.signalMatChunk;
    PB_TGT_DECEL    = obj.PB_TGT_DECEL;
    FB_TGT_DECEL    = obj.FB_TGT_DECEL;
    TGT_TOL         = obj.TGT_TOL;

    aebEndReq = length(signalMatChunk.time); % Simplified: you can reuse your end-detection logic

    % Ensure required columns exist
    if ~ismember('pbDur', kpiTable.Properties.VariableNames)
        obj.kpiTable.pbDur = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('fbDur', kpiTable.Properties.VariableNames)
        obj.kpiTable.fbDur = NaN(height(obj.kpiTable), 1);
    end
    if ~ismember('isPBOn', kpiTable.Properties.VariableNames)
        obj.kpiTable.isPBOn = false(height(obj.kpiTable), 1);
    end
    if ~ismember('isFBOn', kpiTable.Properties.VariableNames)
        obj.kpiTable.isFBOn = false(height(obj.kpiTable), 1);
    end

    % Always check from AEB request to the end of recording
    segment = signalMatChunk.aebTargetDecel(aebStartIdx:aebEndReq);

    % Find all PB / FB candidate indices
    pbIdx = find(abs(segment - PB_TGT_DECEL) <= TGT_TOL);
    fbIdx = find(abs(segment - FB_TGT_DECEL) <= TGT_TOL);

    % PB and FB status
    isPBOn = ~isempty(pbIdx);
    isFBOn = ~isempty(fbIdx);
    
    % Durations in seconds
    if isPBOn
        pbStart = aebStartIdx + pbIdx(1) - 1;   % Convert back to global index
        pbEnd   = aebStartIdx + pbIdx(end) - 1;
        pbDur = signalMatChunk.time(pbEnd) - signalMatChunk.time(pbStart);
        if isduration(pbDur)
            pbDur_value = seconds(pbDur);
        else
            pbDur_value = double(pbDur); % Handle numeric input
        end
        if ~isnan(pbDur_value) && isfinite(pbDur_value)
            obj.kpiTable.pbDur(i) = round(pbDur_value, 2);
        else
            warning('Invalid pbDur value for file index %d: %s. Setting pbDur to 0.', i, string(pbDur));
            obj.kpiTable.pbDur(i) = 0;
        end
    else
        obj.kpiTable.pbDur(i) = 0;
    end

    if isFBOn
        fbStart = aebStartIdx + fbIdx(1) - 1;
        fbEnd   = aebStartIdx + fbIdx(end) - 1;
        fbDur = signalMatChunk.time(fbEnd) - signalMatChunk.time(fbStart);
        if isduration(fbDur)
            fbDur_value = seconds(fbDur);
        else
            fbDur_value = double(fbDur); % Handle numeric input
        end
        if ~isnan(fbDur_value) && isfinite(fbDur_value)
            obj.kpiTable.fbDur(i) = round(fbDur_value, 2);
        else
            warning('Invalid fbDur value for file index %d: %s. Setting fbDur to 0.', i, string(fbDur));
            obj.kpiTable.fbDur(i) = 0;
        end
    else
        obj.kpiTable.fbDur(i) = 0;
    end

    obj.kpiTable.isPBOn(i) = isPBOn;
    obj.kpiTable.isFBOn(i) = isFBOn;
end