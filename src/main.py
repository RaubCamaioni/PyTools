import os
import sys

if __name__ == "__main__":
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if SECRET_KEY is None:
        print("Middleware Secret Required.")
        sys.exit()

    import uvicorn
    from app import app

    uvicorn.run(app, host="0.0.0.0", port=8080)
