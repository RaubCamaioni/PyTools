# json, schema, validate, data

from pathlib import Path
import json
import jsonschema


def json_schema_validator(json_file: Path, schema_file: Path, max_errors: int = 50) -> dict:
    """Validate a JSON document against a JSON Schema (draft 4 to 2020-12) and list
    every violation with its path and message.
    """
    try:
        data = json.loads(json_file.read_text(encoding="utf-8-sig"))
        schema = json.loads(schema_file.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {"error": f"Not valid JSON: {e}"}
    try:
        validator_class = jsonschema.validators.validator_for(schema)
        validator_class.check_schema(schema)
    except jsonschema.SchemaError as e:
        return {"error": f"The schema itself is invalid: {e.message}"}
    validator = validator_class(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append({"path": path, "message": error.message[:300]})
        if len(errors) >= max(1, max_errors):
            break
    return {"valid": not errors, "errors": errors, "error_count": len(errors)}
