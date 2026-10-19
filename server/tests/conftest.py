import os

# the mandatory secrets must exist before `app` is imported: _ENVIRONMENT raises otherwise
for key in ("SESSION_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"):
    os.environ.setdefault(key, "test")
os.environ.setdefault("DATABASE", ":memory:")
