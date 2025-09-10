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


