#!/bin/bash
./tailwind/tailwindcss -i ./tailwind/styles.css -c ./tailwind/tailwind.config.js  -o ./src/app/static/styles.css --minify
docker build -t pywebtools:latest .