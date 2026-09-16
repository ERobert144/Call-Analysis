#!/usr/bin/env python3
"""Report text volume and transcript presence for a fetched Gemini notes doc."""
import sys, json, re
def probe(path, label):
    d = json.load(open(path))
    t = d.get("fileContent") or d.get("content") or ""
    # The verbatim transcript lives under a top-level "Transcript" heading.
    m = re.search(r"\n#\s*\*{0,2}[^\n]*Transcript", t)
    tr = t[m.start():] if m else ""
    turns = len(re.findall(r"\n\*\*[A-Z][^*\n]{1,40}:\*\*", tr))
    dur = re.search(r"Transcription ended after ([\d:]+)", t)
    print(f"{label:34} chars={len(t):>6}  transcript={'YES' if m else 'no ':3} "
          f"tr_chars={len(tr):>6} turns={turns:>4} dur={dur.group(1) if dur else '-':>8}")
for a in sys.argv[1:]:
    p, l = a.split("::")
    probe(p, l)
