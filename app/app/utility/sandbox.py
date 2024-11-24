import subprocess
from pathlib import Path
from threading import Lock
import random
import os

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


class IsolationWorkers:
    def __init__(
        self,
        workers: int = 5,
        memory: int = 512000,
        processors: int = 50,
    ):
        self.workers = workers
        self.memory = memory
        self.processors = processors
        self.worker_locks = [Lock() for i in range(self.processors)]

    def run(self, tool: Path, dir: Path):
        worker = random.randint(0, self.workers)

        worker = 0
        with self.worker_locks[worker]:
            subprocess.call(["isolate", "--init", f"--box-id={worker}"])
            os.link(tool, f"/var/local/lib/isolate/0/box/{tool.name}")
            subprocess.call(
                [
                    "isolate",
                    "--env",
                    "HOME=/box",
                    f"--box-id={worker}",
                    f"--dir=/tmp=",
                    f"--dir={dir}:rw",
                    "--dir=/sandbox",
                    f"--processes={self.processors}",
                    "--wall-time=30",
                    "--run",
                    "--",
                    "/sandbox/venv/bin/python3.12",
                    "/sandbox/runner.py",
                    "--file",
                    f"/box/{tool.name}",
                    "--workdir",
                    f"{dir}",
                ]
            )
            subprocess.call(["isolate", "--cleanup", f"--box-id={worker}"])


def isolate_run(tool: Path, workdir: Path):
    pass
