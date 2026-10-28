ARG PYTHON_VERSION=3.14@sha256:46a17be7cf526995fbf12177b40c248de30b40c1a509a4c7e5da954226f6885b

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
