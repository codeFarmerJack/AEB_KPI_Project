FROM python:3.10

WORKDIR /data

# Install system dependencies for scipy
RUN apt-get update && apt-get install -y \
    libblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install asammdf scipy pandas argparse numpy 

# Create utils directory and copy script
RUN mkdir -p /data/AEB_KPI_Project/pipeline
COPY pipeline/mdf2matSim.py /data/AEB_KPI_Project/pipeline/mdf2matSim.py
RUN chmod +x /data/AEB_KPI_Project/pipeline/mdf2matSim.py

CMD ["bash"]