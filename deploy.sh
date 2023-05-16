#!/usr/bin/bash

separator_with_terminators() {
  columns_count=$(tput cols)
  ((columns_count=columns_count-2))
  printf ">"
  printf %"$columns_count"s |tr " " "$1"
  printf "<\n"
}

separator() {
  columns_count=$(tput cols)
  printf %"$columns_count"s |tr " " "$1"
  printf "\n"
}

shutdown() {
  separator '='
  echo ""
  echo "Shutdown:"
  separator_with_terminators '-'
  docker compose down
  separator '='
}

GLACIER_USER=qwerty
GLACIER_PASSWORD=12345

trap "shutdown; exit 1" SIGINT
echo "Build:"
separator_with_terminators '-'
docker compose up --build -d
sleep 1
separator '='
echo ""
echo "Server logs:"
separator_with_terminators '-'
docker exec -it glacierrender-backend-1 bash -c "GLACIER_USER=$GLACIER_USER GLACIER_PASSWORD=$GLACIER_PASSWORD python useradd.py"
docker logs --follow glacierrender-backend-1
shutdown
