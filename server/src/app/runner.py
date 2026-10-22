def runner():
    import uvicorn
    from app.app import app

    from app import ENVIRONMENT

    # root_path makes request.scope["root_path"] the mount prefix; routing still sees the paths below it
    uvicorn.run(app, host="0.0.0.0", port=8080, root_path=ENVIRONMENT.ROOT_PATH)
