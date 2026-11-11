#!/usr/bin/env python3
"""
T.REX ARMS Field Manual Vault -> ZIM builder

Mirrors https://www.trex-arms.com/field-manual-vault (public domain U.S.
military publications, as PDF and EPUB) and packs it into a ZIM file for
kiwix-serve. Safe to re-run: every stage is incremental.

  1. crawl     listing pages give every publication; each manual's page gives
               its full metadata (TOC, references, cited-by, editions, files).
               Metadata is kept verbatim as JSON under <work-dir>/meta/.
  2. download  PDFs, EPUBs and cover thumbnails into <work-dir>/files/, using
               conditional requests (ETag) so unchanged files are not fetched.
  3. build     a ZIM with a filterable index, one page per manual, the files,
               the raw metadata (data/catalog.json) and a full-text index fed
               from the EPUB text. Skipped when nothing changed.
  4. register  with kiwix-manage in <output-dir>/library.xml (when available).

Requires the "libzim" package (pip install libzim) for the build stage only.

Usage:
  build-trex-vault-zim.py --work-dir ./trex-vault --output-dir ./zims
  build-trex-vault-zim.py --limit 25          # small test build
Every option also reads an environment variable (see --help).
"""
import argparse
import datetime
import hashlib
import html
from http.client import HTTPException
import json
import os
import re
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SITE = "https://www.trex-arms.com"
VAULT = f"{SITE}/field-manual-vault"
ZIM_NAME = "trex-arms-field-manual-vault_en_all"
# Bump to force a rebuild when the generated pages change.
BUILD_VERSION = 1
DEFAULT_COLLECTIONS = ["current", "recent-archive", "lessons-learned", "historic"]
RESERVED_SLUGS = {"faq", "citations"}

LABELS = {
    "collection": {
        "current": "Current Doctrine",
        "recent-archive": "Recent Archive",
        "lessons-learned": "Lessons Learned",
        "historic": "Historic",
    },
    "branch": {
        "army": "Army",
        "usmc": "Marine Corps",
        "navy": "Navy",
        "joint": "Joint",
        "af": "Air Force",
    },
}


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
class Http:
    """urllib wrapper: identifying User-Agent, per-host pacing, retries."""

    def __init__(self, user_agent, delay):
        self.user_agent = user_agent
        self.delay = delay
        self._lock = threading.Lock()
        self._next = {}

    def _pace(self, url):
        host = urllib.parse.urlsplit(url).netloc
        with self._lock:
            now = time.monotonic()
            at = max(now, self._next.get(host, 0.0))
            self._next[host] = at + self.delay
        if at > now:
            time.sleep(at - now)

    def open(self, url, headers=None, timeout=120):
        """Return an open response; HTTPError for 304/404 is raised to the caller."""
        last = None
        for attempt in range(5):
            self._pace(url)
            req = urllib.request.Request(
                url, headers={"User-Agent": self.user_agent, **(headers or {})}
            )
            try:
                return urllib.request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as e:
                if e.code in (304, 404, 410):
                    raise
                if e.code == 403:
                    body = e.read(4096).decode("utf-8", "replace")
                    if "Just a moment" in body:
                        raise SystemExit(
                            f"❌ {url} answered with a bot challenge. The site lets "
                            "identified clients through; check --user-agent."
                        )
                    raise
                last = e
                wait = int(e.headers.get("Retry-After") or 0) or 5 * 2**attempt
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = e
                wait = 5 * 2**attempt
            log(f"  ⚠️ {url}: {last}; retrying in {wait}s")
            time.sleep(min(wait, 300))
        raise last

    def retry_read(self, url, fn):
        """Run fn(), which opens and reads url, again if the connection drops mid-body."""
        for attempt in range(4):
            try:
                return fn()
            except urllib.error.HTTPError:
                raise
            except (OSError, HTTPException) as e:
                if attempt == 3:
                    raise
                wait = 5 * 2**attempt
                log(f"  ⚠️ {url}: {e}; retrying in {wait}s")
                time.sleep(wait)

    def text(self, url):
        def read():
            with self.open(url) as resp:
                return resp.read().decode("utf-8", "replace")

        return self.retry_read(url, read)


