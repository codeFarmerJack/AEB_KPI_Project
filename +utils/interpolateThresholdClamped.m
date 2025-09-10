function y = interpolateThresholdClamped(table, x_query)
% interpolateThresholdClampedFromTable - Interpolates from a 2-row calibratable with clamping
%
% Inputs:
%   table    - 2×N matrix where:
%              Row 1 = input breakpoints
%              Row 2 = corresponding threshold values
%   x_query  - Scalar input value to interpolate
%
% Output:
%   y        - Interpolated or clamped threshold value
 
    x_table = double(table{1, :});
    y_table = double(table{2, :});
    x_query_clamped = min(max(x_query, min(x_table)), max(x_table));
    y = interp1(x_table, y_table, x_query_clamped, 'linear');
end