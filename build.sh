#!/bin/bash
./tailwind/tailwindcss -o ./server/src/app/static/styles.css --minify
podman build -f containers/Containerfile.dev -t pywebtools:dev .
# podman build -f containers/Containerfile.prod -t pywebtools:prod .