# --------------------------------------------------------------------------
# The site embeds each page's data as a JavaScript literal (not JSON).
# --------------------------------------------------------------------------
class JsLiteral:
    """Parser for the plain-data subset of JavaScript object literals."""

    ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
    NUMBER = re.compile(r"-?(?:\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)")
    IDENT = re.compile(r"[A-Za-z_$][\w$]*")

    class Ref:
        def __init__(self, name):
            self.name = name

    def __init__(self, text, pos=0):
        self.s = text
        self.i = pos
        self.params = set()

    def error(self, what):
        raise ValueError(f"{what} at offset {self.i}: {self.s[self.i:self.i + 40]!r}")

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1

    def value(self):
        self.ws()
        s, c = self.s, self.s[self.i]
        if c == "{":
            return self.object()
        if c == "[":
            return self.array()
        if c in "\"'":
            return self.string()
        m = self.NUMBER.match(s, self.i)
        if m:
            self.i = m.end()
            n = m.group(0)
            return int(n) if re.fullmatch(r"-?\d+", n) else float(n)
        for word, val in (("null", None), ("true", True), ("false", False), ("void 0", None)):
            if s.startswith(word, self.i):
                self.i += len(word)
                return val
        if s.startswith("(function(", self.i):
            return self.wrapped()
        m = self.IDENT.match(s, self.i)
        if m and m.group(0) in self.params:
            self.i = m.end()
            return self.Ref(m.group(0))
        if s.startswith("new ", self.i):  # new Date(123) / new URL("...")
            self.i = s.index("(", self.i) + 1
            val = self.value()
            self.ws()
            if s[self.i] != ")":
                self.error("unsupported constructor")
            self.i += 1
            return val
        self.error("unsupported value")

    def expect(self, token):
        self.ws()
        if not self.s.startswith(token, self.i):
            self.error(f"expected {token!r}")
        self.i += len(token)

    def wrapped(self):
        """(function(a,b){return VALUE}(ARG,ARG)): repeated values hoisted into parameters."""
        self.expect("(function(")
        end = self.s.index(")", self.i)
        names = [n.strip() for n in self.s[self.i:end].split(",") if n.strip()]
        self.i = end + 1
        self.expect("{")
        self.expect("return ")
        outer, self.params = self.params, set(names)
        body = self.value()
        self.params = outer
        self.expect("}")
        self.expect("(")
        args = []
        while True:
            self.ws()
            if self.s[self.i] == ")":
                self.i += 1
                break
            args.append(self.value())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1
        self.expect(")")
        return self.resolve(body, dict(zip(names, args)))

    def resolve(self, node, env):
        if isinstance(node, self.Ref):
            return env.get(node.name)
        if isinstance(node, list):
            return [self.resolve(v, env) for v in node]
        if isinstance(node, dict):
            return {k: self.resolve(v, env) for k, v in node.items()}
        return node

    def string(self):
        s, quote = self.s, self.s[self.i]
        self.i += 1
        out = []
        while True:
            c = s[self.i]
            if c == quote:
                self.i += 1
                return "".join(out)
            if c != "\\":
                j = self.i
                while s[self.i] != quote and s[self.i] != "\\":
                    self.i += 1
                out.append(s[j:self.i])
                continue
            e = s[self.i + 1]
            if e == "u":
                code = int(s[self.i + 2:self.i + 6], 16)
                self.i += 6
                if 0xD800 <= code < 0xDC00 and s.startswith("\\u", self.i):
                    low = int(s[self.i + 2:self.i + 6], 16)
                    code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                    self.i += 6
                out.append(chr(code))
            elif e == "x":
                out.append(chr(int(s[self.i + 2:self.i + 4], 16)))
                self.i += 4
            else:
                out.append(self.ESCAPES.get(e, e))
                self.i += 2

    def array(self):
        self.i += 1
        out = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1

    def object(self):
        self.i += 1
        out = {}
        while True:
            self.ws()
            c = self.s[self.i]
            if c == "}":
                self.i += 1
                return out
            if c in "\"'":
                key = self.string()
            else:
                m = self.IDENT.match(self.s, self.i) or self.NUMBER.match(self.s, self.i)
                if not m:
                    self.error("bad object key")
                key = m.group(0)
                self.i = m.end()
            self.ws()
            if self.s[self.i] != ":":
                self.error("expected ':'")
            self.i += 1
            out[key] = self.value()
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1


def embedded(page, key):
    """Return `key` from the route data in a page's hydration script, or None."""
    start = page.find("kit.start(")
    at = page.find("data: [", start) if start >= 0 else -1
    if at < 0:
        return None
    for node in reversed(JsLiteral(page, at + len("data: ")).value()):
        data = (node or {}).get("data") or {}
        if data.get(key) is not None:
            return data[key]
    return None


# --------------------------------------------------------------------------
# Stage 1: crawl
# --------------------------------------------------------------------------
def crawl_listings(http, limit):
    """Return {slug: listing record or None} for every edition of every manual."""
    landing = http.text(VAULT)
    collections = list(dict.fromkeys(re.findall(r'\?coll=([a-z0-9-]+)"', landing)))
    collections = collections or DEFAULT_COLLECTIONS
    found, expected = {}, 0
    for coll in collections:
        page = 1
        while True:
            data = embedded(http.text(f"{VAULT}?coll={coll}&page={page}"), "list")
            if data is None:
                raise SystemExit(f"❌ no listing data for collection {coll} page {page}")
            results = data.get("results") or []
            if page == 1:
                expected += data.get("searched") or data.get("total") or 0
                log(f"  {coll}: {data.get('total')} publications, {data.get('searched')} editions")
            for rec in results:
                found[rec["slug"]] = rec
                for ed in rec.get("editions") or []:
                    found.setdefault(ed["slug"], None)
            if limit and len(found) >= limit:
                return dict(list(found.items())[:limit]), 0
            if not results or page * (data.get("size") or 30) >= (data.get("total") or 0):
                break
            page += 1
    return found, expected


