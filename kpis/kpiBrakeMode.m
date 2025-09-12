function kpiTable = kpiBrakeMode(obj, i, aebStartIdx)
    
    % Determine if PB and FB are activated during AEB event
    % Assuming PB is indicated by DADCAxLmtIT4 dropping below -6 and FB below -12
    %% Inputs:
    % signalMatChunk - Struct containing time-series data for the event
    % aebStartIdx    - Index of AEB request event
    % offset         - Offset to consider before aebStartIdx for analysis
    % PB_TGT_DECEL   - Target deceleration for PB in m/s²  
    % FB_TGT_DECEL   - Target deceleration for FB in m/s²
    % TGT_TOL        - Tolerance for target deceleration

    %% Outputs:
    % kpiTable       - Updated table with brake mode KPIs

    % bind variables from object
    kpiTable = obj.kpiTable; 
    signalMatChunk = obj.signalMatChunk;
    PB_TGT_DECEL = obj.PB_TGT_DECEL; 
    FB_TGT_DECEL = obj.FB_TGT_DECEL; 
    TGT_TOL = obj.TGT_TOL; 

    aebEndReq = length(signalMatChunk.Time); % Simplified: you can reuse your end-detection logic

    % Always check from AEB request to the end of recording
    segment = signalMatChunk.DADCAxLmtIT4(aebStartIdx:aebEndReq);

    % Find all PB / FB candidate indices
    pbIdx = find(abs(segment - PB_TGT_DECEL) <= TGT_TOL);
    fbIdx = find(abs(segment - FB_TGT_DECEL) <= TGT_TOL);

    % PB and FB status
    isPBOn = ~isempty(pbIdx);
    isFBOn = ~isempty(fbIdx);
    
    % Durations in seconds
    if isPBOn
        pbStart = aebStartIdx + pbIdx(1) - 1;   % convert back to global index
        pbEnd   = aebStartIdx + pbIdx(end) - 1;
        pbDur   = signalMatChunk.Time(pbEnd) - signalMatChunk.Time(pbStart);
        kpiTable.pbDur(i) = round(seconds(pbDur), 2);
    else
        kpiTable.pbDur(i) = 0;
    end

    if isFBOn
        fbStart = aebStartIdx + fbIdx(1) - 1;
        fbEnd   = aebStartIdx + fbIdx(end) - 1;
        fbDur   = signalMatChunk.Time(fbEnd) - signalMatChunk.Time(fbStart);
        kpiTable.fbDur(i) = round(seconds(fbDur), 2);
    else
        kpiTable.fbDur(i) = 0;
    end

    kpiTable.isPBOn(i) = isPBOn;
    kpiTable.isFBOn(i) = isFBOn;

end
