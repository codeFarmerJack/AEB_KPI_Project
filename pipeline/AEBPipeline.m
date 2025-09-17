classdef AEBPipeline < handle
    % AEBPipeline: Orchestrates AEB data processing pipeline
    %
    % Chains Config, InputHandler, EventDetector, KPIExtractor, and Visualizer
    % to process MF4 files, detect AEB events, extract KPIs, and visualize results.
    
    properties
        Config        % Instance of Config class
        InputHandler  % Handles raw data loading
        EventDetector % Segments raw data into AEB events
        KPIExtractor  % Extracts KPIs from each event
        Visualizer    % Generates plots
    end
    
    methods
        function obj = AEBPipeline(configPath)
            % Constructor: Initialize pipeline components
            %
            % Inputs:
            %   configPath - Path to the Config JSON file
            
            if nargin < 1
                error('Configuration file path is required.');
            end
            validateattributes(configPath, {'char', 'string'}, {'nonempty'}, ...
                'AEBPipeline', 'configPath');
            
            % Step 1: Add project path to MATLAB path
            projectRoot = '/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project';
            addpath(genpath(projectRoot));
            fprintf('Added project path: %s\n', projectRoot);
            
            % Step 2: Create Config instance
            try
                obj.Config = Config.fromJSON(configPath);
            catch err
                error('Failed to create Config instance: %s', err.message);
            end
            
            % Step 3: Create InputHandler instance
            try
                obj.InputHandler = InputHandler(obj.Config);
            catch err
                error('Failed to create InputHandler instance: %s', err.message);
            end
        end
        
        function run(obj)
            % Run the AEB processing pipeline
            %
            % Executes the pipeline steps: process MF4 files, detect AEB events,
            % extract KPIs, export to CSV, and visualize results.
            
            % Step 4: Process MF4 files
            fprintf('Processing MF4 files...\n');
            try
                processedData = obj.InputHandler.processMF4Files();
                if isempty(processedData)
                    warning('No data processed from MF4 files. Aborting pipeline.');
                    return;
                end
            catch err
                error('Failed to process MF4 files: %s', err.message);
            end
            
            % Step 5: Create EventDetector and process files
            fprintf('Detecting AEB events...\n');
            try
                obj.EventDetector = EventDetector(obj.InputHandler);
                obj.EventDetector.processAllFiles();
            catch err
                error('Failed to process AEB events: %s', err.message);
            end
            
            % Step 6: Create KPIExtractor, process mat files, and export to CSV
            fprintf('Extracting KPIs and exporting to CSV...\n');
            try
                obj.KPIExtractor = KPIExtractor(obj.Config, obj.EventDetector);
                obj.KPIExtractor = obj.KPIExtractor.processAllMatFiles();
                obj.KPIExtractor.exportToCSV();
            catch err
                error('Failed to extract KPIs or export to CSV: %s', err.message);
            end
            
            % Step 7: Create Visualizer and plot results
            fprintf('Generating visualizations...\n');
            try
                obj.Visualizer = Visualizer(obj.Config, obj.KPIExtractor);
                obj.Visualizer.plot();
            catch err
                error('Failed to generate visualizations: %s', err.message);
            end
            
            fprintf('✅ AEB processing pipeline completed successfully.\n');
        end
    end
end