ARG PYTHON_VERSION=3.14@sha256:61346539f7b26521a230e72c11da5ebd872924745074b19736e7d65ba748c366

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
