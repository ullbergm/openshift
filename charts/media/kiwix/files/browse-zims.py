#!/usr/bin/env python3
"""
Kiwix ZIM Browser (Textual TUI)

Interactive tool to browse the Kiwix library catalog, see which books are
already configured, and build a selection list to copy into values.yaml.

Usage:
    python3 browse-zims.py [--books book1,book2,...] [--values path/to/values.yaml]

    --books <list>   Comma-separated list of already-configured book names.
                     Falls back to the ZIM_BOOKS env var, then auto-reads
                     zimUpdater.books from ../values.yaml.
    --values <path>  Explicit path to a values.yaml file to read books from.

Key bindings:
    Space / Enter   Toggle selection on highlighted book
    i               Show full metadata for highlighted book
    c               Open category browser
    l               Edit language filter
    a               Select all books in current filtered view
    n               Deselect all books in current filtered view
    /               Focus the search box
    Ctrl+L          Reset all filters to defaults
    Ctrl+D          Show final YAML output
    q               Quit
"""

import os
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

try:
    from textual import on, work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, ScrollableContainer, Vertical
    from textual.events import Key
    from textual.screen import ModalScreen
    from textual.widgets import Button, DataTable, Footer, Header, Input, RichLog, Static
except ImportError:
    print("This script requires the 'textual' package.")
    print("Install it with:  pip install textual")
    sys.exit(1)

# ── Constants ─────────────────────────────────────────────────────────────────

LIBRARY_URL = "https://download.kiwix.org/library/library_zim.xml"
DEFAULT_LANGS: set[str] = {"eng", "swe", "mul"}

