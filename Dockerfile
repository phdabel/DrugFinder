# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-alpine3.17

ARG WORK_DIRECTORY=/app

ENV WORK_DIRECTORY=${WORK_DIRECTORY}

# Install git
RUN apk update && apk add git

# Install dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    cargo \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry \
    && apk del .build-deps

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
# COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR $WORK_DIRECTORY
COPY . $WORK_DIRECTORY

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser ${WORK_DIRECTORY}
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "setup.py"]
