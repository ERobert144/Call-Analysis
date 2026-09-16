#!/usr/bin/env python3
"""Phase 1: build inventory.csv from Drive metadata. Metadata only - no documents opened."""
import csv, re, os
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(BASE, "build")

PARENTS = {
    "BOROOT":        ("Google Meet", "Bo"),
    "BOCEDAR":       ("Chat: CourseRev + Cedaredge Golf Course - 2026/09/01 10:00 PDT", "Bo"),
    "BOTILDEN":      ("Chat: CourseRev + Tilden Park Golf Course - 2026/09/04 10:00 PDT", "Bo"),
    "BOHOKUALA":     ("CourseRev + Ocean Course Hokuala - 2026/08/31 11:30 PDT", "Bo"),
    "BOTENFORE":     ("TenFore<>CourseRev info sesh - 2026/08/13 12:59 EDT", "Bo"),
    "BOSUMMIT":      ("CourseRev AI | Summit - 2026/07/29 14:55 CEST", "Bo"),
    "BOOUTBOUND":    ("Outbound Team Sync (recurring)", "Bo"),
    "BOMONDAY":      ("Monday Sales Sync (recurring)", "Bo"),
    "BOTHURSDAY":    ("Thursday Sales Sync (recurring)", "Bo"),
    "BOHUDDLE":      ("Huddle Meeting (recurring)", "Bo"),
    "BOCOURSEREVIEW":("cou-rser-eview (recurring)", "Bo"),
    "JAROOT":        ("Meet Recordings", "Jason"),
}
MIME = {"doc": "application/vnd.google-apps.document",
        "mp4": "video/mp4",
        "vid": "application/vnd.google-apps.vid",
        "shortcut": "application/vnd.google-apps.shortcut"}

# Meetings that are CourseRev-internal, not prospect calls.
INTERNAL_RE = [
    r"^Monday Sales Sync", r"^Thursday Sales Sync", r"^Huddle Meeting",
    r"^Outbound Team Sync", r"^Course Review", r"cou-rser-eview",
    r"^Jason / Elias Weekly 1:1", r"^Tim / Jason", r"^Jason & Bo",
    r"^Outbound Sales Strategy & Demo Practice", r"^Casey / Jason",
]
# Title shapes that name the prospect account.
ACCOUNT_RE = [
    r"^Chat:\s*CourseRev\s*\+\s*(.+?)\s*-\s*\d{4}/",
    r"^CourseRev\s*\+\s*(.+?)\s*-\s*(?:Chat|Quick Chat|Quick Call|Touchbase)",
    r"^CourseRev\s*\+\s*(.+?)\s*-\s*\d{4}/",
    r"^(.+?)\s*&\s*CourseRev\s*-\s*Quick Chat",
    r"^(.+?)\s*&\s*Courserev\s+(?:Discussion|Exploratory|exploratory)",
    r"^Courserev\s*&\s*(.+?)\s+exploratory",
    r"^(.+?)\s+onboarding w/ Courserev",
    r"^Meeting Notes with\s+(.+?)$",
    r"^(.+?)\s+Meeting Notes$",
    r"^(.+?)\s+Meeting\s*-\s*Notes by Gemini$",
    r"^(.+?)<>CourseRev",
]
DATE_RE  = re.compile(r"(\d{4})[/-](\d{2})[/-](\d{2})\s+(\d{2}):(\d{2})\s*([A-Z]{2,4}|GMT[+-]\d+)")
DATE2_RE = re.compile(r"_(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s+(\d{4})")
MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}

def parse_when(title):
    m = DATE_RE.search(title)
    if m:
        y, mo, d, hh, mm, tz = m.groups()
        return f"{y}-{mo}-{d}", f"{hh}:{mm} {tz}"
    m = DATE2_RE.search(title)
    if m:
        mon, d, y = m.groups()
        return f"{y}-{MONTHS[mon]:02d}-{int(d):02d}", ""
    return "", ""

def parse_account(title):
    for pat in ACCOUNT_RE:
        m = re.match(pat, title)
        if m:
            acct = re.sub(r"\s+", " ", m.group(1)).strip(" -")
            if acct and acct.lower() not in ("courserev", "coursrev"):
                return acct, "title"
    return "", "unresolved"

def classify(title, account):
    for pat in INTERNAL_RE:
        if re.search(pat, title):
            return "internal"
    if account:
        # TenFore is a company, not a golf course - verify against the body.
        if title.startswith("TenFore"):
            return "unknown"
        return "customer_call"
    return "unknown"

