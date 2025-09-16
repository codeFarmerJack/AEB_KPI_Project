function [aebStartIdx, M0] = findAEBInterventionStart(obj)
    % Locate AEB intervention start
    %% Input:
    % obj           - Object containing signalMatChunk
    %% Output:
    % aebStartIdx   - Index of AEB request event    
    % M0            - Timestamp of AEB intervention start
    
    % Check aebTargetDecel
    if ~isfield(obj.signalMatChunk, 'aebTargetDecel')
        aebStartIdx = [];
        M0 = [];
        return;
    end

    % Find AEB start index
    [aebStartIdx, ~, ~] = utils.findFirstLastIndicesAdvanced(...
        obj.signalMatChunk.aebTargetDecel, obj.PB_TGT_DECEL, 'less', 0.1);
    
    if ~isempty(aebStartIdx)
        M0 = obj.signalMatChunk.time(aebStartIdx(1));
    else
        M0 = [];
    end
end