def crawl(http, args, meta_dir):
    """Refresh <work-dir>/meta/<slug>.json; return (slugs seen, failures)."""
    log("ℹ️ Crawling listings ...")
    listed, expected = crawl_listings(http, args.limit)
    log(f"  {len(listed)} manuals listed" + (f" (site reports {expected})" if expected else ""))
    if expected and len(listed) < expected * 0.98:
        log(f"  ⚠️ fewer manuals listed than the site reports ({len(listed)} < {expected})")

    queue, seen, failures = list(listed), set(listed), []
    fetched = 0
    max_age = args.detail_max_age * 86400
    while queue:
        slug = queue.pop()
        path = meta_dir / f"{slug}.json"
        rec = listed.get(slug)
        list_hash = (
            hashlib.sha1(json.dumps(rec, sort_keys=True).encode()).hexdigest() if rec else None
        )
        doc = None
        if path.exists():
            doc = json.loads(path.read_text(encoding="utf-8"))
            crawl_info = doc.get("_crawl", {})
            stale = time.time() - crawl_info.get("fetched", 0) > max_age
            changed = list_hash and crawl_info.get("list_hash") != list_hash
            if stale or changed:
                doc = None
        if doc is None:
            try:
                page = http.text(f"{VAULT}/{slug}")
                pub = embedded(page, "pub")
                if not pub or not pub.get("slug"):
                    raise ValueError("no publication data in page")
            except Exception as e:  # noqa: BLE001 - keep crawling, report at the end
                log(f"  ❌ {slug}: {e}")
                failures.append(f"page {slug}")
                continue
            doc = {
                "pub": pub,
                "_crawl": {
                    "fetched": int(time.time()),
                    "list_hash": list_hash,
                    "source": f"{VAULT}/{slug}",
                },
            }
            tmp = path.with_suffix(".json.part")
            tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(path)
            fetched += 1
            if fetched % 100 == 0:
                log(f"  ... {fetched} manual pages fetched, {len(queue)} queued")
        if args.limit:
            continue
        # Follow cross-links so editions and cited manuals outside the listing are kept.
        pub = doc["pub"]
        linked = (pub.get("editions") or []) + (pub.get("cited_by") or [])
        linked += [r for r in pub.get("references") or [] if r.get("held")]
        for other in linked:
            s = other.get("slug")
            if s and s not in seen and s not in RESERVED_SLUGS:
                seen.add(s)
                queue.append(s)
    log(f"✅ Crawl done: {len(seen)} manuals, {fetched} pages fetched, {len(failures)} failed")
    return seen, failures


