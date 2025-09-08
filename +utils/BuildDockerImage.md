# Navigate to the project folder
docker build -t mdf-python .

## Rebuild the image (skip cache) - Force Docker to rebuild and re-copy the file
docker build --no-cache -t mdf-python .

# Run the container interactively 
docker run -it mdf-python /bin/bash
