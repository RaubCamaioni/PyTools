from pathlib import Path, PosixPath
from typing import Any
import json
import io


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (Path, PosixPath)):
            return {"__path__": str(obj)}
        return super().default(obj)


class JsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, object_hook=self.object_hook)

    def object_hook(self, obj):
        if "__path__" in obj:
            return Path(obj["__path__"])
        return obj


def json_dumps(objects: Any) -> str:
    return json.dumps(objects, cls=JsonEncoder)


def json_loads(serial: str) -> Any:
    return json.loads(serial, cls=JsonDecoder)


def json_dump(objects: Any, file: io.FileIO) -> str:
    return json.dump(objects, file, cls=JsonEncoder)


def json_load(file: io.FileIO) -> Any:
    return json.load(file, cls=JsonDecoder)


if __name__ == "__main__":
    items = {"sammy": [1, 2, Path("/some/directory/example.txt")]}
    print(f"original: {items}")
    encoded = json_dumps(items)
    print(f"encoded: {encoded}")
    decoded = json_loads(encoded)
    print(f"decoded: {decoded}")
