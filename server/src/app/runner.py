def runner():
    import uvicorn
    from app.app import app

    uvicorn.run(app, host="0.0.0.0", port=8080)
