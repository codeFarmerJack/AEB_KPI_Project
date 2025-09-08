function threshold = interpolate(dataTable, queryValue)
% interpolate - Interpolates a threshold value from a table
% Inputs:
%   dataTable   - A MATLAB table with two columns: 'Input' and 'Threshold'
%   queryValue  - The input value to query
% Output:
%   threshold   - Interpolated threshold value (clamped if out of range)

    % Extract input and threshold columns
    x = dataTable.Input;
    y = dataTable.Threshold;

    % Clamp queryValue to the range of x
    queryValue = max(min(queryValue, max(x)), min(x));

    % Perform linear interpolation
    threshold = interp1(x, y, queryValue, 'linear');
end
