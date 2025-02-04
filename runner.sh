#!/bin/bash

docker run -it --rm --privileged \
  --env-file .env \
  -e DATABASE=/data/database.db \
  --name pytools_test \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -v $(pwd)/src:/app \
  pywebtools:dev
