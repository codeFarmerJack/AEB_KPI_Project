function [val,idx] = find_duration(time_vector,duration_value)

[val,idx] = min(abs(time_vector - duration_value));

end

