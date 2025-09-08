function calibratables = extractCalibratables(calStruct)
% ExtractCalibratables - Flattens nested calibratable struct and extracts .Data fields
% Input:
%   calStruct - Struct with nested calibratable categories and signals
% Output:
%   calibratables - Flat struct with signal names as fields and .Data arrays as values

    calibratables = struct();  % Initialize output

    % Loop through top-level categories (e.g., steering, throttle, etc.)
    categories = fieldnames(calStruct);
    for i = 1:numel(categories)
        categoryStruct = calStruct.(categories{i});
        signals = fieldnames(categoryStruct);

        % Loop through each signal in the category
        for j = 1:numel(signals)
            signalName = signals{j};
            signalStruct = categoryStruct.(signalName);

            % Check if .Data field exists
            if isfield(signalStruct, 'Data')
                calibratables.(signalName) = signalStruct.Data;
            else
                warning('Skipping "%s" in "%s": no .Data field found.', signalName, categories{i});
            end
        end
    end
end
