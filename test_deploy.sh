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
}

trap "shutdown; exit 1" SIGINT
echo "Build:"
separator_with_terminators '-'
docker compose up --build -d
sleep 1
docker exec -it glacierrender-backend-1 bash -c "GLACIER_USER=qwerty GLACIER_PASSWORD=12345 python useradd.py"
separator '='
echo ""
echo "Frontend logs:"
separator_with_terminators '-'
python general_test.py
separator '='
echo ""
echo "Server logs:"
separator_with_terminators '-'
docker logs glacierrender-backend-1
shutdown