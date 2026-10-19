"""Run every sample tool in tools/ through the real sandbox.

Needs the inner podman and the sandbox image, so it runs inside the app container
(see test_integration_sandbox.py). Each case supplies the inputs a user would and
checks the result a user would expect.
"""

import base64
import hashlib
import io
import os
import shutil
import time
import wave
from pathlib import Path

import pytest

from app.utility import serializer
from app.utility.podman_runner import Outcome, PodmanRunner
from app.utility.sandbox_config import SandboxConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("SANDBOX_INTEGRATION") != "1", reason="needs the inner podman and the sandbox image"),
]

TOOLS = Path(__file__).resolve().parents[2] / "tools"

# a valid 1x1 PNG
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# a minimal single-page PDF that prints "Hello PDF"
PDF_HELLO = b"""%PDF-1.1
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 18 Tf 20 40 Td (Hello PDF) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
trailer << /Root 1 0 R >>
"""


def wav_bytes(seconds: float = 0.5, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * int(rate * seconds))
    return buf.getvalue()


@pytest.fixture(scope="module")
def config():
    return SandboxConfig.from_environment(os.environ)


@pytest.fixture
async def runner(config):
    r = PodmanRunner(config)
    await r.start()
    assert r.available, r.unavailable_reason
    yield r
    await r.stop()


@pytest.fixture
def run_dir(config):
    d = config.run_dir / f"sample-{time.monotonic_ns()}"
    d.mkdir(parents=True)
    d.chmod(0o777)
    yield d
    shutil.rmtree(d, ignore_errors=True)


async def run_sample(runner, run_dir, name, args=None, files=None):
    """Copy tools/<name>.py and the given input files into run_dir and run it like the route does."""
    tool = run_dir / f"{name}.py"
    shutil.copy(TOOLS / f"{name}.py", tool)
    for filename, content in (files or {}).items():
        (run_dir / filename).write_bytes(content)
    args = {k: (run_dir / v if isinstance(v, FileArg) else v) for k, v in (args or {}).items()}
    with open(run_dir / "args.json", "w") as f:
        serializer.dump(args, f)
    return await runner.run(tool, run_dir)


class FileArg(str):
    """Marks an argument as a path to one of the uploaded files."""


async def test_lower_case_text(runner, run_dir):
    r = await run_sample(runner, run_dir, "lower_case_text", {"input": FileArg("in.txt")}, {"in.txt": b"HeLLo World"})
    assert r.outcome is Outcome.OK, r
    assert Path(r.results).read_text() == "hello world"


async def test_byte_converter_both_directions(runner, run_dir):
    r = await run_sample(runner, run_dir, "byte_converter", {"input": "hi", "output": "hexadecimal"})
    assert r.outcome is Outcome.OK and r.results == "0x68 0x69"


async def test_sha256_of_upload(runner, run_dir):
    r = await run_sample(runner, run_dir, "sha256", {"file": FileArg("data.bin"), "hash": "sha256"}, {"data.bin": b"abc"})
    assert r.outcome is Outcome.OK and r.results == hashlib.sha256(b"abc").hexdigest()


async def test_image_to_grayscale(runner, run_dir):
    r = await run_sample(runner, run_dir, "image_to_grayscale", {"image_file": FileArg("pixel.png")}, {"pixel.png": PNG_1X1})
    assert r.outcome is Outcome.OK, r
    assert Path(r.results).name == "pixel_gray.png" and Path(r.results).stat().st_size > 0


async def test_pdf_to_text(runner, run_dir):
    r = await run_sample(runner, run_dir, "pdf_to_text", {"pdf_file": FileArg("doc.pdf")}, {"doc.pdf": PDF_HELLO})
    assert r.outcome is Outcome.OK, r
    assert "Hello PDF" in Path(r.results).read_text()


async def test_audio_to_audio_wav_to_mp3(runner, run_dir):
    r = await run_sample(runner, run_dir, "audio_to_audio", {"input": FileArg("tone.wav"), "output": "mp3"}, {"tone.wav": wav_bytes()})
    assert r.outcome is Outcome.OK, r
    assert Path(r.results).suffix == ".mp3" and Path(r.results).stat().st_size > 0


async def test_video_to_audio_extracts_audio_stream(runner, run_dir):
    r = await run_sample(runner, run_dir, "video_to_audio", {"video_file": FileArg("clip.wav")}, {"clip.wav": wav_bytes()})
    assert r.outcome is Outcome.OK, r
    assert Path(r.results).suffix == ".mp3"


async def test_multi_modal_return_serializes_a_set(runner, run_dir):
    r = await run_sample(runner, run_dir, "multi_modal_return")
    assert r.outcome is Outcome.OK and sorted(r.results) == ["set", "simple"]


async def test_profanity_check_returns_text(runner, run_dir):
    r = await run_sample(runner, run_dir, "profanity_check")
    assert r.outcome is Outcome.OK and r.results == "bollocks"


async def test_error_tool_reports_runtime_error(runner, run_dir):
    r = await run_sample(runner, run_dir, "error_tool_test")
    # the sandbox runner catches the exception and returns it as text
    assert r.outcome is Outcome.OK and "Runtime Error" in str(r.results) and "AssertionError" in str(r.results)


async def test_async_tool_hits_the_time_limit(run_dir):
    # pin a 5 s limit so the test does not depend on the production SANDBOX_TIMEOUT_SECONDS
    short = PodmanRunner(SandboxConfig.from_environment({**os.environ, "SANDBOX_TIMEOUT_SECONDS": "5"}))
    await short.start()
    assert short.available, short.unavailable_reason
    try:
        r = await run_sample(short, run_dir, "async_tool_test")  # sleeps 15 s
    finally:
        await short.stop()
    assert r.outcome is Outcome.TIMEOUT and r.message == "Tool exceeded the 5 second limit"


CADQUERY_SECONDS = 30  # CadQuery import + geometry needs more than the default 10 s at 0.5 CPU


@pytest.fixture
async def cadquery_runner(config):
    r = PodmanRunner(SandboxConfig.from_environment({**os.environ, "SANDBOX_TIMEOUT_SECONDS": str(CADQUERY_SECONDS)}))
    await r.start()
    assert r.available, r.unavailable_reason
    yield r
    await r.stop()


@pytest.mark.parametrize("name", ["container_with_lid", "container_with_lid_circle", "container_with_lid_sweep", "electronic_stand"])
async def test_cadquery_tools_produce_stl(cadquery_runner, run_dir, name):
    started = time.monotonic()
    r = await run_sample(cadquery_runner, run_dir, name)
    elapsed = time.monotonic() - started
    assert r.outcome is Outcome.OK, f"{name}: {r} after {elapsed:.1f}s"
    assert Path(r.results).suffix == ".stl" and Path(r.results).stat().st_size > 0
    print(f"{name}: {elapsed:.1f}s")  # visible with -s; production SANDBOX_TIMEOUT_SECONDS must cover this
