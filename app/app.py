from fastapi import FastAPI, UploadFile, File, HTTPException, Request, APIRouter
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from tempfile import NamedTemporaryFile, TemporaryDirectory
from starlette.background import BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Generator, Tuple
from dataclasses import dataclass
from types import ModuleType
from pathlib import Path
import importlib.util
import traceback
import zipfile
import inspect
import json
import time
import os

BASE_URL = os.getenv("BASE_URL", "")
print(f"BASE_URL: {BASE_URL}")
router = APIRouter(prefix=BASE_URL)
app = FastAPI()


@dataclass
class ConverterModule:
    name: str
    description: str
    code: str
    endpoint: str
    module: ModuleType


def load_converter_files(converters_folder: Path) -> dict[str, ConverterModule]:
    converter_modules: dict[str, ConverterModule] = {}

    for converter_file in converters_folder.glob("*.py"):

        module_name = converter_file.stem
        spec = importlib.util.spec_from_file_location(module_name, converter_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        json_name = converter_file.with_suffix(".json")
        with open(json_name, "r") as f:
            meta_data = json.load(f)

        with open(converter_file, "r") as f:
            code = f.read().strip()

        converter_module = ConverterModule(
            name=meta_data["name"],
            description=meta_data["description"],
            code=code,
            endpoint=module_name,
            module=module,
        )

        print(f"loaded converter: {module_name}")
        converter_modules[module_name] = converter_module

    return converter_modules


converter_modules = load_converter_files(Path(__file__).parent / "converters")
templates = Jinja2Templates(directory="templates")
app.mount(f"{BASE_URL}/static", StaticFiles(directory="static"), name="static")
app.mount(f"{BASE_URL}/scripts", StaticFiles(directory="scripts"), name="scripts")


@router.get(f"/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "base_url": BASE_URL,
        },
    )


@router.get("/converters", response_class=JSONResponse)
async def get_converters():
    converters = [
        (module.name, module.endpoint) for module in converter_modules.values()
    ]
    return {"converters": converters}


@router.get("/convert/{converter_name}", response_class=HTMLResponse)
async def convert_page(request: Request, converter_name: str):

    if converter_name not in converter_modules:
        raise HTTPException(status_code=404, detail="Converter not found")

    converter = converter_modules[converter_name]
    return templates.TemplateResponse(
        "converter.html",
        {
            "request": request,
            "endpoint": converter.endpoint,
            "converter_name": converter.name,
            "description": converter.description,
            "code": converter.code,
            "time": time.time(),
            "base_url": BASE_URL,
        },
    )


def get_converter_function(module: ModuleType) -> List[str]:
    functions = (
        name for name, obj in inspect.getmembers(module) if inspect.isfunction(obj)
    )
    for name in functions:
        if name.startswith("convert"):
            return name


def TempFileGenerator(files: List[UploadFile]) -> Generator[Path, None, None]:
    with TemporaryDirectory() as tmpdir:
        for file in files:
            temp_file_name = Path(tmpdir) / file.filename
            with open(temp_file_name, "wb") as f:
                f.write(file.file.read())
            yield temp_file_name


@router.post("/convert/{converter_name}")
async def convert_file(
    converter_name: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):

    if converter_name not in converter_modules:
        raise HTTPException(status_code=404, detail="Converter module not found")
    module = converter_modules[converter_name]

    converter_func_name = get_converter_function(module.module)
    if converter_func_name is None:
        raise HTTPException(status_code=404, detail=f"Converter function not found")

    converter_func = getattr(module.module, converter_func_name, None)
    if not callable(converter_func):
        raise HTTPException(status_code=500, detail="Invalid converter function")

    with TemporaryDirectory() as tmpdir:

        for temp_file in TempFileGenerator(files):
            try:
                converter_func(
                    str(temp_file), str(Path(tmpdir) / f"converted_{temp_file.name}")
                )
            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=str(e))

        with NamedTemporaryFile(delete=False, suffix="zip") as tempzip:
            background_tasks.add_task(lambda path: os.unlink(path), tempzip.name)
            with zipfile.ZipFile(tempzip.name, "w", zipfile.ZIP_DEFLATED) as zip:
                for temp_path in Path(tmpdir).rglob("*"):
                    if temp_path.is_file():
                        zip.write(temp_path, arcname=temp_path.relative_to(tmpdir))

    return FileResponse(
        tempzip.name,
        media_type="application/x-zip-compressed",
        filename="converted_files.zip",
    )


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
