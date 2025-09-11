#!/usr/bin/env bash
set -euo pipefail

# Scaffold a new media chart by copying charts/media/sonarr and customizing.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
SRC_CHART_DIR="$ROOT_DIR/charts/media/sonarr"
ROLES_DIR="$ROOT_DIR/roles/media"

if [[ ! -d "$SRC_CHART_DIR" ]]; then
  echo "Source chart not found: $SRC_CHART_DIR" >&2
  exit 1
fi

echo "This wizard will scaffold a new media chart based on Sonarr."

read -rp "New chart machine name (lowercase, no spaces, e.g. 'readarr'): " CHART_NAME
if [[ -z "${CHART_NAME}" ]]; then
  echo "Chart name is required." >&2
  exit 1
fi

if [[ "$CHART_NAME" =~ [A-Z\ ] ]]; then
  echo "Chart name must be lowercase and contain no spaces." >&2
  exit 1
fi

TARGET_CHART_DIR="$ROOT_DIR/charts/media/$CHART_NAME"
if [[ -e "$TARGET_CHART_DIR" ]]; then
  echo "Target chart already exists: $TARGET_CHART_DIR" >&2
  exit 1
fi

DEFAULT_DISPLAY_NAME="$(echo "$CHART_NAME" | sed -E 's/(^|[-_])(\w)/\U\2/g')"
read -rp "Display name (Application.name) [${DEFAULT_DISPLAY_NAME}]: " DISPLAY_NAME
DISPLAY_NAME=${DISPLAY_NAME:-$DEFAULT_DISPLAY_NAME}

read -rp "Description: " DESCRIPTION || true

read -rp "App group (Application.group) [Media]: " APP_GROUP
APP_GROUP=${APP_GROUP:-Media}

read -rp "Console icon (Application.icon, e.g. 'simple-icons:readthedocs'): " ICON || true
read -rp "Icon color (Application.iconColor, optional): " ICON_COLOR || true

read -rp "Console image URL (Application.image, optional): " APP_IMAGE_URL || true

read -rp "Service port (Application.port) [8989]: " PORT
PORT=${PORT:-8989}

read -rp "Container image repository (pods.main.image.repository), e.g. ghcr.io/home-operations/readarr: " CONTAINER_REPO
if [[ -z "${CONTAINER_REPO}" ]]; then
  echo "Container image repository is required." >&2
  exit 1
fi

read -rp "Container image tag (pods.main.image.tag), e.g. 1.0.0: " CONTAINER_TAG
if [[ -z "${CONTAINER_TAG}" ]]; then
  echo "Container image tag is required." >&2
  exit 1
fi

echo "Creating chart at $TARGET_CHART_DIR ..."
cp -R "$SRC_CHART_DIR" "$TARGET_CHART_DIR"

# Update Chart.yaml
CHART_FILE="$TARGET_CHART_DIR/Chart.yaml"
sed -i \
  -e "s/^name: .*/name: ${CHART_NAME}/" \
  -e "s/^description: .*/description: A Helm chart for ${DISPLAY_NAME}/" \
  "$CHART_FILE"

# Rebuild values.yaml: keep cluster: block from source, then write new application and pods blocks.
SRC_VALUES="$SRC_CHART_DIR/values.yaml"
TARGET_VALUES="$TARGET_CHART_DIR/values.yaml"

{
  # Extract cluster block from source up to (but not including) 'application:'
  awk 'BEGIN{print_mode=1} /^application:[[:space:]]*$/ {print_mode=0} print_mode==1 {print $0}' "$SRC_VALUES"
  echo "application:"
  echo "  name: ${DISPLAY_NAME}"
  echo "  group: ${APP_GROUP}"
  echo "  icon: ${ICON}"
  echo "  iconColor: \"${ICON_COLOR}\""
  echo "  image: \"${APP_IMAGE_URL}\""
  echo "  description: \"${DESCRIPTION//"/\\"}\""
  echo "  port: ${PORT}"
  echo "  location: 0"
  echo ""
  echo "pods:"
  echo "  main:"
  echo "    image:"
  echo "      repository: ${CONTAINER_REPO}"
  echo "      # renovate: datasource=docker depName=${CONTAINER_REPO} versioning=semver"
  echo "      tag: ${CONTAINER_TAG}"
  echo "      pullPolicy: IfNotPresent"
} > "$TARGET_VALUES.tmp"

mv "$TARGET_VALUES.tmp" "$TARGET_VALUES"

# Create role template for the new app under roles/media/templates
ROLE_TEMPLATE_SRC="$ROLES_DIR/templates/sonarr.yaml"
ROLE_TEMPLATE_DST="$ROLES_DIR/templates/${CHART_NAME}.yaml"
if [[ -f "$ROLE_TEMPLATE_SRC" ]]; then
  sed \
    -e "s/sonarr/${CHART_NAME}/g" \
    -e "s|charts/media/sonarr|charts/media/${CHART_NAME}|g" \
    "$ROLE_TEMPLATE_SRC" > "$ROLE_TEMPLATE_DST"
  echo "Created role template: $ROLE_TEMPLATE_DST"

  # Add applications.<chart>: false to roles/media/values.yaml if not present
  ROLE_VALUES="$ROLES_DIR/values.yaml"
  if ! grep -Eq "^[[:space:]]${CHART_NAME}:[[:space:]]" "$ROLE_VALUES"; then
    # Insert after the applications: header
    awk -v key="$CHART_NAME" '
      BEGIN{added=0}
      /^applications:[[:space:]]*$/ {print; print "  " key ": false"; next}
      {print}
    ' "$ROLE_VALUES" > "$ROLE_VALUES.tmp"
    # If not added (no applications header?), append a minimal block
    if ! grep -q "^  ${CHART_NAME}:" "$ROLE_VALUES.tmp"; then
      {
        echo "applications:"
        echo "  ${CHART_NAME}: false"
      } >> "$ROLE_VALUES.tmp"
    fi
    mv "$ROLE_VALUES.tmp" "$ROLE_VALUES"
    echo "Updated roles/media/values.yaml with applications.${CHART_NAME}: false"
  fi
else
  echo "Warning: role template source not found ($ROLE_TEMPLATE_SRC); skipping role creation." >&2
fi

echo "Scaffold complete. Review the new chart at: charts/media/${CHART_NAME}"
echo "Enable it by setting roles/media values: applications.${CHART_NAME}: true and commit the changes."