CATEGORIES: list[tuple[str, list[str]]] = [
    ("Wikipedia",           ["wikipedia"]),
    ("Wiktionary",          ["wiktionary"]),
    ("Wikivoyage",          ["wikivoyage"]),
    ("Wikisource",          ["wikisource"]),
    ("Wikibooks",           ["wikibooks"]),
    ("Wikinews",            ["wikinews"]),
    ("Wikiquote",           ["wikiquote"]),
    ("Wikiversity",         ["wikiversity"]),
    ("Other Wikimedia",     ["wikispecies", "wikifunctions", "wikimedia"]),
    ("Stack Exchange",       ["stackoverflow", "stackexchange"]),
    ("DevDocs",             ["devdocs"]),
    ("Programming & Tech",  ["freecodecamp", "ubuntuusers", "linux"]),
    ("Education",           ["libretexts", "phet", "khan", "openstax", "mathoverflow"]),
    ("Books & Literature",  ["gutenberg", "zim-books", "project-gutenberg"]),
    ("Medicine & Health",   ["medlineplus", "nhs.uk", "wwwnc.cdc.gov",
                              "quickguidesformedicine", "fas-military-medicine",
                              "medicalguidelines"]),
    ("Maps",                ["maps", "openstreetmap"]),
    ("Cooking",             ["foss.cooking", "based.cooking", "cooking"]),
    ("How-To & Repair",     ["ifixit", "instructables"]),
    ("Survival & Prepping", ["canadian_prepper", "canadian_prep", "urban-prepper",
                              "survivors", "survivorlibrary", "bushcraft"]),
    ("Talks & Media",       ["ted", "youtube"]),
    ("Science & Nature",    ["arxiv", "pubmed", "ncbi", "nature"]),
]
_CAT_ORDER = [c for c, _ in CATEGORIES] + ["Other"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def category_of(name: str) -> str:
    lower = name.lower()
    for cat_name, prefixes in CATEGORIES:
        for prefix in prefixes:
            # Matches: prefix alone, or as a leading component (prefix_ / prefix. / prefix-)
            # Also matches subdomain-style names: math.stackexchange_en → .stackexchange_
            if (lower == prefix
                    or lower.startswith(prefix + "_")
                    or lower.startswith(prefix + ".")
                    or lower.startswith(prefix + "-")
                    or f".{prefix}_" in lower
                    or f".{prefix}." in lower
                    or f".{prefix}-" in lower
                    or lower.endswith(f".{prefix}")):
                return cat_name
    return "Other"


def format_size(size_kb: int) -> str:
    if size_kb <= 0:
        return "?"
    n = float(size_kb * 1024)
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"


def project_of(name: str) -> str:
    return name.split("_")[0] if "_" in name else name


def _entry_langs(entry: dict) -> set[str]:
    """Return the set of language codes for an entry (field may be comma-separated)."""
    return {l.strip() for l in entry["language"].split(",") if l.strip()}


def apply_filters(entries, lang_filter, cat_filter, project_filter, search_filter):
    result = entries
    if lang_filter:
        result = [e for e in result if _entry_langs(e) & lang_filter]
    if cat_filter:
        result = [e for e in result if category_of(e["name"]) == cat_filter]
    if project_filter:
        result = [e for e in result if project_of(e["name"]) == project_filter]
    if search_filter:
        sf = search_filter.lower()
        result = [e for e in result
                  if sf in e["name"].lower() or sf in e["title"].lower()]
    return result


def fetch_catalog() -> dict[str, dict]:
    """Stream-parse library_zim.xml; keep the most-recent entry per book name."""
    catalog: dict[str, dict] = {}
    req = urllib.request.Request(LIBRARY_URL, headers={"User-Agent": "kiwix-zim-browser/1.0"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
        for event, elem in ET.iterparse(resp, events=["end"]):
            if elem.tag != "book":
                elem.clear()
                continue
            name = elem.get("name", "").strip()
            if not name:
                elem.clear()
                continue
            date = elem.get("date", "")
            existing = catalog.get(name)
            if existing and date <= existing["date"]:
                elem.clear()
                continue
            size_kb = 0
            raw_size = elem.get("size", "") or ""
            if raw_size.isdigit():
                size_kb = int(raw_size)
            catalog[name] = {
                "name":        name,
                "title":       elem.get("title", name).strip(),
                "date":        date,
                "url":         elem.get("url", ""),
                "language":    elem.get("language", ""),
                "size_kb":     size_kb,
                "description": (elem.get("description", "") or "").strip(),
                "articles":    elem.get("articleCount", ""),
            }
            elem.clear()
    return catalog


# ── Modal: Book Info ──────────────────────────────────────────────────────────

class BookInfoScreen(ModalScreen):
    BINDINGS = [("escape,q,i", "dismiss", "Close")]

    def __init__(self, entry: dict, is_selected: bool) -> None:
        super().__init__()
        self.entry = entry
        self.is_selected = is_selected

    def compose(self) -> ComposeResult:
        e = self.entry
        size_str = format_size(e["size_kb"]) if e["size_kb"] else "unknown"
        status = ("[bold green]● SELECTED[/bold green]"
                  if self.is_selected else "[dim]○ not selected[/dim]")
        desc = e["description"] or "[dim]—[/dim]"
        with Vertical(id="info-dialog"):
            yield Static("[bold cyan]Book Info[/bold cyan]", id="modal-title")
            yield Static(f"[bold]Name:[/bold]        {e['name']}")
            yield Static(f"[bold]Title:[/bold]       {e['title']}")
            yield Static(f"[bold]Category:[/bold]    {category_of(e['name'])}")
            yield Static(f"[bold]Language:[/bold]    {e['language']}")
            yield Static(f"[bold]Date:[/bold]        {e['date']}")
            yield Static(f"[bold]Size:[/bold]        {size_str}")
            if e["articles"]:
                yield Static(f"[bold]Articles:[/bold]   {e['articles']}")
            yield Static(f"[bold]Description:[/bold] {desc}")
            yield Static(f"[bold]Status:[/bold]      {status}")
            if e["url"]:
                yield Static(f"[bold]URL:[/bold]         {e['url']}")
            yield Button("Close  [dim]\\[Esc][/dim]", variant="primary", id="close-btn")

    @on(Button.Pressed, "#close-btn")
    def close(self) -> None:
        self.dismiss()


# ── Modal: Category Browser ───────────────────────────────────────────────────

class CategoryScreen(ModalScreen):
    BINDINGS = [("escape,q", "cancel", "Cancel")]

    def __init__(self, entries: list[dict], selected: set[str]) -> None:
        super().__init__()
        self._entries = entries
        self._selected = selected
        self._cats: list[str] = []

    def compose(self) -> ComposeResult:
        cat_buckets: dict[str, list] = defaultdict(list)
        for e in self._entries:
            cat_buckets[category_of(e["name"])].append(e)

        with Vertical(id="cat-dialog"):
            yield Static("[bold cyan]Category Browser[/bold cyan]", id="modal-title")
            table = DataTable(id="cat-table", cursor_type="row", zebra_stripes=True)
            table.add_columns("#", "Category", "Books", "Selected", "Size")
            for cat_name in _CAT_ORDER:
                books = cat_buckets.get(cat_name, [])
                if not books:
                    continue
                self._cats.append(cat_name)
                sel = sum(1 for e in books if e["name"] in self._selected)
                size_kb = sum(e["size_kb"] for e in books)
                table.add_row(
                    str(len(self._cats)), cat_name, str(len(books)),
                    f"{sel}/{len(books)}", format_size(size_kb),
                    key=cat_name,
                )
            yield table
            with Horizontal(id="modal-buttons"):
                yield Button("Filter  [dim]\\[Enter][/dim]", variant="primary", id="select-btn")
                yield Button("Clear Filter", variant="warning", id="clear-btn")
                yield Button("Cancel  [dim]\\[Esc][/dim]", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#cat-table", DataTable).focus()

    @on(DataTable.RowSelected, "#cat-table")
    def row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        if 0 <= idx < len(self._cats):
            self.dismiss(self._cats[idx])

    @on(Button.Pressed, "#select-btn")
    def select_btn(self) -> None:
        table = self.query_one("#cat-table", DataTable)
        idx = table.cursor_row
        if 0 <= idx < len(self._cats):
            self.dismiss(self._cats[idx])

    @on(Button.Pressed, "#clear-btn")
    def clear_btn(self) -> None:
        self.dismiss("")

    @on(Button.Pressed, "#cancel-btn")
    def cancel_btn(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Modal: Language Filter ────────────────────────────────────────────────────

class LangFilterScreen(ModalScreen):
    BINDINGS = [("escape,q", "cancel", "Cancel")]

    def __init__(self, current_langs: set[str], all_entries: list[dict]) -> None:
        super().__init__()
        self._current_langs = current_langs
        self._all_entries = all_entries

    def compose(self) -> ComposeResult:
        lang_counts: Counter = Counter()
        for e in self._all_entries:
            for lang in _entry_langs(e):
                lang_counts[lang] += 1
        current_str = " ".join(sorted(self._current_langs))
        with Vertical(id="lang-dialog"):
            yield Static("[bold cyan]Language Filter[/bold cyan]", id="modal-title")
            yield Static(
                f"Current: [cyan]{', '.join(sorted(self._current_langs)) or 'all languages'}[/cyan]"
            )
            table = DataTable(id="lang-table", cursor_type="row", zebra_stripes=True)
            table.add_columns("", "Code", "Books in catalog")
            # Show all languages; pin currently-active ones to the top
            all_langs = lang_counts.most_common()
            active = [(l, c) for l, c in all_langs if l in self._current_langs]
            rest   = [(l, c) for l, c in all_langs if l not in self._current_langs]
            for lang, count in active + rest:
                marker = "[green]✓[/green]" if lang in self._current_langs else " "
                table.add_row(marker, lang, str(count), key=lang)
            yield table
            yield Static("Enter codes (space/comma-separated), or blank for all languages:")
            yield Input(value=current_str, placeholder="e.g. eng swe mul", id="lang-input")
            with Horizontal(id="modal-buttons"):
                yield Button("Apply  [dim]\\[Enter][/dim]", variant="primary", id="apply-btn")
                yield Button("All Languages", variant="warning", id="clear-btn")
                yield Button("Cancel  [dim]\\[Esc][/dim]", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#lang-input", Input).focus()

    def _apply(self, value: str) -> None:
        raw = re.split(r"[\s,]+", value.strip())
        self.dismiss({lg for lg in raw if lg})

    @on(Button.Pressed, "#apply-btn")
    def apply_btn(self) -> None:
        self._apply(self.query_one("#lang-input", Input).value)

    @on(Button.Pressed, "#clear-btn")
    def clear_btn(self) -> None:
        self.dismiss(set())

    @on(Button.Pressed, "#cancel-btn")
    def cancel_btn(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted, "#lang-input")
    def input_submitted(self, event: Input.Submitted) -> None:
        self._apply(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Modal: Final Output ───────────────────────────────────────────────────────

class FinalOutputScreen(ModalScreen):
    BINDINGS = [("escape,q", "dismiss", "Close")]

    def __init__(self, selected: set[str], catalog: dict[str, dict]) -> None:
        super().__init__()
        self._selected = selected
        self._catalog = catalog

    def compose(self) -> ComposeResult:
        total_kb = sum(
            self._catalog[n]["size_kb"] for n in self._selected if n in self._catalog
        )
        with Vertical(id="output-dialog"):
            yield Static(
                f"[bold cyan]Final Selection[/bold cyan]  "
                f"({len(self._selected)} books  ~{format_size(total_kb)})",
                id="modal-title",
            )
            yield RichLog(id="output-log", highlight=False, markup=True, wrap=False)
            with Horizontal(id="modal-buttons"):
                yield Button("Exit & Print to stdout", variant="error", id="exit-btn")
                yield Button("Close  [dim]\\[Esc][/dim]", variant="primary", id="close-btn")

    def on_mount(self) -> None:
        log = self.query_one("#output-log", RichLog)
        by_cat: dict[str, list] = defaultdict(list)
        for name in sorted(self._selected):
            by_cat[category_of(name)].append((name, self._catalog.get(name)))

        log.write("[bold]── YAML (paste into zimUpdater.books in values.yaml) ──[/bold]")
        log.write("  books:")
        for cat_name in _CAT_ORDER:
            rows = by_cat.get(cat_name, [])
            if not rows:
                continue
            log.write(f"    [dim]# {cat_name}[/dim]")
            for name, entry in rows:
                size_str = format_size(entry["size_kb"]).strip() if entry else "?"
                log.write(f"    - {name:<44} [dim]# {size_str}[/dim]")
            log.write("")
        log.write("[bold]── Environment variable ──[/bold]")
        log.write(f"  ZIM_BOOKS={','.join(sorted(self._selected))}")

    @on(Button.Pressed, "#close-btn")
    def close_btn(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#exit-btn")
    def exit_btn(self) -> None:
        self.app.exit(result=True)


# ── Main App ──────────────────────────────────────────────────────────────────

_APP_CSS = """
Screen { background: $background; }

#main-container { height: 1fr; }

#left-panel { width: 3fr; }

#right-panel {
    width: 28;
    border-left: solid $panel-darken-2;
    background: $surface;
}

#filter-bar {
    height: 3;
    padding: 0 1;
    background: $panel;
    align: left middle;
}
.filter-label { width: auto; padding: 0 1; color: $text-muted; }
#search-input  { width: 2fr; }
#project-input { width: 1fr; }

#status-bar {
    height: 1;
    padding: 0 1;
    background: $panel-darken-1;
    color: $text-muted;
}

#book-table { height: 1fr; }

#selected-header {
    height: 3;
    content-align: center middle;
    background: $panel;
    color: $accent;
    text-style: bold;
}
#selected-summary {
    height: 1;
    padding: 0 1;
    background: $panel-darken-1;
    color: $text-muted;
}
#selected-scroll { height: 1fr; }
#selected-list   { padding: 1; }

/* ── Modals ── */

BookInfoScreen, CategoryScreen, LangFilterScreen, FinalOutputScreen {
    align: center middle;
}

#modal-title {
    text-align: center;
    padding-bottom: 1;
    text-style: bold;
}

#info-dialog {
    background: $surface;
    border: thick $primary;
    padding: 1 2;
    width: 72;
    height: auto;
    max-height: 36;
}

#cat-dialog {
    background: $surface;
    border: thick $primary;
    padding: 1 2;
    width: 82;
    height: auto;
    max-height: 40;
}
#cat-table { height: 20; }

#lang-dialog {
    background: $surface;
    border: thick $primary;
    padding: 1 2;
    width: 62;
    height: auto;
    max-height: 38;
}
#lang-table { height: 14; }

#output-dialog {
    background: $surface;
    border: thick $accent;
    padding: 1 2;
    width: 96;
    height: 42;
}
#output-log {
    height: 1fr;
    border: solid $panel;
}

#modal-buttons {
    height: 3;
    padding-top: 1;
    align: right middle;
}
Button { margin: 0 1; }
"""


class KiwixBrowser(App):
    """Kiwix ZIM catalog browser."""

    CSS = _APP_CSS
    TITLE = "Kiwix ZIM Browser"
    SUB_TITLE = "Browse and select ZIM books"

    BINDINGS = [
        Binding("q",       "quit",             "Quit",           show=True),
        Binding("ctrl+d",  "done",             "Export",         show=True),
        Binding("i",       "show_info",        "Info",           show=True),
        Binding("c",       "show_categories",  "Categories",     show=True),
        Binding("l",       "show_lang_filter", "Language",       show=True),
        Binding("a",       "select_all",       "Select All",     show=False),
        Binding("n",       "select_none",      "Deselect All",   show=False),
        Binding("ctrl+l",  "clear_filters",    "Reset Filters",  show=True),
        Binding("/",       "focus_search",     "Search",         show=True),
    ]

    def __init__(self, initial_selected: set[str]) -> None:
        super().__init__()
        self.catalog: dict[str, dict] = {}
        self.all_entries: list[dict] = []
        self.filtered: list[dict] = []
        self._row_map: list[Optional[dict]] = []  # None = category header row
        self.selected: set[str] = set(initial_selected)
        self.lang_filter: set[str] = DEFAULT_LANGS.copy()
        self.cat_filter: str = ""
        self.project_filter: str = ""
        self.search_filter: str = ""
        self._loading = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                with Horizontal(id="filter-bar"):
                    yield Static("Search:", classes="filter-label")
                    yield Input(placeholder="name or title…", id="search-input")
                    yield Static("Project:", classes="filter-label")
                    yield Input(placeholder="prefix…", id="project-input")
                yield Static(
                    "[dim]Fetching catalog from kiwix.org…[/dim]", id="status-bar"
                )
                yield DataTable(id="book-table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="right-panel"):
                yield Static("Selected Books", id="selected-header")
                yield Static("0 books  ~0B", id="selected-summary")
                with ScrollableContainer(id="selected-scroll"):
                    yield Static("[dim](none)[/dim]", id="selected-list")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#book-table", DataTable)
        table.add_columns("", "#", "Name", "Lang", "Date", "Size")
        table.focus()
        self._fetch_catalog()

    # ── Catalog loading ────────────────────────────────────────────────────

    @work(thread=True)
    def _fetch_catalog(self) -> None:
        try:
            catalog = fetch_catalog()
            self.call_from_thread(self._on_catalog_loaded, catalog)
        except Exception as exc:
            self.call_from_thread(self._on_catalog_error, f"{type(exc).__name__}: {exc}")

    def _on_catalog_loaded(self, catalog: dict) -> None:
        self.catalog = catalog
        self.all_entries = sorted(
            catalog.values(), key=lambda e: (category_of(e["name"]), e["name"])
        )
        self._loading = False
        self._refresh_table()
        not_found = sorted(b for b in self.selected if b not in catalog)
        if not_found:
            self.notify(
                f"Not in catalog: {', '.join(not_found)}",
                title="Warning", severity="warning", timeout=8,
            )
        self.notify(
            f"Loaded {len(catalog)} books", title="Catalog ready", timeout=3,
        )

    def _on_catalog_error(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(f"[bold red]Error: {msg}[/bold red]")
        self.notify(msg, title="Catalog fetch failed", severity="error")

    # ── Table refresh ──────────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        self.filtered = apply_filters(
            self.all_entries,
            self.lang_filter, self.cat_filter,
            self.project_filter, self.search_filter,
        )
        table = self.query_one("#book-table", DataTable)
        old_cursor = table.cursor_row
        table.clear()
        self._row_map = []

        prev_cat = None
        row_num = 0
        for entry in self.filtered:
            name = entry["name"]
            cat = category_of(name)
            if cat != prev_cat:
                table.add_row(
                    "", "", f"[bold cyan]▶  {cat}[/bold cyan]",
                    "", "", "", key=f"__cat__{cat}",
                )
                self._row_map.append(None)
                prev_cat = cat
            row_num += 1
            sel = name in self.selected
            table.add_row(
                "[green]●[/green]" if sel else " ",
                str(row_num),
                f"[green]{name}[/green]" if sel else name,
                ",".join(sorted(_entry_langs(entry)))[:11],
                entry["date"],
                format_size(entry["size_kb"]),
                key=name,
            )
            self._row_map.append(entry)

        if table.row_count > 0:
            table.move_cursor(row=min(old_cursor, table.row_count - 1))

        self._refresh_status()
        self._refresh_selected_panel()

    def _refresh_status(self) -> None:
        n_shown = len(self.filtered)
        n_sel_view = sum(1 for e in self.filtered if e["name"] in self.selected)
        n_sel_total = len(self.selected)
        filters = []
        if self.lang_filter:
            filters.append(f"lang:[cyan]{','.join(sorted(self.lang_filter))}[/cyan]")
        if self.cat_filter:
            filters.append(f"cat:[cyan]{self.cat_filter}[/cyan]")
        if self.project_filter:
            filters.append(f"proj:[cyan]{self.project_filter}[/cyan]")
        if self.search_filter:
            filters.append(f"search:[cyan]{self.search_filter!r}[/cyan]")
        filter_str = ("  │  " + "  │  ".join(filters)) if filters else ""
        self.query_one("#status-bar", Static).update(
            f"[bold]{n_shown}[/bold] shown  │  "
            f"[green]{n_sel_view}[/green] selected in view  │  "
            f"[yellow]{n_sel_total}[/yellow] total selected"
            + filter_str
        )

    def _refresh_selected_panel(self) -> None:
        if not self.selected:
            self.query_one("#selected-list", Static).update("[dim](none)[/dim]")
            self.query_one("#selected-summary", Static).update("0 books  ~0B")
            return

        by_cat: dict[str, list] = defaultdict(list)
        for name in sorted(self.selected):
            by_cat[category_of(name)].append(name)

        lines = []
        total_kb = 0
        for cat_name in _CAT_ORDER:
            names = by_cat.get(cat_name, [])
            if not names:
                continue
            lines.append(f"[bold cyan]{cat_name}[/bold cyan]")
            for name in names:
                entry = self.catalog.get(name)
                if entry:
                    total_kb += entry["size_kb"]
                    lines.append(
                        f"  [green]●[/green] {name}\n    [dim]{format_size(entry['size_kb'])}[/dim]"
                    )
                else:
                    lines.append(f"  [yellow]●[/yellow] {name}")

        self.query_one("#selected-list", Static).update("\n".join(lines))
        self.query_one("#selected-summary", Static).update(
            f"[bold]{len(self.selected)}[/bold] books  ~[cyan]{format_size(total_kb)}[/cyan]"
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_current_entry(self) -> Optional[dict]:
        table = self.query_one("#book-table", DataTable)
        if table.row_count == 0:
            return None
        idx = table.cursor_row
        if 0 <= idx < len(self._row_map):
            return self._row_map[idx]
        return None

    def _toggle_entry(self, entry: dict) -> None:
        name = entry["name"]
        if name in self.selected:
            self.selected.discard(name)
            self.notify(f"Deselected: {name}", severity="information", timeout=2)
        else:
            self.selected.add(name)
            self.notify(f"Selected: {name}", severity="information", timeout=2)
        self._refresh_table()

    # ── Key / event handlers ───────────────────────────────────────────────

    def on_key(self, event: Key) -> None:
        if event.key == "space" and not isinstance(self.focused, Input):
            entry = self._get_current_entry()
            if entry:
                self._toggle_entry(entry)
            event.prevent_default()

    @on(DataTable.RowSelected, "#book-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        entry = self._get_current_entry()
        if entry:
            self._toggle_entry(entry)

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.search_filter = event.value
        if not self._loading:
            self._refresh_table()

    @on(Input.Changed, "#project-input")
    def on_project_changed(self, event: Input.Changed) -> None:
        self.project_filter = event.value.strip().lower()
        if not self._loading:
            self._refresh_table()

    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        self.query_one("#book-table", DataTable).focus()

    # ── Actions ────────────────────────────────────────────────────────────

    def action_done(self) -> None:
        self.push_screen(FinalOutputScreen(self.selected, self.catalog))

    def action_show_info(self) -> None:
        entry = self._get_current_entry()
        if entry is None:
            self.notify("No book highlighted", severity="warning")
            return
        self.push_screen(BookInfoScreen(entry, entry["name"] in self.selected))

    def action_show_categories(self) -> None:
        def handle(result) -> None:
            if result is None:
                return
            self.cat_filter = result
            if not self._loading:
                self._refresh_table()
        self.push_screen(CategoryScreen(self.filtered, self.selected), handle)

    def action_show_lang_filter(self) -> None:
        def handle(result) -> None:
            if result is None:
                return
            self.lang_filter = result
            if not self._loading:
                self._refresh_table()
        self.push_screen(LangFilterScreen(self.lang_filter, self.all_entries), handle)

    def action_select_all(self) -> None:
        added = sum(1 for e in self.filtered if e["name"] not in self.selected)
        for e in self.filtered:
            self.selected.add(e["name"])
        self.notify(f"Selected {added} books ({len(self.selected)} total)")
        self._refresh_table()

    def action_select_none(self) -> None:
        removed = sum(1 for e in self.filtered if e["name"] in self.selected)
        for e in self.filtered:
            self.selected.discard(e["name"])
        self.notify(
            f"Deselected {removed} books ({len(self.selected)} total)",
            severity="warning",
        )
        self._refresh_table()

    def action_clear_filters(self) -> None:
        self.lang_filter = DEFAULT_LANGS.copy()
        self.cat_filter = ""
        self.project_filter = ""
        self.search_filter = ""
        self.query_one("#search-input", Input).value = ""
        self.query_one("#project-input", Input).value = ""
        if not self._loading:
            self._refresh_table()
        self.notify("Filters reset to defaults")

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()


# ── values.yaml reading & CLI ─────────────────────────────────────────────────

_VALUES_CANDIDATES = [
    Path(__file__).parent.parent / "values.yaml",
    Path("values.yaml"),
]


def read_values_yaml_books(values_path: Path) -> list[str]:
    if not values_path.exists():
        return []
    books: list[str] = []
    in_zim_updater = False
    in_books = False
    books_indent = -1
    with open(values_path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.rstrip()
            if re.match(r"^zimUpdater\s*:", stripped):
                in_zim_updater = True
                in_books = False
                continue
            if in_zim_updater:
                if stripped and not stripped[0].isspace() and not stripped.startswith("#"):
                    in_zim_updater = False
                    in_books = False
                    continue
                m_books = re.match(r"^(\s+)books\s*:", stripped)
                if m_books:
                    in_books = True
                    books_indent = len(m_books.group(1))
                    continue
                if in_books:
                    if stripped and not stripped.startswith("#"):
                        indent = len(stripped) - len(stripped.lstrip())
                        if indent <= books_indent and not re.match(r"\s*-", stripped):
                            in_books = False
                            continue
                    m_item = re.match(r"^\s+-\s+(\S+)", stripped)
                    if m_item:
                        raw_name = m_item.group(1).split("#")[0].strip()
                        if raw_name:
                            books.append(raw_name)
    return books


def parse_args():
    books_arg = values_path_arg = ""
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--books", "-b") and i + 1 < len(args):
            books_arg = args[i + 1]; i += 2
        elif args[i].startswith("--books="):
            books_arg = args[i].split("=", 1)[1]; i += 1
        elif args[i] in ("--values", "-v") and i + 1 < len(args):
            values_path_arg = args[i + 1]; i += 2
        elif args[i].startswith("--values="):
            values_path_arg = args[i].split("=", 1)[1]; i += 1
        else:
            i += 1
    return books_arg, values_path_arg


def main() -> None:
    books_arg, values_path_arg = parse_args()

    if books_arg:
        selected: set[str] = {b.strip() for b in books_arg.split(",") if b.strip()}
    elif os.environ.get("ZIM_BOOKS"):
        selected = {b.strip() for b in os.environ["ZIM_BOOKS"].split(",") if b.strip()}
    else:
        candidates = [Path(values_path_arg)] if values_path_arg else _VALUES_CANDIDATES
        yaml_books: list[str] = []
        for candidate in candidates:
            yaml_books = read_values_yaml_books(candidate)
            if yaml_books:
                break
        selected = set(yaml_books)

    app = KiwixBrowser(initial_selected=selected)
    result = app.run()

    # "Exit & Print to stdout" button sets result=True
    if result is True and app.selected and app.catalog:
        by_cat: dict[str, list] = defaultdict(list)
        for name in sorted(app.selected):
            by_cat[category_of(name)].append((name, app.catalog.get(name)))
        total_kb = sum(
            app.catalog[n]["size_kb"] for n in app.selected if n in app.catalog
        )
        print()
        print("=" * 70)
        print(f"Final Selection: {len(app.selected)} books  ~{format_size(total_kb)}")
        print("=" * 70)
        print()
        print("  books:")
        for cat_name in _CAT_ORDER:
            rows = by_cat.get(cat_name, [])
            if not rows:
                continue
            print(f"    # {cat_name}")
            for name, entry in rows:
                size_str = format_size(entry["size_kb"]).strip() if entry else "?"
                print(f"    - {name:<44} # {size_str}")
            print()
        print("─" * 46)
        print(f"ZIM_BOOKS={','.join(sorted(app.selected))}")
        print()


if __name__ == "__main__":
    main()
