# Navigate to the project folder
docker build -t mdf-python .

## Rebuild the image (skip cache) - Force Docker to rebuild and re-copy the file
docker build --no-cache -t mdf-python .

# Run the container interactively 
docker run -it mdf-python /bin/bash



docker run --rm -v /Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor:/data \
    mdf-python:latest \
    python /data/AEB_KPI_Project/pipeline/mdf2matSim.py \
        /data/rawdata/roadcast_debug_converted.mf4 \
        --signal_db /data/mdf_project/signalDatabase.csv \
        --resample 0.01