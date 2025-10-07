#!/bin/bash
set -euo pipefail

# Icon validation script for Helm charts
# Validates icon fields in values.yaml files and suggests defaults based on prefixes
# Supports both Iconify icons (e.g., simple-icons:github) and HTTP URL icons
# Optionally validates icons online using Iconify API and HTTP requests

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
ONLINE_VALIDATION=false
API_TIMEOUT=5
CACHE_DIR="/tmp/iconify-cache-$$"

# Track validation state
has_errors=false
has_warnings=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --online)
            ONLINE_VALIDATION=true
            shift
            ;;
        --timeout)
            API_TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--online] [--timeout SECONDS]"
            echo "  --online    Enable online validation using Iconify API and HTTP requests"
            echo "  --timeout   Timeout in seconds for API and HTTP requests (default: 5)"
            echo ""
            echo "Validates both Iconify icons (simple-icons:name) and HTTP URL icons"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create cache directory for online validation
if [ "$ONLINE_VALIDATION" = true ]; then
    mkdir -p "$CACHE_DIR"
    trap 'rm -rf "$CACHE_DIR"' EXIT
fi

# Function to parse icon into collection and name
parse_icon() {
    local icon="$1"
    local collection=""
    local icon_name=""

    if [[ "$icon" == *:* ]]; then
        # Icon has collection prefix (e.g., "mdi:robot", "simple-icons:youtube", "lucide:heart")
        collection="${icon%%:*}"
        icon_name="${icon#*:}"
    else
        # No collection specified, assume mdi
        collection="mdi"
        icon_name="$icon"
    fi

    echo "$collection:$icon_name"
}

# Function to validate HTTP URL format for icons
validate_url_format() {
    local url="$1"

    # Check if URL starts with http or https
    if [[ "$url" =~ ^https?:// ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate HTTP URL icon online
validate_url_icon_online() {
    local url="$1"
    local status_code

    # Use HEAD request to check if URL is accessible without downloading the full content
    status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$API_TIMEOUT" -L "$url" 2>/dev/null)

    case "$status_code" in
        "200"|"201"|"202"|"204")
            return 0  # Success
            ;;
        "000")
            return 2  # Network error (timeout, connection refused, etc.)
            ;;
        *)
            return 1  # HTTP error (404, 403, 500, etc.)
            ;;
    esac
}

