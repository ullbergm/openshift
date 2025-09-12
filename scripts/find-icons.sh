#!/bin/bash
set -euo pipefail

# Icon search script using Iconify API
# Searches for icons for a given application name with preference for simple-icons

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="https://api.iconify.design"
API_TIMEOUT=10
MAX_RESULTS=10
PREFERRED_COLLECTIONS=("simple-icons" "mdi" "lucide" "tabler" "heroicons")

# Global variables
SEARCH_TERM=""
SHOW_HELP=false
VERBOSE=false

# Usage function
usage() {
    cat << EOF
Usage: $0 <application-name> [options]

Search for icons using the Iconify API with preference for simple-icons.

ARGUMENTS:
    application-name    The name of the application to search icons for

OPTIONS:
    -h, --help         Show this help message
    -v, --verbose      Enable verbose output
    --timeout SECONDS  API request timeout (default: 10)
    --max-results N    Maximum number of results per collection (default: 10)

EXAMPLES:
    $0 plex
    $0 "visual studio code" --verbose
    $0 jellyfin --max-results 5

OUTPUT:
    Returns matching icons in order of preference:
    1. simple-icons (brand icons) - preferred for applications
    2. mdi (Material Design Icons)
    3. lucide, tabler, heroicons (other popular collections)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                SHOW_HELP=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --timeout)
                if [[ -n "${2:-}" ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
                    API_TIMEOUT="$2"
                    shift 2
                else
                    echo -e "${RED}Error: --timeout requires a numeric value${NC}" >&2
                    exit 1
                fi
                ;;
            --max-results)
                if [[ -n "${2:-}" ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
                    MAX_RESULTS="$2"
                    shift 2
                else
                    echo -e "${RED}Error: --max-results requires a numeric value${NC}" >&2
                    exit 1
                fi
                ;;
            -*)
                echo -e "${RED}Error: Unknown option '$1'${NC}" >&2
                usage
                exit 1
                ;;
            *)
                if [[ -z "$SEARCH_TERM" ]]; then
                    SEARCH_TERM="$1"
                else
                    echo -e "${RED}Error: Multiple search terms provided. Use quotes for multi-word terms.${NC}" >&2
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

# Logging function
log() {
    local level="$1"
    shift
    case "$level" in
        "INFO")
            [[ "$VERBOSE" == true ]] && echo -e "${BLUE}[INFO]${NC} $*" >&2
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $*" >&2
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $*" >&2
            ;;
    esac
}

# Function to check if required tools are available
check_dependencies() {
    local missing_tools=()

    if ! command -v curl >/dev/null 2>&1; then
        missing_tools+=("curl")
    fi

    if ! command -v jq >/dev/null 2>&1; then
        missing_tools+=("jq")
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log "ERROR" "Missing required tools: ${missing_tools[*]}"
        log "ERROR" "Please install the missing tools and try again"
        exit 1
    fi
}

# Function to search icons in a specific collection
search_collection() {
    local collection="$1"
    local search_term="$2"
    local url="${API_BASE_URL}/search?query=${search_term}&collection=${collection}&limit=${MAX_RESULTS}"

    log "INFO" "Searching in collection: $collection"

    # Make API request with error handling
    local response
    local http_code

    response=$(curl -s --max-time "$API_TIMEOUT" -w "%{http_code}" "$url" 2>/dev/null)
    http_code="${response: -3}"
    response="${response%???}"

    if [[ "$http_code" -ne 200 ]]; then
        log "WARN" "API request failed for collection $collection (HTTP $http_code)"
        return 1
    fi

    # Parse JSON response
    local icons
    if ! icons=$(echo "$response" | jq -r '.icons[]?' 2>/dev/null); then
        log "WARN" "No icons found in collection: $collection"
        return 1
    fi

    # Return results if any found
    if [[ -n "$icons" ]]; then
        echo "$icons"
        return 0
    else
        log "INFO" "No icons found in collection: $collection"
        return 1
    fi
}

