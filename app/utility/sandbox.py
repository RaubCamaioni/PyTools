import subprocess
from pathlib import Path


def docker_run(image: str, tool: Path, workdir: Path):
    command = [
        "docker",
        "run",
        "--network=none",
        "-m=512m",
        "--cpus=1.5",
        "--rm",
        "-v",
        f"{tool}:/sandbox/{tool.name}:ro",
        "-v",
        f"{workdir}:{'/sandbox' / workdir}",
        f"{image}",
        "python3",
        "runner.py",
        "--file",
        f"/sandbox/{tool.name}",
        "--workdir",
        f"{'sandbox' / workdir}",
    ]
    subprocess.call(command)
