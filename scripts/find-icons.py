#!/usr/bin/env python3
"""
Iconify Icon Search Tool - Python Edition

A comprehensive icon search utility using the Iconify API with enhanced features
leveraging Python's rich ecosystem for better performance and functionality.
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import quote

import aiohttp
import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


@dataclass
class IconResult:
    """Represents an icon search result."""
    name: str
    collection: str
    full_name: str
    score: float = 0.0
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class CollectionInfo:
    """Information about an icon collection."""
    name: str
    title: str
    author: str
    license: str
    total_icons: int
    priority: int = 0


class IconSearchConfig:
    """Configuration for the icon search."""

    API_BASE_URL = "https://api.iconify.design"
    DEFAULT_TIMEOUT = 10
    DEFAULT_MAX_RESULTS = 10
    CONCURRENT_REQUESTS = 5

    # Collection priorities for scoring
    COLLECTION_PRIORITIES = {
        "simple-icons": 100,
        "mdi": 90,
        "lucide": 80,
        "tabler": 75,
        "heroicons": 70,
        "fa6-brands": 85,
        "logos": 95,
        "devicon": 88,
    }


class IconifyAPI:
    """Async client for Iconify API."""

    def __init__(self, timeout: int = IconSearchConfig.DEFAULT_TIMEOUT):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.console = Console()

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(limit=IconSearchConfig.CONCURRENT_REQUESTS)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_collections(self) -> Dict[str, CollectionInfo]:
        """Fetch all available collections with metadata."""
        url = f"{IconSearchConfig.API_BASE_URL}/collections"

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )

                data = await response.json()
                collections = {}

                for name, info in data.items():
                    collections[name] = CollectionInfo(
                        name=name,
                        title=info.get('name', name),
                        author=info.get('author', {}).get('name', 'Unknown'),
                        license=info.get('license', {}).get('title', 'Unknown'),
                        total_icons=info.get('total', 0),
                        priority=IconSearchConfig.COLLECTION_PRIORITIES.get(name, 0)
                    )

                return collections

        except Exception as e:
            logging.error(f"Failed to fetch collections: {e}")
            raise

    async def search_collection(self, collection: str, query: str, limit: int) -> List[str]:
        """Search for icons in a specific collection."""
        encoded_query = quote(query)
        url = f"{IconSearchConfig.API_BASE_URL}/search"
        params = {
            'query': query,
            'collection': collection,
            'limit': limit
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logging.warning(f"Search failed for collection {collection}: HTTP {response.status}")
                    return []

                data = await response.json()
                return data.get('icons', [])

        except Exception as e:
            logging.warning(f"Error searching collection {collection}: {e}")
            return []

    async def get_icon_details(self, collection: str, icon_name: str) -> Optional[Dict]:
        """Get detailed information about a specific icon."""
        url = f"{IconSearchConfig.API_BASE_URL}/{collection}.json"
        params = {'icons': icon_name}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                icon_data = data.get('icons', {}).get(icon_name)

                if icon_data:
                    return {
                        'width': data.get('width'),
                        'height': data.get('height'),
                        'prefix': data.get('prefix'),
                        'icon_data': icon_data
                    }

                return None

        except Exception as e:
            logging.warning(f"Error getting icon details for {collection}:{icon_name}: {e}")
            return None


class IconSearcher:
    """Main icon search orchestrator."""

    def __init__(self, console: Console, verbose: bool = False):
        self.console = console
        self.verbose = verbose
        self.setup_logging()

    def setup_logging(self):
        """Setup logging with rich formatting."""
        log_level = logging.DEBUG if self.verbose else logging.INFO

        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, show_path=False)]
        )

    def calculate_relevance_score(self, icon_name: str, search_term: str, collection: str) -> float:
        """Calculate relevance score for an icon result."""
        icon_lower = icon_name.lower()
        search_lower = search_term.lower()

        # Base scoring
        score = 0.0

        # Exact match gets highest score
        if icon_lower == search_lower:
            score += 100

        # Starts with search term
        elif icon_lower.startswith(search_lower):
            score += 80

        # Contains search term
        elif search_lower in icon_lower:
            score += 60

        # Fuzzy matching for common variations
        search_parts = search_lower.replace('-', ' ').replace('_', ' ').split()
        icon_parts = icon_lower.replace('-', ' ').replace('_', ' ').split()

        matching_parts = len(set(search_parts) & set(icon_parts))
        if matching_parts > 0:
            score += (matching_parts / len(search_parts)) * 40

        # Collection priority bonus
        collection_bonus = IconSearchConfig.COLLECTION_PRIORITIES.get(collection, 0) / 10
        score += collection_bonus

        # Penalty for very long names (likely less relevant)
        if len(icon_name) > len(search_term) * 2:
            score -= 10

        return max(0, score)

    async def search_collections(
        self,
        api: IconifyAPI,
        search_term: str,
        collections: List[str],
        max_results: int
    ) -> List[IconResult]:
        """Search multiple collections concurrently."""

        semaphore = asyncio.Semaphore(IconSearchConfig.CONCURRENT_REQUESTS)

        async def search_single_collection(collection: str) -> List[IconResult]:
            async with semaphore:
                icons = await api.search_collection(collection, search_term, max_results)
                results = []

                for icon in icons:
                    score = self.calculate_relevance_score(icon, search_term, collection)
                    results.append(IconResult(
                        name=icon,
                        collection=collection,
                        full_name=f"{collection}:{icon}",
                        score=score
                    ))

                return results

        # Create tasks for concurrent execution
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=not self.verbose
        ) as progress:

            task = progress.add_task(
                f"Searching {len(collections)} collections...",
                total=len(collections)
            )

            tasks = []
            for collection in collections:
                task_coro = search_single_collection(collection)
                tasks.append(task_coro)

            # Execute searches concurrently
            all_results = []
            for completed_task in asyncio.as_completed(tasks):
                results = await completed_task
                all_results.extend(results)
                progress.advance(task, 1)

        # Sort by relevance score
        all_results.sort(key=lambda x: x.score, reverse=True)

        return all_results

    def display_results(
        self,
        results: List[IconResult],
        search_term: str,
        show_details: bool = False
    ):
        """Display search results in a unified table."""

        if not results:
            self.console.print("\n[yellow]No icons found.[/yellow]")
            self._show_suggestions(search_term)
            return

        # Limit to top 30 results for display
        display_results = results[:30]

        self.console.print(f"\n[bold cyan]Found {len(results)} icons matching '[green]{search_term}[/green]'[/bold cyan]")
        if len(results) > 30:
            self.console.print(f"[dim]Showing top 30 results[/dim]")
        self.console.print()

        # Create unified table with all results
        table = Table(
            title="Icon Search Results",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("Rank", justify="right", style="dim", width=4)
        table.add_column("Collection", style="blue", width=15)
        table.add_column("Icon Name", style="cyan", min_width=25)
        table.add_column("Score", justify="right", style="yellow", width=6)

        if show_details:
            table.add_column("Dimensions", justify="center", style="blue", width=12)

        # Add all results to single table
        for idx, icon in enumerate(display_results, 1):
            row = [
                str(idx),
                icon.collection,
                icon.name,
                f"{icon.score:.1f}"
            ]

            if show_details:
                if icon.width and icon.height:
                    row.append(f"{icon.width}x{icon.height}")
                else:
                    row.append("N/A")

            table.add_row(*row)

        self.console.print(table)
        self.console.print()

    def _show_suggestions(self, search_term: str):
        """Show helpful suggestions when no results are found."""
        suggestions_panel = Panel(
            "[yellow]Suggestions:[/yellow]\n"
            "• Try a shorter or more generic term\n"
            "• Check spelling\n"
            "• Try searching for the company/brand name instead\n"
            "• Some applications may not have dedicated icons",
            title="No Results Found",
            border_style="yellow"
        )
        self.console.print(suggestions_panel)

    def show_recommendations(self, search_term: str, results: List[IconResult]):
        """Show usage recommendations for Helm charts."""
        if not results:
            return

        best_result = results[0]

        recommendations = f"""[green]For Helm Chart values.yaml:[/green]
  Use the full collection:name format:
    [cyan]icon: {best_result.name}[/cyan]  # Top match

