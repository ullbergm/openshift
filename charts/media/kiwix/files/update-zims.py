#!/usr/bin/env python3
"""
Kiwix ZIM Updater
Fetches the official Kiwix library catalog (library_zim.xml), finds the
latest version of each configured book by its "name" attribute (e.g.
wikipedia_en_all_mini), downloads any missing or updated ZIM files, and
removes outdated versions.

Books renamed upstream can be listed in ZIM_SUPERSEDED as "new=old" pairs
(old being the previous filename prefix); once the new book is on disk the
old-named files are dropped from the library and deleted.
"""
import os
import re
import ssl
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

LIBRARY_URL = "https://download.kiwix.org/library/library_zim.xml"
DATA_DIR = Path(os.environ.get("ZIM_DATA_DIR", "/data"))
ZIM_BOOKS = [b.strip() for b in os.environ.get("ZIM_BOOKS", "").split(",") if b.strip()]
# {new book name: old filename prefix} for books renamed in the catalog.
ZIM_SUPERSEDED = dict(
    pair.strip().split("=", 1)
    for pair in os.environ.get("ZIM_SUPERSEDED", "").split(",")
    if "=" in pair
)

METALINK_NS = "urn:ietf:params:xml:ns:metalink"

# Preferred flavour order when a book is published in several; lower wins.
# Books without a flavour only come in one variant and rank with maxi.
FLAVOUR_RANK = {"maxi": 0, "": 0, "nopic": 1, "mini": 2}


