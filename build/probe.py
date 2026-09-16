#!/usr/bin/env python3
"""Report text volume and transcript presence for a fetched Gemini notes doc.

Two document shapes exist and they do NOT share a format:
  - Gemini "Notes by Gemini" docs: bolded "**Speaker:**" turns,
    "Transcription ended after HH:MM:SS".
  - Raw Meet transcript exports ("<meet-code> (date) - Transcript"):
    plain "Speaker:" turns, "Meeting ended after" / "Session ended after".
Handle both or the corpus gets under-reported.
"""
import sys, json, re

TURN_BOLD  = re.compile(r"\n\*\*([A-Z][^*\n]{1,40}):\*\*")
TURN_PLAIN = re.compile(r"\n([A-Z][A-Za-z.'\- ]{1,40}):\s")
END_RE     = re.compile(r"(?:Transcription|Meeting|Session) ended after ([\d:]+)")
HEAD_RE    = re.compile(r"\n#{1,3}\s*\*{0,2}[^\n]{0,40}Transcript", re.I)

def analyse(text):
    m = HEAD_RE.search(text)
    tr = text[m.start():] if m else ""
    bold, plain = len(TURN_BOLD.findall(tr)), len(TURN_PLAIN.findall(tr))
    turns = max(bold, plain)
    # A heading alone is not a transcript - it needs actual dialogue under it.
    has = bool(m) and turns >= 3
    durs = END_RE.findall(text)
    return {"chars": len(text), "has_transcript": has, "transcript_chars": len(tr) if has else 0,
            "turns": turns, "turn_style": "bold" if bold >= plain else "plain",
            "duration": durs[-1] if durs else None}

def load(path):
    d = json.load(open(path))
    return d.get("fileContent") or d.get("content") or ""

if __name__ == "__main__":
    for a in sys.argv[1:]:
        path, _, label = a.partition("::")
        r = analyse(load(path))
        print(f"{(label or path)[:34]:34} chars={r['chars']:>6} "
              f"transcript={'YES' if r['has_transcript'] else 'no ':3} "
              f"tr_chars={r['transcript_chars']:>6} turns={r['turns']:>4} "
              f"style={r['turn_style']:5} dur={r['duration'] or '-':>8}")
