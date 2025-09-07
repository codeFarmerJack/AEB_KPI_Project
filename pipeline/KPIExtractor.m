classdef KPIExtractor
    properties
        KPIList   % Cell array of KPI function handles or names
    end

    methods
        function obj = KPIExtractor(kpiNames)
            % Constructor: accepts a list of KPI module names
            if nargin < 1
                % Default to all available KPIs
                obj.KPIList = {'KPI_TTC', 'KPI_MaxDecel', 'KPI_BrakeTime'};
            else
                obj.KPIList = kpiNames;
            end
        end

        function kpiResults = extractKPIs(obj, eventData)
            % Main method to extract KPIs from eventData
            kpiResults = struct();

            for i = 1:length(obj.KPIList)
                kpiName = obj.KPIList{i};

                try
                    % Dynamically call the KPI function
                    kpiFunc = str2func(kpiName);
                    result = kpiFunc(eventData);

                    % Store result in struct
                    kpiResults.(kpiName) = result;
                catch ME
                    warning('Failed to extract %s: %s', kpiName, ME.message);
                    kpiResults.(kpiName) = NaN;
                end
            end
        end
    end
end
