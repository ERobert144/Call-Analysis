#!/usr/bin/env python3
"""Load a document's text from whatever form the cache holds for it.

Triage workers wrote .json ({"fileContent": ...} or {"content": base64}), .md
and .html. Extraction writes .txt. Read them all so nothing is re-fetched.
"""
import json, os, glob, base64, re, html as _html

def _from_html(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h[1-6]>|</li>", "\n", h)
    return _html.unescape(re.sub(r"(?s)<[^>]+>", "", h))

def load_text(base, file_id):
    for ext in ("txt", "md", "json", "html"):
        p = os.path.join(base, "cache", f"{file_id}.{ext}")
        if not os.path.exists(p):
            continue
        raw = open(p, encoding="utf-8", errors="replace").read()
        if ext == "json":
            try:
                d = json.loads(raw)
            except Exception:
                return raw
            if d.get("fileContent"):
                return d["fileContent"]
            if d.get("content"):
                try:
                    dec = base64.b64decode(d["content"]).decode("utf-8", "replace")
                    return _from_html(dec) if "<" in dec[:200] else dec
                except Exception:
                    return d["content"]
            return raw
        return _from_html(raw) if ext == "html" else raw
    return None

def cached_ids(base):
    ids = set()
    for p in glob.glob(os.path.join(base, "cache", "*")):
        b = os.path.basename(p)
        if "." in b:
            ids.add(b.rsplit(".", 1)[0])
    return ids
