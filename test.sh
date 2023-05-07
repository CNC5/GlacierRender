#!/usr/bin/bash

trap "docker compose down" SIGINT
docker compose up --build -d
sleep 1
docker exec -it glacierrender-glacier-backend-1 bash -c "python authenticator.py"
docker logs --follow glacierrender-glacier-backend-1
docker compose down
