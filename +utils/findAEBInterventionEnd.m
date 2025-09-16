function [isVehStopped, aebEndIdx, M2] = findAEBInterventionEnd(obj, aebStartIdx)

    % Check for actuation end and vehicle stop
    %% Input:
    % obj           - Object containing signalMatChunk
    % aebStartIdx   - Index of AEB request event
    %% Output:
    % aebEndIdx     - Index of AEB intervention end
    % M2            - Timestamp of AEB intervention end 
    % isVehStopped  - Boolean indicating if vehicle stopped during intervention

    % bind variables from object
    signalMatChunk = obj.signalMatChunk;
    AEB_END_THD = obj.AEB_END_THD;

    isIntvEnd = ~isempty(find(signalMatChunk.aebTargetDecel(aebStartIdx:end) > AEB_END_THD, 1));
    % the window to check if vehicle stopped: from AEB start to intervention end
    intvEndIdxTmp = find(signalMatChunk.aebTargetDecel(aebStartIdx:end) > AEB_END_THD, 1) + aebStartIdx;
    isVehStopped = ~isempty(find(signalMatChunk.egoSpeed(aebStartIdx:intvEndIdxTmp) == 0, 1));

    if isIntvEnd && isVehStopped
        aebEndIdx = min(...
                        find(signalMatChunk.egoSpeed(aebStartIdx:end) == 0, 1) + aebStartIdx, ...
                        find(signalMatChunk.aebTargetDecel(aebStartIdx:end) > AEB_END_THD, 1) + aebStartIdx ...
                        );
    elseif ~isIntvEnd && isVehStopped
        aebEndIdx = find(signalMatChunk.egoSpeed(aebStartIdx:end) == 0, 1) + aebStartIdx;
    elseif isIntvEnd && ~isVehStopped
        aebEndIdx = find(signalMatChunk.aebTargetDecel(aebStartIdx:end) > AEB_END_THD, 1) + aebStartIdx;
    else
        aebEndIdx = length(signalMatChunk.time);
    end

    M2 = signalMatChunk.time(aebEndIdx);

end