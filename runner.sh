#!/bin/bash
docker run -it --rm --privileged \
	--env-file .secrets \
	-p 8080:8080 \
	-v $(pwd)/data:/data \
	sandbox:isolate