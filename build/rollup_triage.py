#!/usr/bin/env python3
"""Roll triage/*.json into the real N, and re-verify the workers' transcript calls."""
import json, glob, csv, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import analyse, load

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inv = {r["file_id"]: r for r in csv.DictReader(open(os.path.join(BASE, "inventory.csv")))}

# External, but not a golf course being sold to.
NOT_PROSPECT = {"tenfore", "pitch crm", "pitchcrm"}

recs, bad = [], []
for p in sorted(glob.glob(os.path.join(BASE, "triage", "*.json"))):
    try:
        d = json.load(open(p))
        d.setdefault("file_id", os.path.basename(p)[:-5])
        recs.append(d)
    except Exception as e:
        bad.append((os.path.basename(p), str(e)[:60]))

expected = [f for f, r in inv.items()
            if r["mime_type"].endswith("document") and r["classification"] in ("customer_call", "unknown")]
seen = {r["file_id"] for r in recs}
missing = [f for f in expected if f not in seen]
rep_of = lambda r: inv.get(r["file_id"], {}).get("rep", "?")
name_of = lambda r: inv.get(r["file_id"], {}).get("file_name", "")

print(f"triaged {len(recs)}/{len(expected)}"
      + (f"   MISSING {len(missing)}" if missing else "")
      + (f"   UNPARSEABLE {len(bad)}" if bad else ""))
for f, e in bad: print(f"  bad json: {f}: {e}")
for f in missing: print(f"  missing:  {f}  {inv[f]['file_name'][:52]}")
if not recs: raise SystemExit(0)

# Independent re-check: workers judged has_transcript by hand after probe.py
# under-reported raw Meet exports. Re-run the fixed probe on anything cached.
disagree = []
for r in recs:
    cp = os.path.join(BASE, "cache", f"{r['file_id']}.json")
    if not os.path.exists(cp): continue
    try: a = analyse(load(cp))
    except Exception: continue
    r["_probe_transcript"], r["_probe_turns"] = a["has_transcript"], a["turns"]
    if bool(r.get("has_transcript")) != a["has_transcript"]:
        disagree.append((r["file_id"], bool(r.get("has_transcript")), a["has_transcript"], a["turns"]))
checked = sum(1 for r in recs if "_probe_transcript" in r)
print(f"\nre-verified {checked}/{len(recs)} against cached text; {len(disagree)} disagreement(s)")
for fid, w, p, t in disagree:
    print(f"  {fid}  worker={w} probe={p} turns={t}  {inv.get(fid,{}).get('file_name','')[:44]}")

def is_prospect(r):
    if r.get("is_customer_call") is not True: return False
    return (r.get("account_name") or "").strip().lower() not in NOT_PROSPECT

prospect = [r for r in recs if is_prospect(r)]
tr = [r for r in prospect if r.get("has_transcript")]
undecided = [r for r in recs if r.get("is_customer_call") is None]

print(f"\n{'PROSPECT CALLS':<28}{len(prospect)}")
print(f"{'  with real dialogue':<28}{len(tr)}")
print(f"{'  summary only':<28}{len(prospect)-len(tr)}")
print(f"{'internal / vendor / other':<28}{len(recs)-len(prospect)-len(undecided)}")
print(f"{'undecided (no evidence)':<28}{len(undecided)}")

print("\ntranscript-bearing prospect calls by rep")
for rep, n in sorted(Counter(rep_of(r) for r in tr).items()): print(f"  {rep:6} {n}")

print("\naccounts with at least one transcript call")
acc = defaultdict(list)
for r in tr: acc[r.get("account_name") or "(unresolved)"].append(r)
for a, v in sorted(acc.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    ch = sum(x.get("transcript_chars") or 0 for x in v)
    print(f"  {a:32} {len(v)} call(s)  {ch:>7} transcript chars")

promoted = [r for r in prospect if inv.get(r["file_id"], {}).get("classification") == "unknown"]
demoted  = [r for r in recs if inv.get(r["file_id"], {}).get("classification") == "customer_call"
            and not is_prospect(r)]
print(f"\npromoted unknown -> prospect: {len(promoted)}")
for r in sorted(promoted, key=lambda r: -(r.get("char_count") or 0)):
    print(f"  {rep_of(r):6} {(r.get('account_name') or '(unresolved)'):24} {r.get('char_count') or 0:>6}ch "
          f"tr={'Y' if r.get('has_transcript') else 'n'}  {name_of(r)[:40]}")
print(f"\ndemoted customer_call -> not a prospect call: {len(demoted)}")
for r in demoted:
    print(f"  {rep_of(r):6} {(r.get('account_name') or '(none)'):24} {name_of(r)[:46]}")

print(f"\nobjection ceiling: {len(tr)} transcript calls x ~3 = ~{len(tr)*3} objections")

with open(os.path.join(BASE, "triage_summary.csv"), "w", newline="") as fh:
    cols = ["file_id","rep","file_name","account_name","account_source","is_customer_call",
            "is_prospect","has_transcript","probe_transcript","char_count","transcript_chars",
            "transcript_turns","transcript_duration","has_screenshots","confidence","call_type_note"]
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in sorted(recs, key=lambda r: (rep_of(r), -(r.get("char_count") or 0))):
        row = {c: r.get(c, "") for c in cols}
        row.update(rep=rep_of(r), file_name=name_of(r), is_prospect=is_prospect(r),
                   probe_transcript=r.get("_probe_transcript", ""))
        w.writerow(row)
print("\nwrote triage_summary.csv")