# Function to validate icon format generically
validate_icon_format() {
    local icon="$1"

    # Check if it's an HTTP URL first
    if validate_url_format "$icon"; then
        return 0
    fi

    # Otherwise parse as Iconify format
    local parsed
    parsed=$(parse_icon "$icon")
    local collection="${parsed%:*}"
    local icon_name="${parsed#*:}"

    # Basic validation rules based on collection
    case "$collection" in
        "simple-icons")
            # Simple Icons: lowercase, numbers, hyphens, dots
            if [[ "$icon_name" =~ ^[a-z0-9]([a-z0-9\.-]*[a-z0-9])?$ ]]; then
                return 0
            else
                return 1
            fi
            ;;
        *)
            # MDI and most other collections: lowercase, numbers, hyphens
            if [[ "$icon_name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
                return 0
            else
                return 1
            fi
            ;;
    esac
}

# Function to validate icon online using Iconify API
validate_icon_online() {
    local icon="$1"
    local parsed
    parsed=$(parse_icon "$icon")
    local collection="${parsed%:*}"
    local icon_name="${parsed#*:}"

    # Cache file for this specific icon
    local cache_file="$CACHE_DIR/${collection}_${icon_name}.json"

    # Check cache first
    if [ ! -f "$cache_file" ]; then
        # Fetch specific icon data from collection
        if ! curl -s --max-time "$API_TIMEOUT" "https://api.iconify.design/${collection}.json?icons=${icon_name}" > "$cache_file" 2>/dev/null; then
            return 2  # Network error
        fi
    fi

    # Check if icon exists in response
    if jq -e ".icons.\"$icon_name\" != null" "$cache_file" >/dev/null 2>&1; then
        return 0  # Icon exists
    else
        return 1  # Icon does not exist
    fi
}

# Function to check network connectivity to Iconify API
check_api_connectivity() {
    curl -s --max-time 3 "https://api.iconify.design/collections" >/dev/null 2>&1
}

# Function to search for simple-icons by name online
search_simple_icons() {
    local search_term="$1"
    local cache_file="$CACHE_DIR/simple-icons-search.json"

    # Get simple-icons collection data if not cached
    if [ ! -f "$cache_file" ]; then
        if ! curl -s --max-time "$API_TIMEOUT" "https://api.iconify.design/simple-icons.json" > "$cache_file" 2>/dev/null; then
            return 1  # Network error or API unavailable
        fi
    fi

    # Search for icons that match the search term
    # Look for exact matches first, then partial matches
    local matches
    matches=$(jq -r ".icons | keys[] | select(test(\"^${search_term}$\"; \"i\"))" "$cache_file" 2>/dev/null | head -1)

    if [ -n "$matches" ]; then
        echo "simple-icons:$matches"
        return 0
    fi

    # If no exact match, try partial match
    matches=$(jq -r ".icons | keys[] | select(test(\"${search_term}\"; \"i\"))" "$cache_file" 2>/dev/null | head -1)

    if [ -n "$matches" ]; then
        echo "simple-icons:$matches"
        return 0
    fi

    return 1  # No matches found
}

# Function to suggest default icon based on app name and category
suggest_default_icon() {
    local app_name="$1"
    local category="$2"

    # First try to find a simple-icons match online if available
    if [ "$ONLINE_VALIDATION" = true ] || check_api_connectivity 2>/dev/null; then
        # Try searching for the app name directly
        local online_suggestion
        online_suggestion=$(search_simple_icons "$app_name" 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$online_suggestion" ]; then
            echo "$online_suggestion"
            return
        fi

        # Try common brand variations for media apps
        case "$app_name" in
            *tube*)
                online_suggestion=$(search_simple_icons "youtube" 2>/dev/null)
                if [ $? -eq 0 ] && [ -n "$online_suggestion" ]; then
                    echo "$online_suggestion"
                    return
                fi
                ;;
        esac
    fi

    # Fallback to hardcoded suggestions when online search fails or is unavailable
    case "$category" in
        "ai")
            case "$app_name" in
                *llm*|*gpt*|*ai*|*ollama*|*litellm*) echo "robot" ;;
                *webui*|*interface*|*ui*) echo "web" ;;
                *) echo "brain" ;;
            esac
            ;;
        "media")
            case "$app_name" in
                *sonarr*) echo "simple-icons:sonarr" ;;
                *radarr*) echo "simple-icons:radarr" ;;
                *lidarr*) echo "music-box" ;;
                *prowlarr*) echo "cloud-search" ;;
                *bazarr*|*subtitles*) echo "subtitles" ;;
                *book*|*read*|*kavita*) echo "book" ;;
                *youtube*|*tube*) echo "simple-icons:youtube" ;;
                *plex*) echo "simple-icons:plex" ;;
                *jellyfin*) echo "simple-icons:jellyfin" ;;
                *) echo "play-circle" ;;
            esac
            ;;
        "utilities")
            case "$app_name" in
                *draw*|*excalidraw*) echo "mdi:draw-pen" ;;
                *note*|*pad*) echo "note-edit" ;;
                *file*|*manager*) echo "folder" ;;
                *) echo "tools" ;;
            esac
            ;;
        *)
            echo "application"
            ;;
    esac
}

echo "🎨 Validating icons in Helm charts$([ "$ONLINE_VALIDATION" = true ] && echo " (online mode)" || echo " (offline mode)")..."

# Check API connectivity if online validation is enabled
if [ "$ONLINE_VALIDATION" = true ]; then
    echo -n "🌐 Checking Iconify API connectivity... "
    if check_api_connectivity; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}⚠️  Online validation disabled - API not reachable${NC}"
        ONLINE_VALIDATION=false
    fi
fi