# --------------------------------------------------------------------------
# Stage 2: download
# --------------------------------------------------------------------------
class State:
    """ETag bookkeeping for mirrored files, persisted as JSON."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.data = json.loads(path.read_text()) if path.exists() else {}
        self.dirty = 0

    def get(self, url):
        return self.data.get(url, {})

    def put(self, url, entry):
        with self.lock:
            self.data[url] = entry
            self.dirty += 1
            if self.dirty >= 50:
                self._save()

    def _save(self):
        tmp = self.path.with_suffix(".part")
        tmp.write_text(json.dumps(self.data, indent=0, sort_keys=True))
        tmp.replace(self.path)
        self.dirty = 0

    def save(self):
        with self.lock:
            self._save()


def local_path(files_dir, url):
    return files_dir / urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip("/")


def manual_files(pub, formats):
    """[(kind, url)] of the files to mirror for one manual."""
    out = []
    for fmt in formats:
        if pub.get(f"{fmt}_url"):
            out.append((fmt, pub[f"{fmt}_url"]))
    if pub.get("has_thumb"):
        out.append(("thumb", f"https://files.trex-arms.com/data/thumbs/{pub['id']}.webp"))
    return out


def download_one(http, state, files_dir, url):
    """Returns 'new', 'same', 'missing' or raises."""
    return http.retry_read(url, lambda: download_once(http, state, files_dir, url))


def download_once(http, state, files_dir, url):
    dest = local_path(files_dir, url)
    known = state.get(url)
    headers = {}
    if dest.exists() and known.get("etag") and dest.stat().st_size == known.get("size"):
        headers["If-None-Match"] = known["etag"]
    try:
        resp = http.open(url, headers=headers, timeout=600)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return "same"
        if e.code in (404, 410):
            return "missing"
        raise
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    size = 0
    with resp, open(tmp, "wb") as f:
        while chunk := resp.read(1024 * 1024):
            f.write(chunk)
            size += len(chunk)
    declared = resp.headers.get("Content-Length")
    if declared and int(declared) != size:
        tmp.unlink(missing_ok=True)
        raise IOError(f"short download ({size} of {declared} bytes)")
    tmp.replace(dest)
    state.put(url, {"etag": resp.headers.get("ETag"), "size": size})
    return "new"


def download(http, args, pubs, files_dir, state):
    jobs = [url for pub in pubs for _, url in manual_files(pub, args.formats)]
    log(f"ℹ️ Checking {len(jobs)} files ...")
    counts = {"new": 0, "same": 0, "missing": 0}
    failures, missing = [], []
    lock = threading.Lock()
    done = [0]

    def work(url):
        try:
            result = download_one(http, state, files_dir, url)
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the mirror
            result = None
            log(f"  ❌ {url}: {e}")
        with lock:
            done[0] += 1
            if result:
                counts[result] += 1
            if result is None:
                failures.append(f"file {url}")
            elif result == "missing":  # gone upstream: nothing a re-run can fix
                missing.append(url)
            if done[0] % 250 == 0:
                log(f"  ... {done[0]}/{len(jobs)} ({counts['new']} downloaded)")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, jobs))
    state.save()
    log(
        f"✅ Files: {counts['new']} downloaded, {counts['same']} unchanged, "
        f"{counts['missing']} missing upstream, {len(failures)} failed"
    )
    return failures, missing


# --------------------------------------------------------------------------
# Stage 3: build
# --------------------------------------------------------------------------
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def display_title(title):
    """The site stores many titles in capitals; show those in title case."""
    title = (title or "Untitled").strip()
    if title != title.upper():
        return title
    words = []
    for i, w in enumerate(title.split()):
        if any(ch.isdigit() for ch in w) or w.startswith(("{", "(")) and len(w) <= 6:
            words.append(w)
        elif i and w.lower() in SMALL_WORDS:
            words.append(w.lower())
        else:
            words.append("-".join(p[:1] + p[1:].lower() for p in w.split("-")))
    return " ".join(words)


def label(kind, value):
    if not value:
        return ""
    return LABELS.get(kind, {}).get(value) or value.replace("-", " ").title()


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


def edition_label(pub):
    date = pub.get("edition_date") or ""
    try:
        d = datetime.date.fromisoformat(date)
        text = d.strftime("%b %Y")
    except ValueError:
        text = str(pub.get("edition_year") or "Undated")
    if pub.get("change_level"):
        text += f" ({pub['change_level']})"
    return text


def epub_text(path):
    """Plain text of an EPUB, for the full-text index."""
    parts = []
    try:
        with zipfile.ZipFile(path) as z:
            for name in sorted(z.namelist()):
                if name.lower().endswith((".xhtml", ".html", ".htm")):
                    raw = z.read(name).decode("utf-8", "replace")
                    raw = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", raw)
                    parts.append(html.unescape(re.sub(r"<[^>]+>", " ", raw)))
    except (zipfile.BadZipFile, OSError) as e:
        log(f"  ⚠️ could not read {path.name}: {e}")
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


STYLE = """
:root{--bg:#f6f5f1;--card:#fff;--fg:#1d1d1b;--mute:#6b6a64;--line:#dcdad2;--accent:#5b6b3a;--tag:#ecebe4}
@media(prefers-color-scheme:dark){:root{--bg:#161614;--card:#1f1f1c;--fg:#e9e7df;--mute:#a09e94;
--line:#33322d;--accent:#a9bb7c;--tag:#2a2a26}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1000px;margin:0 auto;padding:16px}
a{color:var(--accent)}
h1{font-size:1.6rem;line-height:1.2;margin:.2em 0}
h2{font-size:1.1rem;margin:1.6em 0 .5em;border-bottom:1px solid var(--line);padding-bottom:.2em}
.mute{color:var(--mute)}.small{font-size:.85rem}
.eyebrow{color:var(--mute);font-size:.85rem;letter-spacing:.03em}
.tag{display:inline-block;background:var(--tag);border-radius:4px;padding:1px 7px;font-size:.78rem;margin:0 4px 4px 0}
.filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:14px 0}
.filters input,.filters select{width:100%;padding:8px;font:inherit;color:var(--fg);background:var(--card);
border:1px solid var(--line);border-radius:6px}
.filters input{grid-column:1/-1}
.row{display:flex;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:10px;margin:8px 0}
.row img,.row .noimg{width:62px;height:80px;object-fit:cover;flex:none;border:1px solid var(--line);background:var(--tag)}
.row h3{margin:0;font-size:1rem}.row p{margin:.25em 0;font-size:.88rem;color:var(--mute)}
.head{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}
.head img{width:170px;max-width:40vw;border:1px solid var(--line)}
.head>div{flex:1;min-width:240px}
.btn{display:inline-block;background:var(--accent);color:var(--bg);text-decoration:none;font-weight:600;
padding:8px 14px;border-radius:6px;margin:6px 8px 0 0}
button.btn{border:0;font:inherit;cursor:pointer}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0}
dt{color:var(--mute)}dd{margin:0}
ul.toc,ul.refs{list-style:none;padding:0;margin:0}
ul.toc li{display:flex;justify-content:space-between;gap:12px;border-bottom:1px dotted var(--line);padding:2px 0}
ul.toc .l2{padding-left:18px}ul.toc .l3{padding-left:36px}ul.toc .l4{padding-left:54px}
ul.refs li{padding:3px 0}
"""

APP_JS = r"""
(function(){
var C=window.VAULT_CATALOG,F=window.VAULT_FACETS,keys=['collection','branch','type','function','echelon'];
var q=document.getElementById('q'),out=document.getElementById('results'),count=document.getElementById('count');
var more=document.getElementById('more'),sort=document.getElementById('sort'),shown=0,hits=[],PAGE=60;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
keys.forEach(function(k){var s=document.getElementById('f-'+k);F[k].forEach(function(o){
var e=document.createElement('option');e.value=o[0];e.textContent=o[1]+' ('+o[2]+')';s.appendChild(e)});s.onchange=run});
C.forEach(function(m){m._t=(m.designation+' '+m.title+' '+m.designation.replace(/[^a-z0-9]/gi,'')).toLowerCase()});
function row(m){return '<div class="row">'+(m.thumb?'<img loading="lazy" alt="" src="'+esc(m.thumb)+'">':'<span class="noimg"></span>')+
'<div><div class="eyebrow">'+esc(m.designation)+' · '+esc(m.branch_label)+' · '+esc(m.year||'Undated')+'</div>'+
'<h3><a href="m/'+esc(m.slug)+'.html">'+esc(m.title)+'</a></h3>'+(m.purpose?'<p>'+esc(m.purpose)+'</p>':'')+
'<span class="tag">'+esc(m.collection_label)+'</span>'+(m.pages?'<span class="tag">'+m.pages+' pages</span>':'')+
(m.function_label?'<span class="tag">'+esc(m.function_label)+'</span>':'')+'</div></div>'}
function draw(){out.insertAdjacentHTML('beforeend',hits.slice(shown,shown+PAGE).map(row).join(''));
shown=Math.min(hits.length,shown+PAGE);more.style.display=shown<hits.length?'':'none'}
function run(){var words=q.value.toLowerCase().split(/\s+/).filter(Boolean),f={};
keys.forEach(function(k){f[k]=document.getElementById('f-'+k).value});
hits=C.filter(function(m){for(var i=0;i<keys.length;i++){if(f[keys[i]]&&m[keys[i]]!==f[keys[i]])return false}
for(var j=0;j<words.length;j++){if(m._t.indexOf(words[j])<0)return false}return true});
var s=sort.value;hits.sort(function(a,b){if(s==='newest')return(b.date||'').localeCompare(a.date||'');
if(s==='oldest')return(a.date||'9').localeCompare(b.date||'9');if(s==='title')return a.title.localeCompare(b.title);
return a.designation.localeCompare(b.designation,undefined,{numeric:true})});
out.innerHTML='';shown=0;count.textContent=hits.length.toLocaleString()+' of '+C.length.toLocaleString()+' manuals';draw()}
q.oninput=run;sort.onchange=run;more.onclick=draw;run();
})();
"""


def page(title, body, depth=0):
    root = "../" * depth
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title>"
        f'<link rel="stylesheet" href="{root}assets/style.css"></head>'
        f"<body><main>{body}</main></body></html>"
    )


def zim_file_path(url):
    return "files/" + urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip("/")


def manual_page(pub, by_slug, files_dir, formats):
    e = html.escape
    title = display_title(pub.get("title"))
    present = {
        kind: url
        for kind, url in manual_files(pub, formats)
        if local_path(files_dir, url).exists()
    }
    rel = lambda url: "../" + urllib.parse.quote(zim_file_path(url))  # noqa: E731

    buttons = ""
    for fmt in formats:
        if fmt in present:
            size = human_size(local_path(files_dir, present[fmt]).stat().st_size)
            name = e((pub.get("download_name") or pub["slug"]) + f".{fmt}")
            buttons += (
                f'<a class="btn" href="{rel(present[fmt])}">{fmt.upper()} · {size}</a>'
                if fmt == "pdf"
                else f'<a class="btn" href="{rel(present[fmt])}" download="{name}">{fmt.upper()} · {size}</a>'
            )
        elif pub.get(f"{fmt}_url"):
            buttons += f'<span class="tag">{fmt.upper()} unavailable</span>'

    facts = [
        ("Designation", pub.get("designation")),
        ("Edition", edition_label(pub)),
        ("Status", label("status", pub.get("status"))),
        ("Branch", ", ".join(label("branch", s) for s in pub.get("services") or [])
            or pub.get("branch_label")),
        ("Type", pub.get("pub_type")),
        ("Proponent", pub.get("proponent")),
        ("Pages", pub.get("page_count")),
        ("Function", label("function", pub.get("functional_category"))),
        ("Echelon", label("echelon", pub.get("echelon"))),
        ("Collection", label("collection", pub.get("collection"))),
        ("Vault ID", pub.get("id")),
    ]
    facts_html = "".join(f"<dt>{k}</dt><dd>{e(str(v))}</dd>" for k, v in facts if v)

    def link(other):
        slug = other.get("slug")
        text = e(other.get("designation") or "")
        if slug and slug in by_slug:
            name = e(display_title(other.get("title") or by_slug[slug].get("title")))
            return f'<a href="{e(slug)}.html">{text}</a> <span class="mute">{name}</span>'
        return f'{text} <span class="mute small">not in the Vault</span>'

    body = [
        '<p class="small"><a href="../index.html">← Field Manual Vault</a></p><div class="head">'
    ]
    if "thumb" in present:
        body.append(f'<img alt="Cover" src="{rel(present["thumb"])}">')
    body.append(
        f'<div><div class="eyebrow">{e(pub.get("designation") or "")}</div><h1>{e(title)}</h1>'
        f'<p class="mute">{e(pub.get("branch_label") or "")} · {e(pub.get("pub_type") or "")} · '
        f'{e(edition_label(pub))} · {pub.get("page_count") or "?"} pages</p>{buttons}</div></div>'
    )
    if pub.get("purpose"):
        body.append(f"<h2>About</h2><p>{e(pub['purpose'])}</p>")
    body.append(f"<h2>Details</h2><dl>{facts_html}</dl>")
    if pub.get("distribution_statement"):
        body.append(f'<p class="small mute">{e(pub["distribution_statement"])}</p>')

    editions = [ed for ed in pub.get("editions") or [] if ed.get("slug") != pub["slug"]]
    if editions:
        items = "".join(
            f'<li><a href="{e(ed["slug"])}.html">{e(str(ed.get("label") or ed.get("edition_year")))}'
            "</a></li>"
            if ed["slug"] in by_slug
            else f'<li>{e(str(ed.get("label")))}</li>'
            for ed in editions
        )
        body.append(f'<h2>Other editions</h2><ul class="refs">{items}</ul>')

    if pub.get("toc"):
        rows = []
        for entry in pub["toc"]:
            level, text, num = (list(entry) + [None, None])[:3]
            target = f'{rel(present["pdf"])}#page={num}' if "pdf" in present and num else None
            name = f'<a href="{target}">{e(str(text))}</a>' if target else e(str(text))
            rows.append(
                f'<li class="l{min(int(level or 1), 4)}"><span>{name}</span>'
                f'<span class="mute">{num or ""}</span></li>'
            )
        body.append(f'<h2>Contents</h2><ul class="toc">{"".join(rows)}</ul>')

    refs = pub.get("references") or []
    if refs:
        items = "".join(
            f"<li>{link(r)}"
            + (f' <span class="mute small">×{r["count"]}</span>' if (r.get("count") or 0) > 1 else "")
            + "</li>"
            for r in refs
        )
        body.append(f'<h2>References ({len(refs)})</h2><ul class="refs">{items}</ul>')
    cited = pub.get("cited_by") or []
    if cited:
        items = "".join(f"<li>{link(c)}</li>" for c in cited)
        body.append(f'<h2>Cited by ({len(cited)})</h2><ul class="refs">{items}</ul>')

    body.append(
        f'<p class="small mute">Source: <a href="{VAULT}/{e(pub["slug"])}">'
        f'{VAULT}/{e(pub["slug"])}</a> · <a href="../data/manuals/{e(pub["slug"])}.json">'
        "raw metadata</a></p>"
    )
    return page(f"{pub.get('designation') or ''}: {title}", "".join(body), depth=1)


def catalog_entry(pub, files_dir):
    thumb = next((u for k, u in manual_files(pub, []) if k == "thumb"), None)
    purpose = pub.get("purpose") or ""
    return {
        "slug": pub["slug"],
        "designation": pub.get("designation") or "",
        "title": display_title(pub.get("title")),
        "branch": pub.get("branch") or "",
        "branch_label": pub.get("branch_label") or label("branch", pub.get("branch")),
        "type": pub.get("pub_type") or "",
        "collection": pub.get("collection") or "",
        "collection_label": label("collection", pub.get("collection")),
        "function": pub.get("functional_category") or "",
        "function_label": label("function", pub.get("functional_category")),
        "echelon": pub.get("echelon") or "",
        "status": pub.get("status") or "",
        "year": pub.get("edition_year"),
        "date": pub.get("edition_date"),
        "pages": pub.get("page_count"),
        "purpose": purpose if len(purpose) <= 220 else purpose[:217].rsplit(" ", 1)[0] + "…",
        "thumb": urllib.parse.quote(zim_file_path(thumb))
        if thumb and local_path(files_dir, thumb).exists()
        else None,
    }


def index_page(catalog, total_pages, built):
    facets = {}
    for key, kind in (("collection", "collection"), ("branch", "branch"), ("type", None),
                      ("function", "function"), ("echelon", "echelon")):
        counts = {}
        for m in catalog:
            if m[key]:
                counts[m[key]] = counts.get(m[key], 0) + 1
        facets[key] = [
            [value, label(kind, value) if kind else value, n]
            for value, n in sorted(counts.items(), key=lambda kv: -kv[1])
        ]
    selects = "".join(
        f'<select id="f-{k}" aria-label="{k}"><option value="">Any {k}</option></select>'
        for k in facets
    )
    body = (
        "<h1>Field Manual Vault</h1>"
        f'<p>{len(catalog):,} U.S. Army, Marine Corps, Navy, Air Force and Joint publications '
        f"({total_pages:,} pages), as original PDFs and EPUBs. An offline copy of the "
        f'<a href="{VAULT}">T.REX ARMS Field Manual Vault</a>, mirrored {built}.</p>'
        '<p class="small mute">The box below filters by designation and title. '
        "Use the Kiwix search to search inside the manuals.</p>"
        '<div class="filters"><input id="q" type="search" placeholder="Filter by designation or title" '
        f'autofocus>{selects}<select id="sort" aria-label="sort">'
        '<option value="designation">Sort: designation</option><option value="title">Sort: title</option>'
        '<option value="newest">Sort: newest</option><option value="oldest">Sort: oldest</option>'
        '</select></div><p id="count" class="mute small"></p><div id="results"></div>'
        '<button id="more" class="btn" type="button">Show more</button>'
        '<noscript><p>This index needs JavaScript; the Kiwix search works without it.</p></noscript>'
        '<script src="assets/catalog.js"></script><script src="assets/app.js"></script>'
    )
    catalog_js = (
        "window.VAULT_CATALOG=" + json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
        + ";window.VAULT_FACETS=" + json.dumps(facets, ensure_ascii=False, separators=(",", ":")) + ";"
    )
    return page("Field Manual Vault", body), catalog_js


def icon_png(size=48):
    """A plain 48x48 PNG (olive square with a pale book shape) as the ZIM illustration."""
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            book = 12 <= x < 36 and 9 <= y < 39
            spine = book and x < 16
            lines = book and x >= 20 and x < 32 and y in (17, 18, 23, 24)
            rows += b"\x3d\x47\x27" if spine or lines or not book else b"\xe9\xe7\xdf"

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )


def fingerprint(pubs, args, files_dir, state):
    h = hashlib.sha256(f"v{BUILD_VERSION}|{args.formats}|{args.fulltext}".encode())
    for pub in pubs:
        h.update(json.dumps(pub, sort_keys=True).encode())
        for _, url in manual_files(pub, args.formats):
            p = local_path(files_dir, url)
            h.update(f"{url}|{state.get(url).get('etag')}|{p.exists()}".encode())
    return h.hexdigest()


def build_zim(args, pubs, work, files_dir, dest):
    try:
        from libzim.writer import Creator, FileProvider, Hint, IndexData, Item, StringProvider
    except ImportError:
        raise SystemExit("❌ The build stage needs libzim: pip install libzim")

    class TextIndex(IndexData):
        def __init__(self, title, content, keywords):
            super().__init__()
            self.title, self.content, self.keywords = title, content, keywords

        def has_indexdata(self):
            return True

        def get_title(self):
            return self.title

        def get_content(self):
            return self.content

        def get_keywords(self):
            return self.keywords

        def get_wordcount(self):
            return len(self.content.split())

    class Entry(Item):
        def __init__(self, path, title, mimetype, text=None, file=None, front=False,
                     compress=True, index=None):
            super().__init__()
            self.path, self.title, self.mimetype = path, title, mimetype
            self.text, self.file, self.front, self.compress, self.index = (
                text, file, front, compress, index)

        def get_path(self):
            return self.path

        def get_title(self):
            return self.title

        def get_mimetype(self):
            return self.mimetype

        def get_contentprovider(self):
            if self.file is not None:
                return FileProvider(str(self.file))
            return StringProvider(self.text)

        def get_hints(self):
            return {Hint.FRONT_ARTICLE: self.front, Hint.COMPRESS: self.compress}

        def get_indexdata(self):
            return self.index

    by_slug = {p["slug"]: p for p in pubs}
    text_dir = work / "text"
    text_dir.mkdir(exist_ok=True)
    built = datetime.date.today().isoformat()
    mimetypes = {"pdf": "application/pdf", "epub": "application/epub+zip", "thumb": "image/webp"}
    catalog = [catalog_entry(p, files_dir) for p in pubs]
    index_html, catalog_js = index_page(catalog, sum(p.get("page_count") or 0 for p in pubs), built)

    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)
    log(f"ℹ️ Building {dest.name} from {len(pubs)} manuals ...")
    with Creator(tmp).config_indexing(True, "eng") as zim:
        zim.set_mainpath("index.html")
        zim.add_illustration(icon_png(), 48)
        for key, value in {
            "Name": ZIM_NAME,
            "Title": "Field Manual Vault",
            "Description": "U.S. military field manuals and doctrine, from WWII to today",
            "LongDescription": (
                f"{len(pubs)} public domain U.S. Army, Marine Corps, Navy, Air Force and Joint "
                "publications as PDF and EPUB, with tables of contents and citation links. "
                "Mirror of the T.REX ARMS Field Manual Vault."
            ),
            "Creator": "T.REX ARMS",
            "Publisher": "openshift homelab",
            "Date": built,
            "Language": "eng",
            "Tags": "military;manuals;preparedness;_category:other;_ftindex:yes;_pictures:yes",
            "Source": VAULT,
            "Scraper": f"build-trex-vault-zim.py v{BUILD_VERSION}",
            "License": "Public domain (U.S. Government works)",
        }.items():
            zim.add_metadata(key, value)

        zim.add_item(Entry("index.html", "Field Manual Vault", "text/html", text=index_html, front=True))
        zim.add_item(Entry("assets/style.css", "", "text/css", text=STYLE))
        zim.add_item(Entry("assets/app.js", "", "application/javascript", text=APP_JS))
        zim.add_item(Entry("assets/catalog.js", "", "application/javascript", text=catalog_js))
        zim.add_item(Entry(
            "data/catalog.json", "", "application/json",
            text=json.dumps(pubs, ensure_ascii=False, separators=(",", ":")),
        ))

        added = set()
        for n, pub in enumerate(pubs, 1):
            title = f"{pub.get('designation') or ''}: {display_title(pub.get('title'))}".strip(": ")
            files = dict(manual_files(pub, args.formats))
            content = " ".join(str(t[1]) for t in pub.get("toc") or [] if len(t) > 1)
            content = f"{title}. {pub.get('purpose') or ''} {content}"
            epub = local_path(files_dir, files["epub"]) if "epub" in files else None
            if args.fulltext and epub and epub.exists():
                cache = text_dir / f"{pub['id']}.txt"
                if not cache.exists() or cache.stat().st_mtime < epub.stat().st_mtime:
                    cache.write_text(epub_text(epub), encoding="utf-8")
                content += " " + cache.read_text(encoding="utf-8")
            keywords = " ".join(filter(None, [
                pub.get("designation"), pub.get("pub_type"), pub.get("branch_label"),
                label("function", pub.get("functional_category")),
            ]))
            zim.add_item(Entry(
                f"m/{pub['slug']}.html", title, "text/html",
                text=manual_page(pub, by_slug, files_dir, args.formats),
                front=True, index=TextIndex(title, content, keywords),
            ))
            zim.add_item(Entry(
                f"data/manuals/{pub['slug']}.json", "", "application/json",
                text=json.dumps(pub, ensure_ascii=False, indent=1),
            ))
            for kind, url in files.items():
                src, zpath = local_path(files_dir, url), zim_file_path(url)
                if src.exists() and zpath not in added:
                    added.add(zpath)
                    zim.add_item(Entry(zpath, "", mimetypes[kind], file=src, compress=False))
            if n % 250 == 0:
                log(f"  ... {n}/{len(pubs)} manuals added")
        log("  Finalizing (clusters and full-text index) ...")
    tmp.replace(dest)
    log(f"✅ Wrote {dest} ({human_size(dest.stat().st_size)})")


# --------------------------------------------------------------------------
# Stage 4: register
# --------------------------------------------------------------------------
def kiwix_manage(library, *cmd):
    try:
        result = subprocess.run(
            ["kiwix-manage", str(library), *cmd], capture_output=True, text=True, timeout=300
        )
    except FileNotFoundError:
        log("  ⚠️ kiwix-manage not found; skipping library.xml update")
        return False
    if result.returncode != 0:
        log(f"  ⚠️ kiwix-manage {cmd[0]} failed: {result.stderr.strip()}")
    return result.returncode == 0


def register(out_dir, dest):
    """Point library.xml at the new ZIM and drop older builds of this book."""
    library = out_dir / "library.xml"
    stale_ids = []
    if library.exists():
        try:
            for book in ET.parse(library).getroot().iter("book"):
                if Path(book.get("path", "")).name.startswith(f"{ZIM_NAME}_") and book.get("id"):
                    stale_ids.append(book.get("id"))
        except ET.ParseError as e:
            log(f"  ⚠️ could not read library.xml: {e}")
    if stale_ids:
        kiwix_manage(library, "remove", *stale_ids)
    registered = kiwix_manage(library, "add", str(dest))
    if registered:
        log(f"✅ Registered {dest.name} in library.xml")
    for old in out_dir.glob(f"{ZIM_NAME}_*.zim"):
        if old != dest:
            log(f"  Removing old build: {old.name}")
            old.unlink(missing_ok=True)
    return registered


# --------------------------------------------------------------------------
def parse_args():
    env = os.environ.get
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    p.add_argument("--work-dir", default=env("VAULT_WORK_DIR", "./trex-vault"),
                   help="mirror of metadata and files, reused between runs [VAULT_WORK_DIR]")
    p.add_argument("--output-dir", default=env("ZIM_DATA_DIR", "."),
                   help="where the ZIM and library.xml live [ZIM_DATA_DIR]")
    p.add_argument("--formats", default=env("VAULT_FORMATS", "pdf,epub"),
                   help="file formats to mirror: pdf, epub [VAULT_FORMATS]")
    p.add_argument("--no-fulltext", dest="fulltext", action="store_false",
                   default=env("VAULT_FULLTEXT", "true").lower() != "false",
                   help="index only titles, summaries and contents [VAULT_FULLTEXT=false]")
    p.add_argument("--delay", type=float, default=float(env("VAULT_REQUEST_DELAY", "0.5")),
                   help="seconds between requests to one host [VAULT_REQUEST_DELAY]")
    p.add_argument("--workers", type=int, default=int(env("VAULT_WORKERS", "4")),
                   help="parallel file downloads [VAULT_WORKERS]")
    p.add_argument("--detail-max-age", type=int, default=int(env("VAULT_DETAIL_MAX_AGE", "30")),
                   help="days before a manual's metadata is fetched again [VAULT_DETAIL_MAX_AGE]")
    p.add_argument("--user-agent",
                   default=env("VAULT_USER_AGENT", "kiwix-zim-builder/1.0 (personal offline archive)"),
                   help="[VAULT_USER_AGENT]")
    p.add_argument("--limit", type=int, default=int(env("VAULT_LIMIT", "0")),
                   help="only the first N manuals, for testing [VAULT_LIMIT]")
    p.add_argument("--prune", action="store_true", default=env("VAULT_PRUNE", "").lower() == "true",
                   help="drop manuals no longer on the site (default: keep them) [VAULT_PRUNE=true]")
    p.add_argument("--force", action="store_true", help="rebuild the ZIM even if nothing changed")
    p.add_argument("--skip-crawl", action="store_true", help="build from the existing mirror only")
    args = p.parse_args()
    args.formats = [f for f in (x.strip().lower() for x in args.formats.split(",")) if f]
    if not set(args.formats) <= {"pdf", "epub"}:
        p.error("--formats takes pdf and/or epub")
    return args


def main():
    args = parse_args()
    work, out_dir = Path(args.work_dir), Path(args.output_dir)
    meta_dir, files_dir = work / "meta", work / "files"
    for d in (meta_dir, files_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)
    http = Http(args.user_agent, args.delay)
    state = State(work / "state.json")
    failures, missing = [], []

    seen = None
    if not args.skip_crawl:
        seen, crawl_failures = crawl(http, args, meta_dir)
        failures += crawl_failures

    pubs = []
    for path in sorted(meta_dir.glob("*.json")):
        if args.limit and seen is not None and path.stem not in seen:
            continue
        if args.prune and seen is not None and not crawl_failures and path.stem not in seen:
            log(f"  Pruning {path.stem} (no longer on the site)")
            path.unlink()
            continue
        pubs.append(json.loads(path.read_text(encoding="utf-8"))["pub"])
    if not pubs:
        raise SystemExit("❌ No manuals in the mirror; nothing to build")

    if not args.skip_crawl:
        file_failures, missing = download(http, args, pubs, files_dir, state)
        failures += file_failures

    last_path = work / "last-build.json"
    last = json.loads(last_path.read_text()) if last_path.exists() else {}
    digest = fingerprint(pubs, args, files_dir, state)
    current = out_dir / last.get("zim", "-")
    if not args.force and last.get("fingerprint") == digest and current.is_file():
        log(f"✅ Nothing changed since the last build; keeping {current.name}")
        if not last.get("registered"):  # kiwix-manage was unavailable last time
            last["registered"] = register(out_dir, current)
            last_path.write_text(json.dumps(last))
    else:
        dest = out_dir / f"{ZIM_NAME}_{datetime.date.today():%Y-%m}.zim"
        build_zim(args, pubs, work, files_dir, dest)
        registered = register(out_dir, dest)
        last_path.write_text(
            json.dumps({"fingerprint": digest, "zim": dest.name, "registered": registered})
        )

    if missing:
        log(f"\n⚠️ {len(missing)} files are missing upstream (404) and were left out:")
        for url in sorted(missing)[:50]:
            log(f"  - {url}")
    if failures:
        log(f"\n❌ {len(failures)} items could not be mirrored:")
        for item in failures[:50]:
            log(f"  - {item}")
        sys.exit(1)


if __name__ == "__main__":
    main()
