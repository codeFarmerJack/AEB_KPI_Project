function [val,idx] = findDuration(time_vector,duration_value)

[val,idx] = min(abs(time_vector - duration_value));

end

