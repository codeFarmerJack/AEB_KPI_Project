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
    %     kpiTable - MATLAB table with specified variables and units stored in UserData

    if nargin < 2
        N = 0; % default to empty table
    end

    % Validate and resolve file path
    if ~exist(jsonFile, 'file')
        error('JSON file not found or inaccessible: %s. Check the path and permissions.', jsonFile);
    end

    % Read JSON schema
    fid = fopen(jsonFile, 'r');
    if fid == -1
        error('Failed to open JSON file: %s. Ensure the file exists and you have read permissions.', jsonFile);
    end
    raw = fread(fid, inf, 'uint8=>char')';
    fclose(fid);
    schema = jsondecode(raw);

    % Extract variable names, types, and units
    if ~isfield(schema, 'variables') || isempty(schema.variables)
        error('JSON schema is missing or empty "variables" field in %s.', jsonFile);
    end
    vars = schema.variables;
    varName = {vars.name};
    varType = lower({vars.type}); % Convert to lowercase for case-insensitive matching
    varUnit = cell(size(varName));
    for i = 1:length(vars)
        varUnit{i} = '';
        if isfield(vars(i), 'unit') && ~isempty(vars(i).unit)
            varUnit{i} = vars(i).unit;
        end
    end

    % Create display names with units
    varDisplayName = cell(size(varName));
    for i = 1:length(varName)
        if isempty(varUnit{i})
            varDisplayName{i} = varName{i};
        else
            varDisplayName{i} = sprintf('%s [%s]', varName{i}, varUnit{i});
        end
    end

    % Validate and map types to MATLAB equivalents
    validTypes = {'string', 'double', 'logical'};
    initialValues = cell(size(varType));
    for i = 1:length(varType)
        if ~ismember(varType{i}, validTypes)
            warning('Unsupported type "%s" for variable "%s" in %s. Defaulting to double.', varType{i}, varName{i}, jsonFile);
            varType{i} = 'double';
        end
        switch varType{i}
            case 'string'
                initialValues{i} = strings(N, 1); % Use strings(N, 1) for string array
            case 'double'
                initialValues{i} = NaN(N, 1);
            case 'logical'
                initialValues{i} = false(N, 1);
        end
    end

    % Create table with original variable names
    kpiTable = table('Size', [N, numel(varName)], ...
                     'VariableTypes', varType, ...
                     'VariableNames', varName);
    
    % Assign initial values (table constructor may not always respect defaults)
    for i = 1:length(varName)
        kpiTable.(varName{i}) = initialValues{i};
    end

    % Store display names with units in UserData for export
    kpiTable.Properties.UserData.displayNames = varDisplayName;

    % Verify all variables are created
    if ~all(ismember(varName, kpiTable.Properties.VariableNames))
        missingVars = setdiff(varName, kpiTable.Properties.VariableNames);
        error('Failed to create variables: %s in %s', strjoin(missingVars, ', '), jsonFile);
    end
end