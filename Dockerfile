FROM python:3.10-slim-bookworm AS isolate-builder

RUN apt-get update && apt install -y \
    libcap-dev \
    pkg-config \
    libsystemd-dev \ 
    asciidoc \
    build-essential \
    git

RUN /usr/local/bin/pip install asciidoc

RUN cd /tmp && \
    git clone https://github.com/ioi/isolate.git && \
    cd isolate && \
    make

# RUN cd /tmp && \
#     git clone https://github.com/ioi/isolate.git && \
#     cd isolate && \
#     make && \
#     make install && \
#     cd / && rm -rf /tmp/isolate && \
#     apt-get clean && rm -rf /var/lib/apt/lists/*

FROM python:3.10-slim-bookworm

RUN apt-get update && apt install -y \
    libgl1-mesa-glx \
    make \
    && rm -rf /var/lib/apt/lists/*

COPY --from=isolate-builder /tmp/isolate /tmp/isolate
RUN cd /tmp/isolate && make install && rm -rf /tmp/isolate

RUN useradd -ms /bin/bash app
RUN mkdir /app && chown app:app /app
RUN mkdir /sandbox && chown app:app /sandbox

USER app

RUN python3 -m venv /app/venv
COPY --chown=app:app sandbox/app_requirements.txt /tmp/
RUN /app/venv/bin/pip install -r /tmp/app_requirements.txt

RUN python3 -m venv /sandbox/venv
COPY --chown=app:app sandbox/sandbox_requirements.txt /tmp/
RUN /sandbox/venv/bin/pip install -r /tmp/sandbox_requirements.txt

COPY --chown=app:app /sandbox/sandbox /sandbox
COPY --chown=app:app /src /app
    
WORKDIR /app
ENTRYPOINT ["/app/venv/bin/python", "main.py"]