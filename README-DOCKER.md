# StringZ Docker Setup

## Quick Start (Recommended)
1. Install Docker Desktop from https://docker.com
2. Make sure Docker is running (look for Docker icon in system tray)
3. Double-click `run-docker.bat`
4. Wait for "Opening browser at http://localhost:5000"
5. Browser should open automatically

## Manual Commands (if batch files don't work)
```bash
# Build the image
docker build -t stringz .

# Run the container
docker run --rm -p 5000:5000 -v ./uploads:/app/uploads stringz
