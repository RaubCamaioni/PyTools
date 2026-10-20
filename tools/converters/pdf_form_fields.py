# pdf, form, fields, fill, json, flatten

from pathlib import Path
from typing import Literal
import json
import pymupdf


def pdf_form_fields(
    pdf: Path,
    action: Literal["list_fields", "fill_from_json", "flatten_fields"] = "list_fields",
    values_json: str = "{}",
) -> dict:
    """List a PDF form's fields with their current values (as JSON you can edit), fill
    the form from a JSON object of field name to value, or flatten it so the values
    become fixed text.
    """
    with pymupdf.open(pdf) as doc:
        if not doc.is_form_pdf:
            return {"error": "This PDF has no form fields"}
        if action == "list_fields":
            fields = {}
            for page in doc:
                for w in page.widgets():
                    fields[w.field_name] = {
                        "type": w.field_type_string,
                        "value": w.field_value,
                        "page": page.number + 1,
                    }
                    if w.choice_values:
                        fields[w.field_name]["choices"] = w.choice_values
            out = pdf.with_name(f"{pdf.stem}_fields.json")
            out.write_text(
                json.dumps({k: v["value"] for k, v in fields.items()}, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return {"file": out, "fields": fields}
        if action == "fill_from_json":
            try:
                values = json.loads(values_json or "{}")
            except json.JSONDecodeError as e:
                return {"error": f"values_json is not valid JSON: {e}"}
            filled = 0
            for page in doc:
                for w in page.widgets():
                    if w.field_name in values:
                        value = values[w.field_name]
                        if w.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                            w.field_value = bool(value) and value not in ("Off", "false", "0")
                        else:
                            w.field_value = str(value)
                        w.update()
                        filled += 1
            out = pdf.with_name(f"{pdf.stem}_filled.pdf")
            doc.save(out, garbage=3, deflate=True)
            return {"file": out, "fields_filled": filled}
        for page in doc:
            for w in list(page.widgets()):
                page.delete_widget(w)
        doc.bake()
        out = pdf.with_name(f"{pdf.stem}_flat.pdf")
        doc.save(out, garbage=3, deflate=True)
        return {"file": out}
