#!/bin/bash
podman run --rm -it \
    --systemd=always \
    --cgroupns=private \
    -p 8080:8080 \
    -v .secrets:/root/.secrets:z \
    --name pytools \
    pywebtools:dev