from fastapi import FastAPI, UploadFile, File, HTTPException, Request, APIRouter, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from tempfile import NamedTemporaryFile, TemporaryDirectory
from starlette.background import BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Generator, Tuple, Any, Callable, Dict, Annotated, Union
from dataclasses import dataclass, fields
from types import ModuleType
from pathlib import Path
import cadquery as cq
from cadquery.occ_impl import jupyter_tools
import importlib.util
import traceback
import zipfile
from IPython.display import Javascript
import inspect
import json
import time
import os
import vtk

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
    func: Callable
    form: str
    types: Dict[str, type]


def form_group(name: str, type: str):
    form = "\n".join(
        [
            '<div class="form-group">',
            f'	<label for="{name}">{name}:</label>',
            f'	<input type="{type}" id="{name}" name="{name}" step=".01" required>',
            "</div>",
        ]
    )
    return form


def load_converter_files(converters_folder: Path) -> dict[str, ConverterModule]:
    converter_modules: dict[str, ConverterModule] = {}

    for converter_file in converters_folder.glob("*.py"):
        module_name = converter_file.stem
        spec = importlib.util.spec_from_file_location(module_name, converter_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # json_name = converter_file.with_suffix(".json")
        # with open(json_name, "r") as f:
        #     meta_data = json.load(f)

        with open(converter_file, "r") as f:
            code = f.read().strip()

        func = get_converter_function(module)

        signature = inspect.signature(func)
        name = func.__name__
        comment = inspect.getdoc(func)

        forms = []
        types = {}
        for param in signature.parameters.values():
            param_name = param.name
            param_type = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else "No type hint"
            )
            types[param_name] = param_type
            form_type = {
                "str": "text",
                "int": "number",
                "float": "number",
            }
            forms.append(
                form_group(param_name, form_type.get(param_type.__name__, "text"))
            )

        converter_module = ConverterModule(
            name=name,
            description=comment,
            code=code,
            endpoint=module_name,
            module=module,
            func=func,
            form="\n".join(forms),
            types=types,
        )

        print(f"loaded converter: {module_name}")
        converter_modules[module_name] = converter_module

    return converter_modules


def get_converter_function(module: ModuleType) -> str:
    functions = (
        name for name, obj in inspect.getmembers(module) if inspect.isfunction(obj)
    )
    for name in functions:
        if name.startswith("convert"):
            return getattr(module, name, None)


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
            "form_groups": converter.form,
            "time": time.time(),
            "base_url": BASE_URL,
        },
    )


def TempFileGenerator(files: List[UploadFile]) -> Generator[Path, None, None]:
    with TemporaryDirectory() as tmpdir:
        for file in files:
            temp_file_name = Path(tmpdir) / file.filename
            with open(temp_file_name, "wb") as f:
                f.write(file.file.read())
            yield temp_file_name


@router.post("/convert/{converter_name}", response_class=HTMLResponse)
async def convert_file(
    request: Request,
    converter_name: str,
) -> str:
    if converter_name not in converter_modules:
        raise HTTPException(status_code=404, detail="Converter module not found")
    module = converter_modules[converter_name]

    converter_func = module.func
    if not callable(converter_func):
        raise HTTPException(status_code=500, detail="Invalid converter function")

    form_data = await request.form()
    kwargs = {}
    for key, value in form_data.items():
        kwargs[key] = module.types[key](value)

    result = converter_func(**kwargs)

    if isinstance(result, cq.Shape):
        # return_string = vtk.generate_vtk_inner_html(result)
        return_string = vtk.display(result)
    else:
        return_string = f"{type(result).__name__}: {result}"

    structure = f'<div id="result" class="result-container"><div class="return">{return_string}</div></div>'

    return HTMLResponse(structure)


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
