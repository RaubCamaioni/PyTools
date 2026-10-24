"""A tool is a model when its entrypoint declares a CadQuery return (and its upload build passed); rows stored
before the kind existed read as scripts."""

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.models import tools as db
from app.models.kind import declares_model


@pytest.mark.parametrize("ann", ["cq.Workplane", "Workplane", "cadquery.Shape", "Solid", "cq.Compound", "Assembly",
                                 "cadquery.Workplane", "cq.Shape"])
def test_declares_model(ann):
    assert declares_model(ann)


@pytest.mark.parametrize("ann", [None, "", "str", "Path", "cq.Vector", "list[cq.Workplane]", "Workplanes",
                                 "Optional[cq.Workplane]", "cq.Workplane | None", "foo.Workplane"])
def test_not_a_model(ann):
    assert not declares_model(ann)


def test_a_row_from_before_the_kind_reads_as_a_script(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:  # the tool table as v0.5.0 created it: no kind, preview_svg or meta
        conn.execute(text("CREATE TABLE user (id INTEGER PRIMARY KEY, alias VARCHAR NOT NULL)"))
        conn.execute(text(
            "CREATE TABLE tool (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, code VARCHAR NOT NULL, arguments JSON, "
            "usage INTEGER NOT NULL, public BOOLEAN NOT NULL, annonymous BOOLEAN NOT NULL, user_id INTEGER)"))
        conn.execute(text("INSERT INTO tool VALUES (1, 'old', 'def old() -> int:\n    return 1\n', '{}', 0, 1, 1, 1)"))
    SQLModel.metadata.create_all(engine)
    db.migrate(engine)
    with Session(engine) as session:
        tool = session.get(db.Tool, 1)
        assert tool.kind == "script" and tool.preview_svg == "" and tool.meta in ({}, None)
