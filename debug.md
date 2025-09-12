# Add the entire path string to MATLAB's search path
addpath(genpath('/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project'));

# Create a Config instance
cfg = Config.fromJSON('/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project/config/Config.json')

# Create an input handler
handler = InputHandler(cfg);

# Debug mdf2mat converter 
processedData = handler.processMF4Files();


# Process MF4 file 
processedData = handler.processMF4Files();

# AEB event detector 
eventDet = EventDetector()

eventDet.processAllFiles()


# KPIExtractor
By default, MATLAB classdef classes (like KPIExtractor) are value classes, meaning every time you assign to obj inside a method, MATLAB creates a copy, and when the method ends, those changes are not reflected in the original object (unless you explicitly return obj and reassign it).

extractor = KPIExtractor(cfg);
extractor = extractor.processAllMatFiles();
extractor.exportToCSV();

# Visualizer
viz = Visualizer(cfg)
