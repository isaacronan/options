docker network rm options-network
docker network create options-network
docker image rm options-image
docker build -t options-image .