# Check each chart directory
for category in charts/*/; do
    if [ -d "$category" ]; then
        category_name=$(basename "$category")

        for chart_dir in "$category"*/; do
            if [ -f "$chart_dir/Chart.yaml" ] && [ -f "$chart_dir/values.yaml" ]; then
                chart_name=$(basename "$chart_dir")
                values_file="$chart_dir/values.yaml"

                # Check if values.yaml has an application section
                if ! grep -q "^application:" "$values_file"; then
                    # No application section, skip icon/image validation for this chart
                    continue
                fi

                # Extract icon and image values from values.yaml
                icon_line=$(grep -n "^  icon:" "$values_file" || echo "")
                image_line=$(grep -n "^  image:" "$values_file" || echo "")

                # Check icon field first
                if [ -n "$icon_line" ]; then
                    icon_value=$(echo "$icon_line" | sed 's/.*icon: *\(.*\)$/\1/' | tr -d '"' | tr -d "'")
                    line_number=$(echo "$icon_line" | cut -d: -f1)

                    # Check if icon is empty
                    if [ -z "$icon_value" ] || [ "$icon_value" = "\"\"" ] || [ "$icon_value" = "''" ]; then
                        suggested_icon=$(suggest_default_icon "$chart_name" "$category_name")
                        echo -e "  ${YELLOW}⚠️${NC}  $chart_name (line $line_number): Icon is empty, suggested default: ${BLUE}$suggested_icon${NC}"
                        has_warnings=true
                    else
                        # Validate icon format
                        if validate_icon_format "$icon_value"; then
                            # Icon format is valid, now check online if enabled
                            if [ "$ONLINE_VALIDATION" = true ]; then
                                # Check if it's a URL or Iconify icon and validate accordingly
                                if validate_url_format "$icon_value"; then
                                    # It's a URL - validate URL accessibility
                                    online_result=$(validate_url_icon_online "$icon_value"; echo $?)
                                    case $online_result in
                                        0)
                                            echo -e "  ${GREEN}✅${NC} $chart_name: Icon URL '$icon_value' is accessible ${PURPLE}(verified online)${NC}"
                                            ;;
                                        1)
                                            echo -e "  ${RED}❌${NC} $chart_name (line $line_number): Icon URL '$icon_value' returned HTTP error (404, 403, etc.)"
                                            has_errors=true
                                            ;;
                                        2)
                                            echo -e "  ${YELLOW}⚠️${NC}  $chart_name: Icon URL '$icon_value' format valid ${YELLOW}(online check failed - network error)${NC}"
                                            has_warnings=true
                                            ;;
                                    esac
                                else
                                    # It's an Iconify icon - validate against Iconify database
                                    online_result=$(validate_icon_online "$icon_value"; echo $?)
                                    case $online_result in
                                        0)
                                            echo -e "  ${GREEN}✅${NC} $chart_name: Icon '$icon_value' is valid ${PURPLE}(verified online)${NC}"
                                            ;;
                                        1)
                                            echo -e "  ${RED}❌${NC} $chart_name (line $line_number): Icon '$icon_value' not found in Iconify database"
                                            has_errors=true
                                            ;;
                                        2)
                                            echo -e "  ${YELLOW}⚠️${NC}  $chart_name: Icon '$icon_value' format valid ${YELLOW}(online check failed - network error)${NC}"
                                            has_warnings=true
                                            ;;
                                    esac
                                fi
                            else
                                # Offline mode - just validate format
                                if validate_url_format "$icon_value"; then
                                    echo -e "  ${GREEN}✅${NC} $chart_name: Icon URL '$icon_value' format is valid"
                                else
                                    echo -e "  ${GREEN}✅${NC} $chart_name: Icon '$icon_value' format is valid"
                                fi
                            fi
                        else
                            # Icon format is invalid
                            # Check if it looks like a malformed URL
                            if [[ "$icon_value" =~ ^https?:// ]] || [[ "$icon_value" =~ \. ]]; then
                                echo -e "  ${RED}❌${NC} $chart_name (line $line_number): Invalid URL format '$icon_value'. URLs should start with 'http://' or 'https://'"
                                has_errors=true
                            else
                                # It's an Iconify format icon with invalid format
                                parsed=$(parse_icon "$icon_value")
                                collection="${parsed%:*}"

                                case "$collection" in
                                    "simple-icons")
                                        echo -e "  ${RED}❌${NC} $chart_name (line $line_number): Invalid simple-icons format. Should be 'simple-icons:iconname' with lowercase letters, numbers, hyphens, and dots only."
                                        has_errors=true
                                        ;;
                                    *)
                                        suggested_icon=$(suggest_default_icon "$chart_name" "$category_name")
                                        echo -e "  ${YELLOW}⚠️${NC}  $chart_name (line $line_number): Icon '$icon_value' doesn't follow $collection naming convention, suggested: ${BLUE}$suggested_icon${NC}"
                                        has_warnings=true
                                        ;;
                                esac
                            fi
                        fi
                    fi
                else
                    # No icon field found
                    suggested_icon=$(suggest_default_icon "$chart_name" "$category_name")
                    echo -e "  ${YELLOW}⚠️${NC}  $chart_name: No icon field found, suggested: ${BLUE}$suggested_icon${NC}"
                    has_warnings=true
                fi

                # Now check image field for HTTP URL icons
                if [ -n "$image_line" ]; then
                    image_value=$(echo "$image_line" | sed 's/.*image: *\(.*\)$/\1/' | tr -d '"' | tr -d "'")
                    image_line_number=$(echo "$image_line" | cut -d: -f1)

                    # Check if image is empty
                    if [ -z "$image_value" ] || [ "$image_value" = "\"\"" ] || [ "$image_value" = "''" ]; then
                        echo -e "  ${YELLOW}⚠️${NC}  $chart_name (line $image_line_number): Image field is empty"
                        has_warnings=true
                    else
                        # Validate image format (should be HTTP URL)
                        if validate_url_format "$image_value"; then
                            # Image format is valid, now check online if enabled
                            if [ "$ONLINE_VALIDATION" = true ]; then
                                online_result=$(validate_url_icon_online "$image_value"; echo $?)
                                case $online_result in
                                    0)
                                        echo -e "  ${GREEN}✅${NC} $chart_name: Image URL '$image_value' is accessible ${PURPLE}(verified online)${NC}"
                                        ;;
                                    1)
                                        echo -e "  ${RED}❌${NC} $chart_name (line $image_line_number): Image URL '$image_value' returned HTTP error (404, 403, etc.)"
                                        has_errors=true
                                        ;;
                                    2)
                                        echo -e "  ${YELLOW}⚠️${NC}  $chart_name: Image URL '$image_value' format valid ${YELLOW}(online check failed - network error)${NC}"
                                        has_warnings=true
                                        ;;
                                esac
                            else
                                echo -e "  ${GREEN}✅${NC} $chart_name: Image URL '$image_value' format is valid"
                            fi
                        else
                            echo -e "  ${RED}❌${NC} $chart_name (line $image_line_number): Invalid image URL format '$image_value'. URLs should start with 'http://' or 'https://'"
                            has_errors=true
                        fi
                    fi
                fi
            fi
        done
    fi
done

echo ""
echo "— Icon validation summary —"

if [ "$has_errors" = true ]; then
    echo -e "${RED}❌ Icon validation failed - fix the errors above${NC}"
    exit 1
elif [ "$has_warnings" = true ]; then
    echo -e "${YELLOW}⚠️  Icon validation completed with warnings${NC}"
    echo -e "    ${YELLOW}ℹ️  Use --online flag for Iconify database and URL verification${NC}"
else
    echo -e "${GREEN}✅ Icon validation passed${NC}"
    if [ "$ONLINE_VALIDATION" = true ]; then
        echo -e "    ${PURPLE}🌐 All icons verified online (Iconify database + URL accessibility)${NC}"
    else
        echo -e "    ${BLUE}ℹ️  Add --online flag to verify icons online (Iconify database + URL accessibility)${NC}"
    fi
fi