[green]Icon Validation:[/green]
  Run '[cyan]./scripts/validate-icons.sh --online[/cyan]' to validate your choices

[green]Alternative Options:[/green]"""

        # Show top 53 alternatives
        for i, result in enumerate(results[1:4], 1):
            recommendations += f"\n    [cyan]icon: {result.name}[/cyan]  # Alternative {i}"

        recommendations_panel = Panel(
            recommendations,
            title="Usage Recommendations",
            border_style="green"
        )

        self.console.print(recommendations_panel)

    def export_to_markdown(self, results: List[IconResult], search_term: str, filename: str):
        """Export search results to a markdown file with icon previews."""
        if not results:
            self.console.print("[yellow]No results to export[/yellow]")
            return

        # Iconify CDN URL pattern for icon images
        # Format: https://api.iconify.design/{collection}/{icon}.svg

        markdown_content = f"""# Icon Search Results for "{search_term}"

Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}

Found **{len(results)}** icons matching your search.

| Rank | Icon Name | Preview |
|------|-----------|---------|
"""

        for idx, icon in enumerate(results, 1):
            # Create icon URL for Iconify API
            # Extract just the icon name without collection prefix
            clean_icon_name = icon.name.split(':')[-1] if ':' in icon.name else icon.name
            icon_url = f"https://api.iconify.design/{icon.collection}/{clean_icon_name}.svg"

            # Create markdown image with size limit and fallback
            icon_preview = f'<img src="{icon_url}" alt="{icon.name}" width="32" height="32" style="vertical-align: middle;" onerror="this.style.display=\'none\'">'

            markdown_content += f"| {idx} | {icon.name} | {icon_preview} |\n"

        # Add usage instructions at the end
        markdown_content += f"""

