classdef AEBProcessor
    properties
        Config              % Instance of Config class
        InputHandler        % Handles raw data loading
        EventDetector       % Segments raw data into AEB events
        KPIExtractor        % Extracts KPIs from each event
        ThresholdComparator % Compares KPIs to thresholds
        Visualizer          % Generates plots
    end

    methods
        function obj = AEBProcessor(configPath)
            % Initialize pipeline components
            obj.Config = Config(configPath);
            obj.InputHandler = InputHandler(obj.Config);
            obj.Visualizer = Visualizer('Plots');
        end

        function run(obj)
            % Step 1: Load raw data
            rawData = obj.InputHandler.loadRawData();

            % Step 2: Detect and segment AEB events
            obj.EventDetector = EventDetector(rawData, obj.Config.get('EventField'));
            eventFiles = obj.EventDetector.segmentAndSaveEvents();

            % Step 3: Initialize KPI extractor
            kpiModules = obj.Config.get('KPIList');
            obj.KPIExtractor = KPIExtractor(kpiModules);

            % Step 4: Process each event
            allResults = [];
            for i = 1:length(eventFiles)
                eventStruct = load(eventFiles{i});
                eventData = eventStruct.eventData;

                % Extract KPIs
                kpiResult = obj.KPIExtractor.extractKPIs(eventData);

                % Compare to thresholds
                obj.ThresholdComparator = ThresholdComparator(obj.Config);
                comparison = obj.ThresholdComparator.compare(kpiResult);

                % Store results
                allResults = [allResults; comparison]; %#ok<AGROW>
            end

            % Step 5: Export results
            OutputHandler.saveResults(allResults, 'Results/AEB_KPI_Results.xlsx');

            % Step 6: Visualize
            visConfig = obj.InputHandler.loadVisualizationConfig();
            obj.Visualizer.plotScatter(visConfig, 'Results');
        end
    end
end
