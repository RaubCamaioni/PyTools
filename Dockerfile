FROM docker:27.4.0-rc.1-dind-alpine3.20

RUN apk --no-cache add python3 py3-pip

RUN pip3 install --break-system-packages --no-cache-dir fastapi[standard] itsdangerous requests jwt

COPY /app /app/app
WORKDIR /app

CMD ["fastapi", "dev", "app/app.py", "--host", "0.0.0.0", "--port", "8080"]