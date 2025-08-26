#!/bin/bash
./tailwind/tailwindcss -i ./tailwind/styles.css -c ./tailwind/tailwind.config.js -o ./src/app/static/styles.css --minify
podman build -f containers/Containerfile.dev -t pywebtools:dev .
# podman build -f containers/Containerfile.prod -t pywebtools:prod .
