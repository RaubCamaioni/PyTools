# docker, compose, container, devops, converter

from pathlib import Path
import shlex
import yaml


def docker_run_to_compose(
    command: str = "docker run -d --name web -p 8080:80 -v ./site:/usr/share/nginx/html nginx:alpine",
) -> Path:
    """Turn a `docker run ...` command line into an equivalent docker-compose.yml
    service.
    """
    try:
        tokens = shlex.split(command.strip().replace("\\\n", " "))
    except ValueError as e:
        raise ValueError(f"Could not parse the command: {e}")
    if tokens[:2] == ["docker", "run"]:
        tokens = tokens[2:]
    elif tokens[:1] == ["docker"]:
        tokens = tokens[1:]

    service: dict = {}
    name = None
    i = 0

    def take(key, value):
        service.setdefault(key, []).append(value)

    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t in ("-d", "--detach", "-it", "-i", "-t", "--rm"):
            if t in ("-it", "-i"):
                service["stdin_open"] = True
            if t in ("-it", "-t"):
                service["tty"] = True
            i += 1
        elif t in ("--name",):
            name = nxt
            i += 2
        elif t in ("-p", "--publish"):
            take("ports", nxt)
            i += 2
        elif t in ("-v", "--volume"):
            take("volumes", nxt)
            i += 2
        elif t in ("-e", "--env"):
            take("environment", nxt)
            i += 2
        elif t == "--env-file":
            take("env_file", nxt)
            i += 2
        elif t in ("--network", "--net"):
            take("networks", nxt)
            i += 2
        elif t == "--restart":
            service["restart"] = nxt
            i += 2
        elif t in ("-w", "--workdir"):
            service["working_dir"] = nxt
            i += 2
        elif t in ("-u", "--user"):
            service["user"] = nxt
            i += 2
        elif t in ("-h", "--hostname"):
            service["hostname"] = nxt
            i += 2
        elif t == "--entrypoint":
            service["entrypoint"] = nxt
            i += 2
        elif t in ("-l", "--label"):
            take("labels", nxt)
            i += 2
        elif t == "--privileged":
            service["privileged"] = True
            i += 1
        elif t.startswith("--") and "=" in t:
            key, value = t[2:].split("=", 1)
            take(key.replace("-", "_"), value)
            i += 1
        elif t.startswith("-"):
            take("unsupported_flags", t if nxt is None or nxt.startswith("-") else f"{t} {nxt}")
            i += 1 if nxt is None or nxt.startswith("-") else 2
        else:
            service["image"] = t
            rest = tokens[i + 1 :]
            if rest:
                service["command"] = rest
            break

    service_name = name or (service.get("image", "app").split("/")[-1].split(":")[0])
    if name:
        service["container_name"] = name
    compose = {"services": {service_name: service}}
    if "networks" in service:
        compose["networks"] = {n: {} for n in service["networks"]}
    out = Path("docker-compose.yml")
    out.write_text(yaml.safe_dump(compose, sort_keys=False, default_flow_style=False), encoding="utf-8")
    return out