def fetch_latest_entries(book_names):
    """
    Stream-parse the Kiwix library_zim.xml catalog and return the entry
    of the preferred flavour (maxi, then nopic, then mini) for each
    requested book name, taking the newest date within that flavour.

    Book names use underscores and match the "name" XML attribute, e.g.:
      wikipedia_en_all_mini, wiktionary_en_all, ifixit_mul_all
    """
    wanted = set(book_names)
    # best[name] = {"url": ..., "date": ..., "title": ..., "rank": ...}
    best = {}

    print(f"Fetching Kiwix library catalog from {LIBRARY_URL} ...")
    try:
        req = urllib.request.Request(
            LIBRARY_URL, headers={"User-Agent": "kiwix-zim-updater/1.0"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            for event, elem in ET.iterparse(resp, events=["end"]):
                if elem.tag != "book":
                    continue
                name = elem.get("name", "")
                if name not in wanted:
                    elem.clear()
                    continue
                url = elem.get("url", "")
                date = elem.get("date", "")
                if not url:
                    elem.clear()
                    continue
                rank = FLAVOUR_RANK.get(elem.get("flavour", ""), len(FLAVOUR_RANK))
                current = best.get(name)
                if current is None or (rank, current["date"]) < (current["rank"], date):
                    best[name] = {
                        "url": url,
                        "date": date,
                        "title": elem.get("title", name),
                        "rank": rank,
                    }
                elem.clear()
    except Exception as e:
        print(f"ERROR: Failed to fetch library catalog: {e}")
        return {}

    return best


def resolve_meta4(meta4_url):
    """
    Fetch a MirrorBrain .meta4 Metalink 4 file and return the HTTP URL
    with the lowest priority number (highest preference).
    Falls back to stripping .meta4 if the file cannot be fetched/parsed.
    """
    try:
        req = urllib.request.Request(
            meta4_url, headers={"User-Agent": "kiwix-zim-updater/1.0"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            tree = ET.parse(resp)
    except Exception as e:
        print(f"  WARNING: could not fetch meta4 ({e}), falling back to direct URL")
        return meta4_url.removesuffix(".meta4")

    root = tree.getroot()
    candidates = []
    for file_elem in root.findall(f"{{{METALINK_NS}}}file"):
        for url_elem in file_elem.findall(f"{{{METALINK_NS}}}url"):
            href = (url_elem.text or "").strip()
            if not href.startswith("http"):
                continue
            priority = int(url_elem.get("priority", 999))
            candidates.append((priority, href))

    if not candidates:
        print("  WARNING: no HTTP URLs in meta4, falling back to direct URL")
        return meta4_url.removesuffix(".meta4")

    candidates.sort(key=lambda x: x[0])
    chosen = candidates[0][1]
    print(f"  Mirror: {chosen}")
    return chosen


def download_file(url, dest):
    """Download a large file in 4 MB chunks with periodic progress reports."""
    tmp = Path(str(dest) + ".part")
    print(f"  Downloading {dest.name} ...")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "kiwix-zim-updater/1.0"}
        )
        ctx = ssl.create_default_context()
        downloaded = 0
        last_report = 0
        with urllib.request.urlopen(req, timeout=3600, context=ctx) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total and downloaded - last_report >= 100 * 1024 * 1024:
                        pct = downloaded * 100 // total
                        mb = downloaded // (1024 * 1024)
                        total_mb = total // (1024 * 1024)
                        print(
                            f"  Progress: {pct}% ({mb} MB / {total_mb} MB)",
                            flush=True,
                        )
                        last_report = downloaded
        tmp.rename(dest)
        print(f"  Done: {dest.name} ({downloaded // (1024 * 1024)} MB)")
        return True
    except Exception as e:
        print(f"  ERROR: download failed: {e}")
        if tmp.exists():
            tmp.unlink()
        return False


def add_to_library(zim_path):
    """Register a ZIM file with the Kiwix library XML via kiwix-manage."""
    library_xml = DATA_DIR / "library.xml"
    cmd = ["kiwix-manage", str(library_xml), "add", str(zim_path)]
    print(f"  Updating library: kiwix-manage library.xml add {zim_path.name}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  WARNING: kiwix-manage failed: {result.stderr.strip()}")
        else:
            print("  Library updated successfully.")
    except FileNotFoundError:
        print("  WARNING: kiwix-manage not found; skipping library update")
    except Exception as e:
        print(f"  WARNING: kiwix-manage error: {e}")


def library_ids_for(zim_path):
    """Return the library.xml book IDs whose path points at the given ZIM file."""
    library_xml = DATA_DIR / "library.xml"
    try:
        root = ET.parse(library_xml).getroot()
    except Exception as e:
        print(f"  WARNING: could not read library.xml: {e}")
        return []
    return [
        b.get("id")
        for b in root.iter("book")
        if b.get("id") and Path(b.get("path", "")).name == zim_path.name
    ]


def remove_from_library(zim_path):
    """Remove a ZIM file entry from the Kiwix library XML via kiwix-manage."""
    library_xml = DATA_DIR / "library.xml"
    # kiwix-manage removes by ZIM ID, not by path.
    ids = library_ids_for(zim_path)
    if not ids:
        print(f"  No library entry for {zim_path.name}")
        return
    cmd = ["kiwix-manage", str(library_xml), "remove", *ids]
    print(f"  Updating library: kiwix-manage library.xml remove {zim_path.name}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  WARNING: kiwix-manage remove failed: {result.stderr.strip()}")
        else:
            print("  Library entry removed successfully.")
    except FileNotFoundError:
        print("  WARNING: kiwix-manage not found; skipping library cleanup")
    except Exception as e:
        print(f"  WARNING: kiwix-manage remove error: {e}")


def remove_superseded(book):
    """Drop files left behind under a book's pre-rename filename prefix."""
    old_prefix = ZIM_SUPERSEDED.get(book)
    if not old_prefix:
        return
    for old in sorted(DATA_DIR.glob(f"{old_prefix}_*.zim")):
        print(f"  Removing superseded file: {old.name}")
        remove_from_library(old)
        old.unlink(missing_ok=True)


def main():
    if not ZIM_BOOKS:
        print("No ZIM books configured. Set ZIM_BOOKS environment variable.")
        print("Example: ZIM_BOOKS=wikipedia_en_all_mini,wiktionary_en_all")
        sys.exit(0)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    catalog = fetch_latest_entries(ZIM_BOOKS)

    errors = []

    for book in ZIM_BOOKS:
        print(f"\n=== {book} ===")
        entry = catalog.get(book)
        if not entry:
            print(
                f"  Not found in catalog. Check the name against:\n"
                f"    {LIBRARY_URL}"
            )
            errors.append(book)
            continue

        # library_zim.xml urls are .zim.meta4 MirrorBrain metalink files.
        # Parse the meta4 to get the best mirror URL for the actual ZIM.
        meta4_url = entry["url"]
        print(f"  Resolving {meta4_url.split('/')[-1]} ...")
        download_url = resolve_meta4(meta4_url)
        filename = download_url.split("/")[-1].split("?")[0]
        dest = DATA_DIR / filename

        if dest.exists():
            print(f"  Already present: {filename} (catalog date: {entry['date']})")
            remove_superseded(book)
            continue

        # Find old versions; keep one previous file as rollback cache after update.
        # Match on "<book>[_<flavour>]_<YYYY-MM>.zim" so a book whose name is a
        # prefix of another (devdocs_en_c / devdocs_en_c_...) is left alone.
        version_re = re.compile(rf"{re.escape(book)}(_[a-z]+)?_\d{{4}}-\d{{2}}\.zim")
        old_versions = [
            f for f in DATA_DIR.glob(f"{book}_*.zim")
            if f != dest and version_re.fullmatch(f.name)
        ]

        if download_file(download_url, dest):
            add_to_library(dest)

            keep_previous = None
            removable_old_versions = []
            if old_versions:
                old_versions_sorted = sorted(old_versions, key=lambda p: p.stat().st_mtime, reverse=True)
                keep_previous = old_versions_sorted[0]
                removable_old_versions = old_versions_sorted[1:]

                # Keep one rollback file on disk, but ensure it is not served from library.xml.
                print(f"  Keeping one previous version on disk: {keep_previous.name}")
                remove_from_library(keep_previous)

            for old in removable_old_versions:
                remove_from_library(old)
                print(f"  Removing old version: {old.name}")
                old.unlink(missing_ok=True)

            remove_superseded(book)
        else:
            errors.append(book)

    if errors:
        print(f"\nErrors for: {errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
