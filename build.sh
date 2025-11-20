#!/bin/bash
tailwindcss -i server/src/app/webapp/static/input.css -o server/src/app/webapp/static/output.css --minify
podman build -f containers/Containerfile.dev -t pywebtools:dev .
# podman build -f containers/Containerfile.prod -t pywebtools:prod .
