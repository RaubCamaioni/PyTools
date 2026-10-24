"""tools/catalog.yaml carries the repo tools' metadata: one entry per tool file, valid against the category tree."""

from pathlib import Path

import pytest
import yaml

from app.metadata.categories import Categories
from app.metadata.description import Description
from app.metadata.tags import Tags

# the repo root locally; in the test container the tools folder is copied to /tools
REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"


@pytest.mark.skipif(not (TOOLS / "catalog.yaml").exists(), reason="no tools folder beside the server")
def test_manifest_matches_tools_and_tree():
    manifest = yaml.safe_load((TOOLS / "catalog.yaml").read_text(encoding="utf-8"))
    files = {p.stem: p.relative_to(TOOLS).as_posix() for p in TOOLS.rglob("*.py")}
    assert set(manifest) == set(files)
    for name, entry in manifest.items():
        assert {"file", "tags", "categories"} <= set(entry) <= {"file", "tags", "categories", "description"}, name
        assert entry["file"] == files[name], name
        tags = Tags().parse({"tags.present": ["1"], "tags": [str(t) for t in entry["tags"]]})
        assert tags == [str(t) for t in entry["tags"]], f"{name}: tags are not in normal form"
        assert Categories().parse({"categories.present": ["1"], "categories": entry["categories"]}), name
        if "description" in entry:
            Description().parse({"description.present": ["1"], "description": [entry["description"]]})


def test_tool_file_names_are_unique():
    stems = [p.stem for p in TOOLS.rglob("*.py")]
    assert len(stems) == len(set(stems))  # the manifest and the site match tools by name
