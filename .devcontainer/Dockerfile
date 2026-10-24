ARG PYTHON_VERSION=3.15@sha256:67ee282bdbe5ece1e38ea94fa68f1420e969e6176e6c826b9acc931055011bfb

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
