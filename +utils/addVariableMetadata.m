function [var_name, var_type, sz] = addVariableMetadata(var_name, var_type, sz, newVarName, newVarType)
%ADDVARIABLEMETADATA Adds a new variable name and type, and updates the size
%   Inputs:
%       var_name   - Existing cell array of variable names
%       var_type   - Existing cell array of variable types
%       sz         - Existing size array [N, x]
%       newVarName - New variable name to add (string or char)
%       newVarType - New variable type to add ('double', 'logical', 'string', etc.)
%   Outputs:
%       var_name   - Updated list of variable names
%       var_type   - Updated list of variable types
%       sz         - Updated size [N, x+1]
 
    % Append new variable name and type
    var_name{end+1} = newVarName;
    var_type{end+1} = newVarType;
 
    % Update size
    sz(2) = sz(2) + 1;
end