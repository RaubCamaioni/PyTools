import os

# the mandatory settings must exist before `app` is imported: _ENVIRONMENT raises otherwise
os.environ.setdefault("SESSION_KEY", "test")
os.environ.setdefault("DATABASE", ":memory:")
