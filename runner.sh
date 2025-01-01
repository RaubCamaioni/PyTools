#!/bin/bash
docker run -it --rm --privileged \
	--env-file .secrets \
	--name pytools \
	-p 8080:8080 \
	-v $(pwd)/data:/data \
	pywebtools:latest