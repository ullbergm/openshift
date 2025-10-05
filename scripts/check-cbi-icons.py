#!/usr/bin/env python3
"""
Check which applications in the repository have CBI icons available.
"""

import asyncio
import json
from pathlib import Path
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


async def check_icon(session, app_name):
    """Check if a CBI icon exists for an application."""
    url = "https://api.iconify.design/search"
    params = {
        'query': app_name,
        'collection': 'cbi',
        'limit': 10
    }

    try:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                icons = data.get('icons', [])
                # Icons come back with the "cbi:" prefix already, so strip it
                icons = [icon.replace('cbi:', '') for icon in icons]
                # Check if we found an exact match or close match
                exact_matches = [icon for icon in icons if icon == app_name]
                if exact_matches:
                    return app_name
                # Check for close matches (icon name contains app name)
                close_matches = [icon for icon in icons if app_name in icon or icon in app_name]
                if close_matches:
                    return close_matches[0]
        return None
    except Exception:
        return None


async def main():
    console = Console()

    # Get all application names
    charts_path = Path('/workspaces/openshift/charts')
    apps = []

    for group_dir in charts_path.iterdir():
        if group_dir.is_dir():
            for app_dir in group_dir.iterdir():
                if app_dir.is_dir():
                    apps.append(app_dir.name)

    apps = sorted(set(apps))

    console.print(f"[cyan]Checking {len(apps)} applications for CBI icons...[/cyan]\n")

    # Check icons concurrently
    found = {}
    not_found = []

    async with aiohttp.ClientSession() as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking icons...", total=len(apps))

            for app in apps:
                icon_name = await check_icon(session, app)
                if icon_name:
                    found[app] = icon_name
                else:
                    not_found.append(app)
                progress.advance(task)

    # Display results
    console.print(f"\n[bold]📊 Summary[/bold]")
    console.print(f"Total applications: {len(apps)}")
    console.print(f"[green]✅ Found CBI icons: {len(found)}[/green]")
    console.print(f"[red]❌ Not found: {len(not_found)}[/red]")

    if found:
        console.print(f"\n[bold green]✅ Applications WITH CBI icons:[/bold green]")
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Application", style="cyan")
        table.add_column("Icon", style="green")

        for app, icon_name in sorted(found.items()):
            table.add_row(app, f"cbi:{icon_name}")

        console.print(table)

    if not_found:
        console.print(f"\n[bold red]❌ Applications WITHOUT CBI icons:[/bold red]")
        for app in not_found:
            console.print(f"  • {app}")


if __name__ == "__main__":
    asyncio.run(main())
