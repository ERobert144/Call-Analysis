#!/usr/bin/env python3
"""Roll triage/*.json into the real N: how many calls actually carry dialogue."""
import json, glob, csv, os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inv = {r["file_id"]: r for r in csv.DictReader(open(os.path.join(BASE, "inventory.csv")))}
recs = []
bad = []
for p in sorted(glob.glob(os.path.join(BASE, "triage", "*.json"))):
    try:
        d = json.load(open(p))
        if not d.get("file_id"):
            d["file_id"] = os.path.basename(p)[:-5]
        recs.append(d)
    except Exception as e:
        bad.append((os.path.basename(p), str(e)[:60]))

expected = [r["file_id"] for r in inv.values()
            if r["mime_type"].endswith("document") and r["classification"] in ("customer_call", "unknown")]
missing = [f for f in expected if f not in {r["file_id"] for r in recs}]

print(f"triaged {len(recs)}/{len(expected)}"
      + (f"  MISSING {len(missing)}" if missing else "")
      + (f"  UNPARSEABLE {len(bad)}" if bad else ""))
for f, e in bad: print(f"  bad json: {f}: {e}")
for f in missing: print(f"  missing:  {f}  {inv[f]['file_name'][:56]}")
if not recs:
    raise SystemExit(0)

cust = [r for r in recs if r.get("is_customer_call")]
tr   = [r for r in cust if r.get("has_transcript")]
print(f"\ncustomer calls: {len(cust)} of {len(recs)} triaged docs")
print(f"  WITH transcript: {len(tr)}")
print(f"  summary only:    {len(cust)-len(tr)}")
print(f"  internal/other:  {len(recs)-len(cust)}")

def rep_of(r): return inv.get(r["file_id"], {}).get("rep", "?")
print("\ntranscript-bearing customer calls by rep")
for rep, n in sorted(Counter(rep_of(r) for r in tr).items()):
    print(f"  {rep:6} {n}")

print("\naccounts with a transcript call")
acc = defaultdict(int)
for r in tr: acc[r.get("account_name") or "(unresolved)"] += 1
for a, n in sorted(acc.items(), key=lambda kv: (-kv[1], kv[0])):
    print(f"  {a:34} {n}")

newly = [r for r in cust
         if inv.get(r["file_id"], {}).get("classification") == "unknown"]
print(f"\npromoted from 'unknown' to customer_call: {len(newly)}")
for r in sorted(newly, key=lambda r: -(r.get("char_count") or 0)):
    print(f"  {rep_of(r):6} {(r.get('account_name') or '(unresolved)'):26} "
          f"{r.get('char_count') or 0:>6}ch  tr={'Y' if r.get('has_transcript') else 'n'}  "
          f"{inv[r['file_id']]['file_name'][:44]}")

tot_obj = sum(1 for _ in tr) * 3
print(f"\nrough objection ceiling: {len(tr)} transcript calls x ~3 = ~{tot_obj} objections")

with open(os.path.join(BASE, "triage_summary.csv"), "w", newline="") as fh:
    cols = ["file_id","rep","file_name","account_name","account_source","is_customer_call",
            "has_transcript","char_count","transcript_chars","transcript_turns",
            "transcript_duration","has_screenshots","confidence","call_type_note"]
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in sorted(recs, key=lambda r: (rep_of(r), -(r.get("char_count") or 0))):
        row = {c: r.get(c, "") for c in cols}
        row["rep"] = rep_of(r)
        row["file_name"] = inv.get(r["file_id"], {}).get("file_name", "")
        w.writerow(row)
print("\nwrote triage_summary.csv")
