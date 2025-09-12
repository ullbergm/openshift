#!/usr/bin/env bash
set -euo pipefail

# Scaffold a new chart by copying charts/media/sonarr and customizing.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
SRC_CHART_DIR="$ROOT_DIR/charts/media/sonarr"

if [[ ! -d "$SRC_CHART_DIR" ]]; then
  echo "Source chart not found: $SRC_CHART_DIR" >&2
  exit 1
fi

echo "This wizard will scaffold a new chart based on Sonarr."

# Ask for the group first
echo "Available groups:"
ls -1 "$ROOT_DIR/charts/"
echo
read -rp "Which group will this chart belong to? " CHART_GROUP
if [[ -z "${CHART_GROUP}" ]]; then
  echo "Chart group is required." >&2
  exit 1
fi

# Validate that the group exists
if [[ ! -d "$ROOT_DIR/charts/$CHART_GROUP" ]]; then
  echo "Group '$CHART_GROUP' does not exist in charts/ directory." >&2
  echo "Available groups: $(ls -1 "$ROOT_DIR/charts/" | tr '\n' ' ')" >&2
  exit 1
fi

read -rp "New chart machine name (lowercase, no spaces, e.g. 'readarr'): " CHART_NAME
if [[ -z "${CHART_NAME}" ]]; then
  echo "Chart name is required." >&2
  exit 1
fi

if [[ "$CHART_NAME" =~ [A-Z\ ] ]]; then
  echo "Chart name must be lowercase and contain no spaces." >&2
  exit 1
fi

TARGET_CHART_DIR="$ROOT_DIR/charts/$CHART_GROUP/$CHART_NAME"
if [[ -e "$TARGET_CHART_DIR" ]]; then
  echo "Target chart already exists: $TARGET_CHART_DIR" >&2
  exit 1
fi

DEFAULT_DISPLAY_NAME="$(echo "$CHART_NAME" | sed -E 's/(^|[-_])(\w)/\U\2/g')"
read -rp "Display name (Application.name) [${DEFAULT_DISPLAY_NAME}]: " DISPLAY_NAME
DISPLAY_NAME=${DISPLAY_NAME:-$DEFAULT_DISPLAY_NAME}

read -rp "Description: " DESCRIPTION || true

# Set app group based on selected chart group with capitalization
DEFAULT_APP_GROUP="$(echo "$CHART_GROUP" | sed -E 's/(^|[-_])(\w)/\U\2/g')"
read -rp "App group (Application.group) [${DEFAULT_APP_GROUP}]: " APP_GROUP
APP_GROUP=${APP_GROUP:-$DEFAULT_APP_GROUP}

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

# Add the new application to the appropriate ApplicationSet template
APPLICATIONSET_TEMPLATE="$ROOT_DIR/cluster/templates/${CHART_GROUP}.yaml"
if [[ -f "$APPLICATIONSET_TEMPLATE" ]]; then
  # Check if the chart name already exists in the ApplicationSet
  if ! grep -q "name: ${CHART_NAME}" "$APPLICATIONSET_TEMPLATE"; then
    # Find the line with "elements:" and add the new chart after the last "- name:" entry
    awk -v new_chart="$CHART_NAME" '
      /^[[:space:]]*elements:[[:space:]]*$/ {
        in_elements=1
        print
        next
      }
      in_elements && /^[[:space:]]*-[[:space:]]*name:/ {
        last_name_line=NR
        print
        next
      }
      in_elements && /^[[:space:]]*$/ {
        # Empty line in elements section, continue
        print
        next
      }
      in_elements && !/^[[:space:]]*-[[:space:]]*name:/ && !/^[[:space:]]*$/ {
        # End of elements section
        if (last_name_line > 0) {
          print "        - name: " new_chart
        }
        in_elements=0
        print
        next
      }
      {print}
    ' "$APPLICATIONSET_TEMPLATE" > "$APPLICATIONSET_TEMPLATE.tmp"

    # If no elements section was found, we need a different approach
    if ! grep -q "name: ${CHART_NAME}" "$APPLICATIONSET_TEMPLATE.tmp"; then
      echo "Warning: Could not automatically add ${CHART_NAME} to ${APPLICATIONSET_TEMPLATE}." >&2
      echo "Please manually add '        - name: ${CHART_NAME}' to the elements list." >&2
      rm "$APPLICATIONSET_TEMPLATE.tmp"
    else
      mv "$APPLICATIONSET_TEMPLATE.tmp" "$APPLICATIONSET_TEMPLATE"
      echo "Added ${CHART_NAME} to ApplicationSet template: ${APPLICATIONSET_TEMPLATE}"
    fi
  else
    echo "Chart ${CHART_NAME} already exists in ApplicationSet template."
  fi
else
  echo "Warning: ApplicationSet template not found ($APPLICATIONSET_TEMPLATE); skipping ApplicationSet update." >&2
fi

echo "Scaffold complete. Review the new chart at: charts/${CHART_GROUP}/${CHART_NAME}"
echo "The chart has been added to the ApplicationSet template and will be deployed automatically."
