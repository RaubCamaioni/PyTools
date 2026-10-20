import os
import tempfile

# the mandatory settings must exist before `app` is imported: _ENVIRONMENT raises otherwise
os.environ.setdefault("SESSION_KEY", "test")
# a file-backed sqlite: `:memory:` would give the test client's thread an empty database
_DB = tempfile.NamedTemporaryFile(prefix="pywebtools-test-", suffix=".db", delete=False)
os.environ.setdefault("DATABASE", _DB.name)

from app.models.tools import create_db_and_tables  # noqa: E402

create_db_and_tables()
