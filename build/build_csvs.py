#!/usr/bin/env python3
"""Phase 3: emit calls.csv, objections.csv and gaps.md from extracted/*.json.

Refuses to run if validate_extraction.py reports errors - a clean-looking CSV
built over invented fields is worse than no CSV.
"""
import json, glob, csv, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from callpath import normalise
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if subprocess.run([sys.executable, os.path.join(BASE, "build", "validate_extraction.py")]).returncode:
    sys.exit("\nvalidation failed - fix the extractions before emitting CSVs")

inv = {r["file_id"]: r for r in csv.DictReader(open(os.path.join(BASE, "inventory.csv")))}
tri = {}
for p in glob.glob(os.path.join(BASE, "triage", "*.json")):
    try:
        d = json.load(open(p)); tri[d.get("file_id") or os.path.basename(p)[:-5]] = d
    except Exception: pass

calls = []
for p in sorted(glob.glob(os.path.join(BASE, "extracted", "*.json"))):
    try: calls.append(json.load(open(p)))
    except Exception as e: print(f"  skip unparseable {os.path.basename(p)}: {e}")

def j(v):
    if v is None: return ""
    if isinstance(v, list): return "|".join(str(x) for x in v if x is not None)
    return v

# --- calls.csv -----------------------------------------------------------
CALL_COLS = ["call_id","rep","date","account_name","account_source","meeting_type",
             "content_tier","prospect_seniority","attendee_count","demo_happened",
             "features_demoed","pain_points","current_solution","objection_count","objections_determinable",
             "objection_categories","objections_resolved","sentiment_open","sentiment_post_demo",
             "sentiment_at_pricing","sentiment_close","sentiment_trajectory","call_path_norm","call_path_len","call_path",
             "pivot_point_count","next_step_secured","next_step_has_date","next_step_description",
             "buying_signal_count","stall_count","rep_commitment_count","unanswered_question_count",
             "extraction_confidence","doc_url"]

def sent(c, cp):
    v = (c.get("sentiment") or {}).get(cp)
    return "" if not isinstance(v, dict) or v.get("score") is None else v["score"]

