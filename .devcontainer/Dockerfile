ARG PYTHON_VERSION=3.14@sha256:e06cc1111ed84189e91866447f562b89faadbfbbb9937cd67e6bf4172cdb45df

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
