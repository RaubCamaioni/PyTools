FROM mambaorg/micromamba:2.0.2

# mamba user id 57439

USER root
RUN apt-get update && apt install libgl1-mesa-glx -y
USER $MAMBA_USER
COPY --chown=$MAMBA_USER:$MAMBA_USER env.yaml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes

USER root
COPY sandbox /sandbox
RUN mkdir /sandbox/tmp
RUN chown -R $MAMBA_USER:$MAMBA_USER /sandbox
# USER $MAMBA_USER

WORKDIR /sandbox