## Usage Instructions

To use any of these icons in your Helm charts, add the icon name to your `values.yaml`:

```yaml
icon: {results[0].name}  # Recommended (top match)
```

### Alternative Options:
"""

        for i, result in enumerate(results[1:6], 1):
            markdown_content += f"- `{result.name}` (Alternative {i})\n"

        markdown_content += """

### Icon Validation

After updating your values.yaml, run the validation script:
```bash
./scripts/validate-icons.sh --online
```

### Icon Preview URLs

All icons are served via the Iconify API:
- Base URL: `https://api.iconify.design/{collection}/{icon}.svg`
- You can also use PNG format by changing `.svg` to `.png`
- Add size parameters: `?width=64&height=64`

"""

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            self.console.print(f"[green]Markdown results exported to {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error exporting markdown: {e}[/red]")

    async def get_detailed_info(self, api: IconifyAPI, results: List[IconResult], limit: int = 3):
        """Fetch detailed information for top results."""
        if not results:
            return

        self.console.print("[bold cyan]Fetching detailed information...[/bold cyan]")

        for result in results[:limit]:
            details = await api.get_icon_details(result.collection, result.name)
            if details:
                result.width = details.get('width')
                result.height = details.get('height')


def create_cli() -> argparse.ArgumentParser:
    """Create command line interface."""
    parser = argparse.ArgumentParser(
        description="Search for icons using the Iconify API with enhanced Python features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s plex
  %(prog)s "visual studio code" --verbose
  %(prog)s jellyfin --max-results 20 --details
  %(prog)s unifi --timeout 15
  %(prog)s docker --export results.json
  %(prog)s plex --export-md plex-icons.md
  %(prog)s jellyfin --details --export-md jellyfin-icons.md
        """
    )

    parser.add_argument(
        "search_term",
        help="The application name to search for icons"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=IconSearchConfig.DEFAULT_TIMEOUT,
        help=f"API request timeout in seconds (default: {IconSearchConfig.DEFAULT_TIMEOUT})"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=IconSearchConfig.DEFAULT_MAX_RESULTS,
        help=f"Maximum results per collection (default: {IconSearchConfig.DEFAULT_MAX_RESULTS})"
    )

    parser.add_argument(
        "--details",
        action="store_true",
        help="Fetch detailed information about top results (dimensions, etc.)"
    )

    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export results to JSON file"
    )

    parser.add_argument(
        "--export-md",
        type=str,
        metavar="FILE",
        help="Export results to Markdown file with icon previews"
    )

    parser.add_argument(
        "--collections",
        nargs="+",
        help="Specify custom collections to search (overrides defaults)"
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=10.0,
        help="Minimum relevance score to display (default: 10.0)"
    )

    return parser


