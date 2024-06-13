include .env

build:
	docker build --platform linux/amd64 -t $IMAGE_NAME:latest .

run:
	docker run --platform linux/amd64 -p 8062:8080 $IMAGE_NAME:latest

push:
	./scripts/push.sh

# Build and Push
bp: build push
