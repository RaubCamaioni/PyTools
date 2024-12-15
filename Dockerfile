FROM mambaorg/micromamba:2.0.2

USER root

RUN apt-get update && apt install -y \
    libgl1-mesa-glx \
    libcap-dev \
    pkg-config \
    libsystemd-dev \ 
    asciidoc-base \
    build-essential \
    git

RUN cd /tmp && \
    git clone https://github.com/ioi/isolate.git && \
    cd isolate && \
    make && \
    make install && \
    cd / && rm -rf /tmp/isolate && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir /sandbox
RUN chown $MAMBA_USER:$MAMBA_USER /sandbox

USER $MAMBA_USER
    
COPY --chown=$MAMBA_USER:$MAMBA_USER sandbox/sandbox.yaml /tmp/sandbox.yaml
RUN micromamba create -y --prefix /sandbox/venv python=3.12 && \
    micromamba install -y --prefix /sandbox/venv -f /tmp/sandbox.yaml

COPY --chown=$MAMBA_USER:$MAMBA_USER sandbox/app.yaml /tmp/app.yaml
RUN micromamba install -y -n base -f /tmp/app.yaml && \
    micromamba clean --all --yes

COPY --chown=$MAMBA_USER:$MAMBA_USER /sandbox/sandbox /sandbox
COPY --chown=$MAMBA_USER:$MAMBA_USER /src /app
    
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "main.py"]