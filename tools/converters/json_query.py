# json, query, jmespath, filter, data

from pathlib import Path
import json
import jmespath


def json_query(json_file: Path, query: str = "[*].name") -> dict:
    """Pull values out of a JSON file with a JMESPath expression: `users[?age >
    `30`].name`, `items[0].price`, `length(@)`, `sort_by(@, &date)[-1]` and so on.
    """
    data = json.loads(json_file.read_text(encoding="utf-8-sig"))
    try:
        result = jmespath.search(query, data)
    except jmespath.exceptions.JMESPathError as e:
        return {"error": f"Invalid query: {e}"}
    out = json_file.with_name(f"{json_file.stem}_query.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    preview = json.dumps(result, ensure_ascii=False)
    return {
        "file": out,
        "result_type": type(result).__name__,
        "preview": preview[:600] + ("..." if len(preview) > 600 else ""),
    }
