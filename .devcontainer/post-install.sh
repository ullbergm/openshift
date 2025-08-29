#!/usr/bin/env bash
set -eux

# initialize pre-commit
git config --global --add safe.directory /workspaces
pre-commit install --overwrite