async def main():
    """Main async function."""
    parser = create_cli()
    args = parser.parse_args()

    console = Console()
    searcher = IconSearcher(console, args.verbose)

    # Print header
    console.print(Panel(
        "[bold magenta]Iconify Icon Search Tool - Python Edition[/bold magenta]\n"
        "[dim]Enhanced with async operations, rich formatting, and intelligent scoring[/dim]",
        style="bold blue"
    ))

    try:
        async with IconifyAPI(args.timeout) as api:

            # Determine collections to search
            if args.collections:
                collections_to_search = args.collections
                console.print(f"[cyan]Using custom collections: {', '.join(collections_to_search)}[/cyan]\n")
            else:
                console.print("[cyan]Fetching all available collections...[/cyan]")
                all_collections = await api.get_collections()

                # Sort by priority, then alphabetically
                sorted_collections = sorted(
                    all_collections.keys(),
                    key=lambda x: (-all_collections[x].priority, x)
                )
                collections_to_search = sorted_collections
                console.print(f"[green]Found {len(collections_to_search)} collections[/green]\n")

            # Search for icons
            results = await searcher.search_collections(
                api,
                args.search_term,
                collections_to_search,
                args.max_results
            )

            # Filter by minimum score
            filtered_results = [r for r in results if r.score >= args.min_score]

            # Get detailed information if requested
            if args.details and filtered_results:
                await searcher.get_detailed_info(api, filtered_results)

            # Display results
            searcher.display_results(filtered_results, args.search_term, args.details)

            # Show recommendations
            if filtered_results:
                searcher.show_recommendations(args.search_term, filtered_results)

            # Export results if requested
            if args.export and filtered_results:
                export_data = {
                    'search_term': args.search_term,
                    'timestamp': time.time(),
                    'results': [
                        {
                            'name': r.name,
                            'collection': r.collection,
                            'full_name': r.full_name,
                            'score': r.score,
                            'width': r.width,
                            'height': r.height
                        }
                        for r in filtered_results
                    ]
                }

                with open(args.export, 'w') as f:
                    json.dump(export_data, f, indent=2)

                console.print(f"\n[green]Results exported to {args.export}[/green]")

            # Export markdown results if requested
            if args.export_md and filtered_results:
                searcher.export_to_markdown(filtered_results, args.search_term, args.export_md)

            # Exit with appropriate code
            sys.exit(0 if filtered_results else 1)

    except KeyboardInterrupt:
        console.print("\n[red]Search cancelled by user[/red]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    # Handle missing dependencies gracefully
    try:
        asyncio.run(main())
    except ImportError as e:
        print(f"Missing required dependencies: {e}")
        print("Install with: pip install aiohttp click rich")
        sys.exit(1)
