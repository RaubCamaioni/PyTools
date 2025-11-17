#!/bin/bash
podman run --rm -it \
    --cap-add=CAP_SYS_ADMIN \
    --cap-add=CAP_NET_ADMIN \
    -p 8080:8080 \
    -v /tmp/data:/data \
    -v .secrets:/root/.secrets:z \
    --name pytools \
    pywebtools:dev