with open(os.path.join(BASE, "calls.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=CALL_COLS); w.writeheader()
    for c in calls:
        raw_objs = c.get("objections")
        objs = raw_objs or []
        w.writerow({
            "call_id": c.get("call_id"), "rep": j(c.get("rep")), "date": j(c.get("date")),
            "account_name": j(c.get("account_name")), "account_source": j(c.get("account_source")),
            "meeting_type": j(c.get("meeting_type")), "content_tier": j(c.get("content_tier")),
            "prospect_seniority": j(c.get("prospect_seniority")),
            "attendee_count": len(c.get("attendees") or []),
            "demo_happened": j(c.get("demo_happened")),
            "features_demoed": j(c.get("features_demoed")), "pain_points": j(c.get("pain_points")),
            "current_solution": j(c.get("current_solution")),
            "objection_count": len(objs) if raw_objs is not None else "",
            "objections_determinable": raw_objs is not None,
            "objection_categories": "|".join(sorted({o.get("category") for o in objs if o.get("category")})),
            "objections_resolved": sum(1 for o in objs if o.get("resolved_in_call") is True),
            "sentiment_open": sent(c,"open"), "sentiment_post_demo": sent(c,"post_demo"),
            "sentiment_at_pricing": sent(c,"at_pricing"), "sentiment_close": sent(c,"close"),
            "sentiment_trajectory": j((c.get("sentiment") or {}).get("trajectory")),
            "call_path_norm": ">".join(normalise(c.get("call_path"))),
            "call_path_len": len(c.get("call_path") or []),
            "call_path": j(c.get("call_path")),
            "pivot_point_count": len(c.get("pivot_points") or []),
            "next_step_secured": j(c.get("next_step_secured")),
            "next_step_has_date": j(c.get("next_step_has_date")),
            "next_step_description": j(c.get("next_step_description")),
            "buying_signal_count": len(c.get("buying_signals") or []),
            "stall_count": len(c.get("stalls") or []),
            "rep_commitment_count": len(c.get("rep_commitments") or []),
            "unanswered_question_count": len(c.get("unanswered_questions") or []),
            "extraction_confidence": j(c.get("extraction_confidence")), "doc_url": j(c.get("doc_url")),
        })

# --- objections.csv (long format - one row per objection) ----------------
OBJ_COLS = ["call_id","rep","account_name","date","meeting_type","content_tier","objection_index",
            "category","response_tactic","prospect_next_move","resolved_in_call",
            "quote_source","trigger_quote","rep_response_summary","next_step_secured","extraction_confidence"]
nobj = 0
with open(os.path.join(BASE, "objections.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=OBJ_COLS); w.writeheader()
    for c in calls:
        for i, o in enumerate(c.get("objections") or []):
            nobj += 1
            w.writerow({"call_id": c.get("call_id"), "rep": j(c.get("rep")),
                        "account_name": j(c.get("account_name")), "date": j(c.get("date")),
                        "meeting_type": j(c.get("meeting_type")), "content_tier": j(c.get("content_tier")),
                        "objection_index": i, "category": j(o.get("category")),
                        "response_tactic": j(o.get("response_tactic")),
                        "prospect_next_move": j(o.get("prospect_next_move")),
                        "resolved_in_call": j(o.get("resolved_in_call")),
                        "quote_source": j(o.get("quote_source")),
                        "trigger_quote": j(o.get("trigger_quote")),
                        "rep_response_summary": j(o.get("rep_response_summary")),
                        "next_step_secured": j(c.get("next_step_secured")),
                        "extraction_confidence": j(c.get("extraction_confidence"))})

# --- gaps.md -------------------------------------------------------------
done = {c.get("call_id") for c in calls}
lines = ["# Gaps", "",
         "Everything in the corpus that did not become a usable row, and why.", ""]

def section(title, rows, why):
    lines.append(f"## {title} ({len(rows)})"); lines.append(""); lines.append(why); lines.append("")
    if rows:
        lines.append("| rep | date | account | file |"); lines.append("|---|---|---|---|")
        for r in rows:
            lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
    lines.append("")

vids = [(r["rep"], r["meeting_date"], "-", r["file_name"])
        for r in inv.values() if r["content_tier"] == "video_only"]
shorts = [(r["rep"], r["meeting_date"], "-", r["file_name"])
          for r in inv.values() if r["content_tier"] == "shortcut_unreadable"]
stubs, unres, lowc, notdone = [], [], [], []
for fid, t in tri.items():
    r = inv.get(fid, {})
    row = (r.get("rep",""), r.get("meeting_date",""), t.get("account_name") or "-", r.get("file_name",""))
    if (t.get("char_count") or 0) < 2500 and not t.get("has_transcript"): stubs.append(row)
    elif t.get("is_customer_call") and not (t.get("account_name") or "").strip(): unres.append(row)
    if fid not in done and t.get("is_customer_call"): notdone.append(row)
for c in calls:
    if c.get("extraction_confidence") == "low":
        r = inv.get(c.get("call_id"), {})
        lowc.append((r.get("rep",""), r.get("meeting_date",""), c.get("account_name") or "-", r.get("file_name","")))

section("Video only", vids, "Recording exists with no notes doc for that rep-day. Not transcribed - out of scope.")
section("Unresolvable shortcuts", shorts, "Drive shortcuts in Bo's folder. `read_file_content` returns `{}`; the target docs live in other users' folders and are recoverable by title search if ever needed.")
section("Contentless stubs", stubs, "Gemini produced no summary and no dialogue - typically 'not enough conversation in a supported language'. A meeting happened; nothing was captured.")
section("Account unresolved", unres, "A real prospect call, but nothing in the doc names the course - no title, no invitee emails. Resolvable only from HubSpot or the calendar. Blocks the HubSpot join.")
section("Low extraction confidence", lowc, "Extracted, but the source was too thin to support most fields.")
section("Customer calls not extracted", notdone, "In scope but no extraction record present.")

open(os.path.join(BASE, "gaps.md"), "w").write("\n".join(lines))
print(f"\ncalls.csv: {len(calls)} rows")
print(f"objections.csv: {nobj} rows")
print(f"gaps.md: {len(vids)} video_only, {len(shorts)} shortcut, {len(stubs)} stub, "
      f"{len(unres)} unresolved-account, {len(lowc)} low-confidence, {len(notdone)} unextracted")
if calls:
    print("\nobjection categories:", dict(Counter(
        o.get("category") for c in calls for o in (c.get("objections") or []))))
