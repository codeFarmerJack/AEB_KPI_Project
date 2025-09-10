function kpiTable = createKpiTableFromJson(jsonFile, N)
% createKpiTableFromJson  Create KPI table based on JSON schema
%
%   kpiTable = createKpiTableFromJson(jsonFile, N)
%
%   Inputs:
%     jsonFile - Path to JSON file containing variable definitions
%     N        - Number of rows (optional). Default = 0 (empty table).
%
%   Output:
%     kpiTable - MATLAB table with specified variables

    if nargin < 2
        N = 0; % default to empty table
    end

    % Read JSON schema
    fid = fopen(jsonFile, 'r');
    raw = fread(fid, inf, 'uint8=>char')';
    fclose(fid);
    schema = jsondecode(raw);

    % Extract variable names and types
    vars = schema.variables;
    varName = {vars.name};
    varType = {vars.type};

    % Define table size
    sz = [N, numel(varName)];

    % Create table
    kpiTable = table('Size', sz, ...
                     'VariableTypes', varType, ...
                     'VariableNames', varName);
end
