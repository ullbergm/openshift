ARG PYTHON_VERSION=3.14@sha256:8edbf9e42c7fb168b9c523718ed907117e6d2e60f5889c0c499bbda3a787da53

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# update PATH for local pip installs
ENV PATH="$PATH:~/.local/bin"

# upgrade pip
RUN python -m pip install --upgrade pip

# install devcontainer requirements
RUN pip install --no-cache-dir pre-commit

CMD sleep infinity

ENTRYPOINT []