def tier(size, mime):
    if mime == "shortcut":
        return "shortcut_unreadable"
    if mime in ("mp4", "vid"):
        return "video"
    if size == 1024:
        return "stub"           # Google's empty transcript placeholder
    if size < 3 * 1024:
        return "stub"
    if size < 10 * 1024:
        return "thin"
    if size < 40 * 1024:
        return "moderate"
    return "rich"

def meeting_key(row):
    """Group a meeting's doc + recordings together."""
    if row["meeting_date"] and row["meeting_time"]:
        hhmm = row["meeting_time"].split()[0]
        return f"{row['rep']}|{row['meeting_date']}|{hhmm}"
    if row["meeting_date"]:
        return f"{row['rep']}|{row['meeting_date']}"
    stem = re.sub(r"\s*-\s*(Notes by Gemini|Transcript|Recording(\s*\d+)?)\s*$", "", row["file_name"])
    return f"{row['rep']}|{stem}"

# Titles with no date in them - fall back to Drive createdTime (UTC date).
DATE_BACKFILL = {
    "1l0Iq_O1cJQ2mhj3ukRfmIXwgtYHeUpuhGhUZVZTxOMI": "2026-08-06",  # Stonebridge Meadows Meeting Notes
    "1IGbv5jcQ6q8_MMNyeZfmtXpsr-dlNGmlU7BSUOvsYDU": "2026-07-02",  # Meeting Notes with Deerhurst
    "17Kdv4-QBw51qfiyqRJUH5QDaCDZzvCG4NvbLIOWALq0": "2026-06-11",  # Scott Lake Meeting
}

rows = []
for fn in ("raw_files.tsv", "raw_shortcuts.tsv"):
    with open(os.path.join(BUILD, fn)) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            title = r["file_name"]
            folder, rep = PARENTS[r["parent_id"]]
            size = int(r["size_bytes"]) if r["size_bytes"] else 0
            date, time = parse_when(title)
            if not date:
                date = DATE_BACKFILL.get(r["file_id"], "")
            acct, src = parse_account(title)
            mime = r["mime"]
            url = (f"https://docs.google.com/document/d/{r['file_id']}/edit"
                   if mime == "doc" else f"https://drive.google.com/file/d/{r['file_id']}/view")
            rows.append({
                "file_id": r["file_id"], "file_name": title, "mime_type": MIME[mime],
                "size_bytes": size or "", "char_count": "",   # filled during extraction
                "parent_folder_name": folder, "rep": rep,
                "meeting_date": date, "meeting_time": time,
                "account_guess": acct, "account_source": src,
                "classification": classify(title, acct),
                "content_tier": tier(size, mime),
                "has_video": "", "doc_url": url, "_mime": mime,
            })

# has_video / video_only need the whole meeting group.
groups = defaultdict(list)
for r in rows:
    groups[meeting_key(r)].append(r)
for key, grp in groups.items():
    has_vid = any(g["_mime"] in ("mp4", "vid") for g in grp)
    for g in grp:
        g["has_video"] = "TRUE" if has_vid else "FALSE"

# A recording counts as a real gap only if that rep has no notes doc that day.
docs_by_day = defaultdict(bool)
for r in rows:
    if r["_mime"] == "doc" and r["meeting_date"]:
        docs_by_day[(r["rep"], r["meeting_date"])] = True
for r in rows:
    if r["_mime"] in ("mp4", "vid") and not docs_by_day.get((r["rep"], r["meeting_date"])):
        r["content_tier"] = "video_only"

# One account can be written several ways ("Dacotah Ridge" / "Dacotah Ridge GC").
# Collapse to the most common spelling, tie-broken by length.
def slug(a):
    a = a.lower().strip()
    a = re.sub(r"\s+(gc|g\.c\.|golf course|golf club|golf links|cc|c\.c\.|country club)$", "", a)
    return re.sub(r"[^a-z0-9]+", " ", a).strip()

variants = defaultdict(Counter)
for r in rows:
    if r["account_guess"]:
        variants[slug(r["account_guess"])][r["account_guess"]] += 1
canon = {s_: max(c.items(), key=lambda kv: (kv[1], len(kv[0])))[0] for s_, c in variants.items()}
for r in rows:
    if r["account_guess"]:
        r["account_guess"] = canon[slug(r["account_guess"])]

rows.sort(key=lambda r: (r["rep"], r["meeting_date"] or "0000", r["file_name"]))
cols = ["file_id","file_name","mime_type","size_bytes","char_count","parent_folder_name","rep",
        "meeting_date","meeting_time","account_guess","account_source","classification",
        "content_tier","has_video","doc_url"]
out = os.path.join(BASE, "inventory.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r[c] for c in cols})
print(f"wrote {out}: {len(rows)} rows")
