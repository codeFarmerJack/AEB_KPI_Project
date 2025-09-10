function [firstIdx, lastIdx, allIdx] = findFirstLastIndicesAdvanced(vector, targetValue, comparisonMode, tolerance)
% findFirstLastIndicesAdvanced - Finds first and last indices of values matching a condition with optional tolerance.
%
% Syntax:
%   [firstIdx, lastIdx, allIdx] = findFirstLastIndicesAdvanced(vector, targetValue, comparisonMode, tolerance)
%
% Inputs:
%   vector         - Numeric vector to search
%   targetValue    - Value to compare against
%   comparisonMode - 'equal', 'less', or 'greater'
%   tolerance      - Optional tolerance (default is 0)
%
% Outputs:
%   firstIdx       - Index of first match
%   lastIdx        - Index of last match
%   allIdx         - All matching indices
 
    if nargin < 4
        tolerance = 0;
    end
 
    switch lower(comparisonMode)
        case 'equal'
            condition = abs(vector - targetValue) <= tolerance;
        case 'less'
            condition = vector < (targetValue + tolerance);
        case 'greater'
            condition = vector > (targetValue - tolerance);
        otherwise
            error('Invalid comparisonMode. Use ''equal'', ''less'', or ''greater''.');
    end
 
    allIdx = find(condition);
 
    if isempty(allIdx)
        firstIdx = NaN;
        lastIdx = NaN;
        warning('No matching values found.');
    else
        firstIdx = allIdx(1);
        lastIdx = allIdx(end);
    end
end