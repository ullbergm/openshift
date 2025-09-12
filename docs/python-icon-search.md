# Python Icon Search Tool

This is an enhanced Python version of the original bash `find-icons.sh` script. It leverages Python's rich ecosystem to provide superior performance, better user experience, and advanced features.

## Features

### 🚀 Performance Enhancements

- **Async/Await Operations**: Concurrent API requests using `aiohttp` for faster searches
- **Smart Collection Prioritization**: Intelligent ordering based on relevance and popularity
- **Connection Pooling**: Efficient HTTP connection management
- **Semaphore-based Concurrency**: Controlled parallel requests to avoid API rate limits

### 🎨 Enhanced User Experience

- **Rich Terminal Output**: Beautiful formatting with colors, tables, and progress bars using the `rich` library
- **Interactive Progress Tracking**: Real-time progress indicators for long-running searches
- **Intelligent Result Scoring**: Advanced relevance algorithms considering multiple factors
- **Structured Result Presentation**: Organized tables grouped by collection

### 📊 Advanced Features

- **JSON Export**: Export search results for further processing or analysis
- **Detailed Icon Information**: Fetch dimensions and metadata when requested
- **Custom Collections**: Specify exact collections to search
- **Flexible Filtering**: Minimum score thresholds and result limits
- **Comprehensive Error Handling**: Graceful handling of network issues and API errors

### 🔧 Intelligent Scoring System

The Python version includes a sophisticated scoring algorithm that considers:

- Exact matches (highest priority)
- Prefix matches
- Substring matches
- Fuzzy matching for word variations
- Collection priority (simple-icons, mdi, etc.)
- Name length penalties for overly verbose results

## Installation

```bash
# Install dependencies
pip install aiohttp click rich

# Or use the requirements file
pip install -r scripts/requirements.txt

# Make executable
chmod +x scripts/find-icons.py
```

## Usage

### Basic Usage

```bash
./scripts/find-icons.py plex
./scripts/find-icons.py "visual studio code"
```

### Advanced Options

```bash
# Verbose output with detailed logging
./scripts/find-icons.py docker --verbose

# Search all available collections (200+)
./scripts/find-icons.py unifi --all-collections

# Get detailed information about top results
./scripts/find-icons.py plex --details

# Export results to JSON
./scripts/find-icons.py docker --export results.json

# Custom collection search
./scripts/find-icons.py react --collections simple-icons mdi logos

# Filter by minimum relevance score
./scripts/find-icons.py app --min-score 50.0

# Adjust API timeout and result limits
./scripts/find-icons.py search --timeout 15 --max-results 20
```

## Configuration

The script includes several configuration options in the `IconSearchConfig` class:

```python
# API Configuration
API_BASE_URL = "https://api.iconify.design"
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RESULTS = 10
CONCURRENT_REQUESTS = 5

# Preferred Collections (in priority order)
PREFERRED_COLLECTIONS = [
    "simple-icons",    # Brand icons - highest priority
    "mdi",            # Material Design Icons
    "lucide",         # Lucide icons
    "tabler",         # Tabler icons
    "heroicons",      # Hero icons
    "fa6-brands",     # FontAwesome brands
    "logos",          # Various logos
    "devicon",        # Developer icons
]
```

## Output Examples

### Standard Output

The tool provides beautifully formatted tables grouped by collection, showing:

- Icon name
- Full collection:name format
- Relevance score
- Dimensions (when using --details)

### JSON Export Format

```json
{
  "search_term": "docker",
  "timestamp": 1757686013.6060321,
  "results": [
    {
      "name": "tabler:brand-docker",
      "collection": "tabler",
      "full_name": "tabler:tabler:brand-docker",
      "score": 97.5,
      "width": null,
      "height": null
    }
  ]
}
```

## Comparison with Bash Version

| Feature            | Bash Script         | Python Script                 |
| ------------------ | ------------------- | ----------------------------- |
| **Performance**    | Sequential requests | Concurrent async requests     |
| **Output**         | Plain text          | Rich formatted tables         |
| **Progress**       | Basic logging       | Interactive progress bars     |
| **Scoring**        | Simple matching     | Advanced relevance algorithm  |
| **Export**         | None                | JSON export with metadata     |
| **Error Handling** | Basic               | Comprehensive with retries    |
| **Dependencies**   | curl, jq            | aiohttp, rich, click          |
| **Extensibility**  | Limited             | Highly modular and extensible |

## Architecture

### Key Components

1. **IconifyAPI**: Async HTTP client with connection pooling
2. **IconSearcher**: Main orchestrator with scoring and formatting
3. **IconResult**: Data class for structured results
4. **CollectionInfo**: Metadata about icon collections
5. **IconSearchConfig**: Centralized configuration

### Async Design

The tool uses Python's `asyncio` for concurrent operations:

- Multiple collection searches run in parallel
- Semaphore controls concurrent request limits
- Connection pooling reduces overhead
- Progress tracking provides real-time feedback

## Best Practices

### Performance

- Use `--all-collections` sparingly (searches 200+ collections)
- Adjust `--timeout` based on network conditions
- Use `--min-score` to filter irrelevant results
- Consider `--max-results` to limit API calls

### Usage in Helm Charts

The tool provides direct copy-paste recommendations:

```yaml
# Example output for Helm values.yaml
icon: simple-icons:plex  # Preferred brand icon
icon: mdi:docker        # Alternative material design
```

### Integration

- Export results to JSON for CI/CD integration
- Use custom collections for organization-specific icon sets
- Combine with validation scripts for automated workflows

## Error Handling

The Python version includes robust error handling:

- Network timeouts and connection errors
- API rate limiting and HTTP errors
- Invalid JSON responses
- Missing dependencies with helpful messages
- Keyboard interrupt handling (Ctrl+C)

## Future Enhancements

Potential improvements for future versions:

- **Caching**: Local cache for frequently searched terms
- **Icon Preview**: Terminal-based icon rendering
- **Batch Processing**: Search multiple terms at once
- **Configuration Files**: User-specific settings and preferences
- **Plugin System**: Custom scoring algorithms and output formats
- **Web Interface**: Browser-based search and preview
- **Integration APIs**: Direct Helm chart and Kubernetes manifest generation

## Dependencies

- **aiohttp**: Async HTTP client for API requests
- **rich**: Terminal formatting and progress bars
- **click**: Command-line interface utilities (imported but not fully utilized yet)

Optional future dependencies:

- **Pillow**: For icon preview and processing
- **typer**: Enhanced CLI with auto-completion
- **pydantic**: Data validation and settings management
