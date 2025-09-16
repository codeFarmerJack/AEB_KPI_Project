function [val, idx] = findDuration(time_vector, duration_value)
%   findDuration - Find the time value in time_vector closest to duration_value
%   Usage:
%       [val, idx] = findDuration(time_vector, duration_value)      
%   Inputs:     
%       time_vector    - Vector of time values (numeric or duration)
%       duration_value - Target duration value (numeric or duration)            
%   Outputs:
%       val - The time value in time_vector closest to duration_value
%       idx - The index of val in time_vector

    % Ensure duration_value is numeric (convert from duration if needed)
    if isduration(duration_value)
        duration_value = seconds(duration_value);
    end
    
    % Compute absolute differences and find minimum
    differences = abs(time_vector - duration_value);
    [~, idx] = min(differences);
    val = time_vector(idx); % Return actual time value, not the difference
end