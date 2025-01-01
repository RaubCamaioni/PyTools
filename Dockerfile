FROM python:3.10-slim-bookworm AS isolate-builder

RUN apt-get update && apt install -y \
    libcap-dev \
    pkg-config \
    libsystemd-dev \ 
    asciidoc \
    build-essential \
    git

RUN /usr/local/bin/pip install asciidoc

# requires cgroupv2: unable to get working inside docker
# RUN cd /tmp && \
#     git clone https://github.com/ioi/isolate.git && \
#     cd isolate && \
#     make

# supports cgroupv1
RUN cd /tmp && \
    git clone --branch v1.10 --single-branch https://github.com/ioi/isolate.git && \
    cd isolate && \
    make

FROM python:3.10-slim-bookworm

RUN apt-get update && apt install -y \
    libgl1-mesa-glx \
    libxrender1 \
    libglib2.0-0 \
    make \
    && rm -rf /var/lib/apt/lists/*

COPY --from=isolate-builder /tmp/isolate /tmp/isolate
RUN cd /tmp/isolate && make install && rm -rf /tmp/isolate

RUN groupadd -g 1001 app && \
    useradd -ms /bin/bash -u 1001 -g 1001 app
    
RUN mkdir /app && chown app:app /app
RUN mkdir /sandbox && chown app:app /sandbox

USER app

RUN python3 -m venv /app/venv
COPY --chown=app:app sandbox/app_requirements.txt /tmp/
RUN /app/venv/bin/pip install -r /tmp/app_requirements.txt

RUN python3 -m venv /sandbox/venv
COPY --chown=app:app sandbox/sandbox_requirements.txt /tmp/
RUN /sandbox/venv/bin/pip install -r /tmp/sandbox_requirements.txt

COPY --chown=app:app /files /files
COPY --chown=app:app /sandbox/sandbox /sandbox
COPY --chown=app:app /src /app
    
WORKDIR /app
ENTRYPOINT ["/app/venv/bin/python", "main.py"]