# Function to search all collections
search_all_collections() {
    local search_term="$1"
    local found_any=false

    log "INFO" "Searching for icons matching: '$search_term'"
    echo

    for collection in "${PREFERRED_COLLECTIONS[@]}"; do
        echo -e "${CYAN}=== Collection: $collection ===${NC}"

        if search_collection "$collection" "$search_term"; then
            found_any=true
        else
            echo -e "${YELLOW}No results found${NC}"
        fi

        echo
    done

    if [[ "$found_any" == false ]]; then
        log "WARN" "No icons found in any collection for: '$search_term'"
        echo
        echo -e "${YELLOW}Suggestions:${NC}"
        echo "  - Try a shorter or more generic term"
        echo "  - Check spelling"
        echo "  - Try searching for the company/brand name instead of the full product name"
        echo "  - Some applications may not have dedicated icons in icon collections"
        return 1
    fi

    return 0
}

# Function to get icon details
get_icon_details() {
    local full_icon="$1"  # e.g., "simple-icons:plex"
    local collection="${full_icon%%:*}"
    local icon_name="${full_icon#*:}"

    local url="${API_BASE_URL}/${collection}.json?icons=${icon_name}"

    log "INFO" "Getting details for: $full_icon"

    local response
    local http_code

    response=$(curl -s --max-time "$API_TIMEOUT" -w "%{http_code}" "$url" 2>/dev/null)
    http_code="${response: -3}"
    response="${response%???}"

    if [[ "$http_code" -ne 200 ]]; then
        log "ERROR" "Failed to get icon details (HTTP $http_code)"
        return 1
    fi

    # Extract and display relevant information
    local width height prefix
    width=$(echo "$response" | jq -r '.width // "N/A"' 2>/dev/null)
    height=$(echo "$response" | jq -r '.height // "N/A"' 2>/dev/null)
    prefix=$(echo "$response" | jq -r '.prefix // "N/A"' 2>/dev/null)

    # Check if the icon exists in the response
    local icon_exists
    icon_exists=$(echo "$response" | jq -r ".icons.\"${icon_name}\" // false" 2>/dev/null)

    if [[ "$icon_exists" == "false" ]]; then
        log "WARN" "Icon '$icon_name' not found in collection '$collection'"
        return 1
    fi

    echo -e "${GREEN}Icon Details:${NC}"
    echo "  Full Name: $full_icon"
    echo "  Collection: $prefix"
    echo "  Dimensions: ${width}x${height}"

    if [[ "$collection" == "simple-icons" ]]; then
        echo -e "${PURPLE}  Note: simple-icons are typically brand/company logos${NC}"
    fi

    return 0
}

# Function to provide usage recommendations
show_recommendations() {
    local search_term="$1"

    echo -e "${CYAN}=== Usage Recommendations ===${NC}"
    echo
    echo -e "${GREEN}For Helm Chart values.yaml:${NC}"
    echo "  Use the full collection:name format in your values.yaml file:"
    echo "    icon: simple-icons:${search_term,,}  # Preferred for brand icons"
    echo "    icon: mdi:${search_term,,}          # Alternative if simple-icons not available"
    echo
    echo -e "${GREEN}Icon Validation:${NC}"
    echo "  Run './scripts/validate-icons.sh --online' to validate your icon choices"
    echo
    echo -e "${GREEN}Fallback Options:${NC}"
    echo "  If no suitable icons are found, consider:"
    echo "  - Using a generic icon (mdi:application, mdi:server, etc.)"
    echo "  - Using the application's favicon URL"
    echo "  - Creating a custom icon"
}

# Main function
main() {
    parse_args "$@"

    if [[ "$SHOW_HELP" == true ]]; then
        usage
        exit 0
    fi

    if [[ -z "$SEARCH_TERM" ]]; then
        echo -e "${RED}Error: Application name is required${NC}" >&2
        echo
        usage
        exit 1
    fi

    check_dependencies

    echo -e "${PURPLE}Iconify Icon Search Tool${NC}"
    echo -e "${PURPLE}=========================${NC}"
    echo

    # Search for icons
    if search_all_collections "$SEARCH_TERM"; then
        echo
        show_recommendations "$SEARCH_TERM"
    fi

    # If verbose mode, show additional info for the first simple-icons match
    if [[ "$VERBOSE" == true ]]; then
        echo
        echo -e "${CYAN}=== Detailed Information ===${NC}"

        # Try to get details for simple-icons first
        local simple_icon="simple-icons:${SEARCH_TERM,,}"
        if get_icon_details "$simple_icon" 2>/dev/null; then
            :  # Success
        else
            log "INFO" "No detailed information available for simple-icons:${SEARCH_TERM,,}"
        fi
    fi
}

# Run main function with all arguments
main "$@"
