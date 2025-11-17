import subprocess
from pathlib import Path
from threading import Lock
from asyncio import create_subprocess_exec as async_exec
import random
import shutil
from app import logger, ENVIRONMENT


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

    async def run(self, tool: Path, dir: Path):
        worker = random.randint(0, self.workers)
        logger.info(f"worker {worker} running {tool.name}")

        with self.worker_locks[worker]:
            p = await async_exec("isolate", "--init", "--cg", f"--box-id={worker}")
            await p.wait()

            # isolate manual: https://www.ucw.cz/moe/isolate.1.html
            cmd = [
                "isolate",
                "--share-net",  # internet
                "--dir=/etc/",  # resolve.conf
                "--cg",
                "--cg-mem=104857600",
                "--env",
                "HOME=/box",
                f"--box-id={worker}",
                "--dir=/tmp=",
                f"--dir={dir}:rw",
                f"--dir=/sandbox={ENVIRONMENT.SANDBOX}",
                f"--processes={self.processors}",
                "--wall-time=30",
                "--run",
                "--",
                "/sandbox/bin/python",
                "-B",
                "/sandbox/bin/sandbox",
                "--file",
                f"{dir}/{tool.name}",
                "--workdir",
                f"{dir}",
            ]

            print(" ".join(cmd))

            p = await async_exec(*cmd)
            await p.wait()

            p = await async_exec("isolate", "--cg", "--cleanup", f"--box-id={worker}")
            await p.wait()
