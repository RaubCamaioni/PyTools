#!/bin/bash
./tailwind/tailwindcss -i ./tailwind/styles.css -c ./tailwind/tailwind.config.js -o ./src/app/static/styles.css --minify
docker build -f docker/Dockerfile.dev -t pywebtools:dev .
docker build -f docker/Dockerfile.prod -t pywebtools:prod .
