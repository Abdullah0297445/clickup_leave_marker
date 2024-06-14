include .env

build:
	docker build --platform linux/amd64 -t ${IMAGE_NAME}:latest .

run:
	docker run --platform linux/amd64 -p 8062:8080 -v .:/var/task --env-file .env ${IMAGE_NAME}:latest
