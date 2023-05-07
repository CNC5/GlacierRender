#!/usr/bin/bash

trap "docker compose down" SIGINT
docker compose up --build -d
sleep 1
docker exec -it glacierrender-glacier-backend-1 bash -c "GLACIER_USER=qwerty GLACIER_PASSWORD=12345 python useradd.py"
docker logs --follow glacierrender-glacier-backend-1
docker compose down
