"""Tags used to be a JSON column on the tool row, filled from line 1 with the tool name appended; the first
start of the metadata version copies them into ToolTag once."""

import json

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

import app.metadata  # noqa: F401  (registers the metadata tables)
from app.metadata.tags import Tags
from app.models import tools as db


def old_database(tmp_path, rows):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE tool ADD COLUMN tags JSON"))
        for id, name, tags in rows:
            conn.execute(
                text("INSERT INTO tool (id, name, code, arguments, tags, usage, public, annonymous, user_id) "
                     "VALUES (:id, :name, '', '{}', :tags, 0, 1, 1, 1)"),
                {"id": id, "name": name, "tags": tags},
            )
    return engine


def test_copy_json_tags_runs_once(tmp_path):
    engine = old_database(tmp_path, [(1, "demo", '["box", "lid", "AA", "demo"]'), (2, "bare", None), (3, "odd", '["ok", "a/b"]')])
    assert db.copy_json_tags(engine) == 4  # box, lid, aa; ok (a/b is not a valid tag and is skipped)
    with Session(engine) as session:
        assert Tags().load(session, [1, 2, 3]) == {1: ["box", "lid", "aa"], 2: [], 3: ["ok"]}
    assert db.copy_json_tags(engine) == 0  # ToolTag is no longer empty: never again


def test_fresh_database_has_nothing_to_copy(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    SQLModel.metadata.create_all(engine)
    assert db.copy_json_tags(engine) == 0


def test_copy_never_repeats_even_after_every_tag_is_removed(tmp_path):
    engine = old_database(tmp_path, [(1, "demo", '["box"]')])
    assert db.copy_json_tags(engine) == 1
    with Session(engine) as session:
        Tags().save(session, 1, [])  # the owner clears the tags
        session.commit()
    assert db.copy_json_tags(engine) == 0  # a restart must not bring the old ones back


def test_legacy_tags_are_normalised_deduplicated_and_capped(tmp_path):
    # PyTools' old JSON tags were never checked: uppercase, spaces, duplicates, bad characters, more than ten
    legacy = ["PDF", "pdf", "two words", "bad!tag", *[f"t{i}" for i in range(12)]]
    engine = old_database(tmp_path, [(1, "conv", json.dumps(legacy)), (2, "broken", "not json"), (3, "obj", '{"a": 1}')])
    db.copy_json_tags(engine)
    with Session(engine) as session:
        loaded = Tags().load(session, [1, 2, 3])
    assert loaded[1][:2] == ["pdf", "two-words"] and len(loaded[1]) == 10 and "bad!tag" not in loaded[1]
    assert loaded[2] == [] and loaded[3] == []  # unreadable values are skipped, never a startup crash
