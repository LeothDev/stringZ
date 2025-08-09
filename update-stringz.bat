@echo off
echo Updating StringZ...
docker pull leothdev/stringz:latest
docker stop stringz-container 2>nul
docker rm stringz-container 2>nul
docker run -d --name stringz-container -p 5000:5000 leothdev/stringz:latest
echo StringZ updated! Visit http://localhost:5000
pause
