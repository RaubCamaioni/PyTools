"""pytools-admin: maintenance commands run inside the app container.

    pytools-admin apply-manifest <manifest.yaml> [--apply] [--owner <user id>]

sets the tags and categories of the owner's stored tools from a manifest (tools/catalog.yaml in the repo),
matching tools by name. Without --apply it only prints what would change. With --apply it first writes the
previous values to <data>/backups/metadata-<UTC time>.json. An invalid entry, or two of the owner's tools with
the same name, stops it before anything is saved.
"""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

import yaml
from sqlmodel import Session, select

from app import metadata
from app.metadata.categories import effective

OWNER = 49600918


def _form(entry: dict) -> dict[str, list[str]]:
    """An entry as the dialog's form fields; its `file` (the path under tools/) is not metadata."""
    form = {
        "tags.present": ["1"],
        "tags": [str(t) for t in entry.get("tags", [])],
        "categories.present": ["1"],
        "categories": [str(c) for c in entry.get("categories", [])],
    }
    if "description" in entry:  # optional: without it a description written on the site is kept
        form.update({"description.present": ["1"], "description": [str(entry["description"])]})
    return form


def apply_manifest(
    session: Session, manifest: dict, owner: int, apply: bool, backup_dir: Path
) -> tuple[int, list[str]]:
    """Returns (exit code, report lines)."""
    from app.models.tools import Tool

    lines: list[str] = []
    parsed = {}
    for name, entry in manifest.items():
        try:
            parsed[name] = metadata.parse_all(_form(entry or {}))
        except metadata.MetadataError as e:
            lines.append(f"{name}: {e}")
    if len(parsed) != len(manifest):
        return 1, lines

    ids: dict[str, list[int]] = {}
    for tool_id, name in session.exec(select(Tool.id, Tool.name).where(Tool.user_id == owner)).all():
        ids.setdefault(name, []).append(tool_id)
    duplicates = sorted(name for name in manifest if len(ids.get(name, [])) > 1)
    if duplicates:
        return 1, [f"{name}: more than one stored tool owned by {owner} has this name" for name in duplicates]

    found = {name: ids[name][0] for name in manifest if name in ids}
    current = metadata.load_all(session, list(found.values()))
    changes = {}
    for name, tool_id in sorted(found.items()):
        want = {**parsed[name], "categories": effective(parsed[name]["categories"])}
        have = {key: current[tool_id][key] for key in want}  # only what the manifest sets
        if have != want:
            changes[name] = tool_id
            lines.append(
                f"{name}: tags {have['tags']} -> {want['tags']}; "
                f"categories {have['categories']} -> {want['categories']}"
            )
    lines += [f"not stored: {name}" for name in sorted(set(manifest) - set(found))]
    lines.append(f"{len(changes)} of {len(found)} stored tools change" + ("" if apply else " (dry run)"))

    if apply and changes:
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        previous = {str(tool_id): {"name": name, **current[tool_id]} for name, tool_id in changes.items()}
        backup = backup_dir / f"metadata-{stamp}.json"
        backup.write_text(json.dumps(previous, indent=1), encoding="utf-8")
        lines.append(f"backup: {backup}")
        for name, tool_id in changes.items():
            metadata.save_all(session, tool_id, parsed[name])
        session.commit()
    return 0, lines


def main(argv: list[str] = None) -> int:
    from app import ENVIRONMENT
    from app.models.tools import create_db_and_tables, engine

    parser = argparse.ArgumentParser(prog="pytools-admin")
    commands = parser.add_subparsers(dest="command", required=True)
    apply = commands.add_parser("apply-manifest", help="set the owner's tools' tags, categories and descriptions from a manifest")
    apply.add_argument("manifest", type=Path)
    apply.add_argument("--apply", action="store_true", help="save the changes (default: only print them)")
    apply.add_argument("--owner", type=int, default=OWNER)
    args = parser.parse_args(argv)

    create_db_and_tables()  # the metadata tables exist even if the app has not started on this version yet
    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    with Session(engine) as session:
        code, lines = apply_manifest(
            session, manifest, args.owner, args.apply, Path(ENVIRONMENT.DATABASE).parent / "backups"
        )
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
