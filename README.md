# AEB_KPI_Project
This project aims to develop a tool to extract AEB KPIs from data collected. read -> Processing -> output the results


AEB_Analysis/
├── MainScript.mlx                 % Live script entry point
├── classes/
│   ├── AEBPipeline.m             % Main class orchestrating the pipeline
│   ├── Config.m                   % Class for configuration (paths, registries)
│   ├── DataReader.m               % Class for reading MF4 files and thresholds
│   ├── EventDetector.m            % Class for detecting and segmenting AEB events
│   ├── KPIExtractor.m             % Class for extracting KPIs
│   ├── ThresholdComparator.m      % Class for comparing KPIs to thresholds
│   ├── ResultsExporter.m          % Class for exporting results to Excel
│   └── Visualizer.m               % Class for generating visualizations
├── kpis/
│   ├── KPI_TTC.m                  % KPI: Time to Collision
│   ├── KPI_MaxDecel.m             % KPI: Maximum Deceleration
│   └── KPI_BrakeTime.m            % KPI: Brake Response Time
├── visualization/
│   ├── Vis_KPIVsThresholdBar.m    % Visualization: Bar plot for KPIs vs thresholds
│   └── Vis_TimeSeries.m           % Visualization: Time-series plots
└── utils/
    └── MergeStructs.m             % Utility: Merges structs (for KPI aggregation)

**Explanation of Folder Structure**

 - **MainScript**.m: Entry point that instantiates AEBPipeline and runs the pipeline.
 - **classes**/: Contains class definitions for the core components. Each class encapsulates a specific part of the pipeline (e.g., reading data, extracting KPIs). Classes use composition or inheritance for extensibility.
 - **kpis**/: Contains classes for individual KPI extractors, inheriting from a base KPI class (defined in KPIExtractor.m). New KPIs are added as new subclasses.
 - **visualization**/: Contains classes for visualizations, inheriting from a base Visualization class (defined in Visualizer.m). New visualizations are added as new subclasses.
 - **utils**/: Same as before, holds helper functions like MergeStructs.m.
 - **Extensibility**:
    - New KPIs: Create a new class in kpis/ inheriting from KPI and add it to Config.kpiClasses.
    - New Visualizations: Create a new class in visualization/ inheriting from Visualization and add to Config.visualizationClasses.
    - New File Formats: Extend DataReader methods.
    - New Processing Logic: Extend or subclass EventDetector or ThresholdComparator.

%% AEB Event Analysis Pipeline
% This Live Script processes AEB (Autonomous Emergency Braking) events from MF4 files.
% It reads files, detects events, extracts KPIs, compares them to thresholds, exports results,
% and generates visualizations. The pipeline uses a class-based architecture for modularity
% and extensibility.

%% Initialize Environment
% Add all subfolders to the MATLAB path to access classes and utilities.
addpath(genpath('classes'));
addpath(genpath('kpis'));
addpath(genpath('visualization'));
addpath(genpath('utils'));

% Display confirmation
disp('Environment initialized. All subfolders added to MATLAB path.');

%% Create AEB Processor
% Instantiate the AEBPipeline class, which orchestrates the pipeline.
processor = AEBPipeline();
disp('AEBPipeline instantiated with configuration:');
disp(processor.config);

%% Run the Pipeline
% Process MF4 files, extract KPIs, compare to thresholds, export to Excel, and visualize.
% Results are stored in processor.resultsTable.
processor.run();

% Display the results table (first few rows for inspection)
disp('Results Table (first 5 rows):');
if height(processor.resultsTable) > 0
    head(processor.resultsTable, 5)
else
    disp('No results generated. Check input files or event detection.');
end

%% Notes
% * To add new KPIs, create a new class in the 'kpis/' folder and update Config.kpiClasses.
% * To add new visualizations, create a new class in 'visualization/' and update Config.visualizationClasses.
% * Check the generated Excel file and visualization outputs in the configured output folder.
% * Use the Live Editor to interactively modify parameters or debug specific sections.
