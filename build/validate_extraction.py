#!/usr/bin/env python3
"""Enforce the extraction rules mechanically. Exit 1 on any hard failure."""
import json, glob, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cacheio import load_text

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = {"price","integration","staff_adoption","call_volume_doubt","ai_quality_doubt",
        "contract_terms","approval_authority","timing_seasonality","security_privacy","other"}
TACTICS = {"reference_customer","roi_math","feature_explanation","reframe","concession",
           "pricing_flex","defer_to_followup","acknowledge_only","deflect"}
MOVES = {"accepted","partially_accepted","deflected","re_raised_later","went_quiet","escalated"}
TRAJ = {"rising","flat","declining","v_shaped","insufficient_data"}

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

errors, warnings = [], []
files = sorted(glob.glob(os.path.join(BASE, "extracted", "*.json")))
for p in files:
    cid = os.path.basename(p)[:-5]
    E = lambda m: errors.append(f"{cid}: {m}")
    W = lambda m: warnings.append(f"{cid}: {m}")
    try:
        d = json.load(open(p))
    except Exception as e:
        E(f"unparseable JSON: {e}"); continue

    raw_src = load_text(BASE, cid)
    src = norm(raw_src) if raw_src else None
    if src is None:
        W("no cached source text - quotes unverifiable")

    # Speech can only be quoted from a source that actually contains dialogue.
    has_dialogue_src = False
    if raw_src:
        turns = max(len(re.findall(r"\n\*\*([A-Z][^*\n]{1,40}):\*\*", raw_src)),
                    len(re.findall(r"\n([A-Z][A-Za-z.'\- ]{1,40}):\s", raw_src)))
        has_dialogue_src = turns >= 30
    tier = d.get("content_tier")
    conf = d.get("extraction_confidence")
    has_dialogue = tier in ("rich", "moderate")

    # Rule 1: thin/stub sources cannot yield high confidence.
    if tier in ("thin", "stub") and conf == "high":
        E(f"content_tier={tier} but extraction_confidence=high")

    objs = d.get("objections") or []
    for i, o in enumerate(objs):
        tag = f"objections[{i}]"
        if o.get("category") and o["category"] not in CATS:
            E(f"{tag}.category '{o['category']}' not in enum")
        if o.get("response_tactic") and o["response_tactic"] not in TACTICS:
            E(f"{tag}.response_tactic '{o['response_tactic']}' not in enum")
        qs = o.get("quote_source")
        if o.get("trigger_quote") and qs not in ("verbatim_speech", "summary_narration"):
            E(f"{tag}.quote_source must be verbatim_speech or summary_narration, got {qs!r}")
        if qs == "verbatim_speech" and not has_dialogue_src:
            E(f"{tag}.quote_source=verbatim_speech but the source has no transcript")
        mv = o.get("prospect_next_move")
        if mv and mv not in MOVES:
            E(f"{tag}.prospect_next_move '{mv}' not in enum")
        # Rule 2: no dialogue in the source means no evidence of what happened next.
        if mv and tier == "stub":
            E(f"{tag}.prospect_next_move='{mv}' on a stub source - must be null")
        if mv and tier == "thin":
            W(f"{tag}.prospect_next_move='{mv}' on a thin source - verify dialogue exists")
        # Rule 4: quotes must be verbatim.
        q = o.get("trigger_quote")
        if q and src is not None and norm(q) and norm(q) not in src:
            E(f"{tag}.trigger_quote not found verbatim in source: {q[:60]!r}")
        if not q and mv:
            W(f"{tag} has prospect_next_move but no trigger_quote")

    # Rule 3: a sentiment score requires evidence; absent checkpoints are null.
    sent = d.get("sentiment") or {}
    for cp in ("open", "post_demo", "at_pricing", "close"):
        v = sent.get(cp)
        if v is None:
            continue
        if not isinstance(v, dict):
            E(f"sentiment.{cp} must be an object or null"); continue
        if v.get("score") is not None and not (v.get("evidence") or "").strip():
            E(f"sentiment.{cp} has score {v.get('score')} with no evidence")
        ev = v.get("evidence")
        if ev and src is not None:
            qs = re.findall(r'"([^"]{12,})"', ev)
            for qq in qs:
                if norm(qq) and norm(qq) not in src:
                    E(f"sentiment.{cp}.evidence quote not verbatim: {qq[:60]!r}")
    if sent.get("trajectory") and sent["trajectory"] not in TRAJ:
        E(f"sentiment.trajectory '{sent['trajectory']}' not in enum")
    if tier in ("thin","stub") and sent.get("trajectory") not in (None,"insufficient_data"):
        W(f"trajectory='{sent.get('trajectory')}' on a {tier} source")

    # Rule 6: no coaching language.
    blob = json.dumps(d).lower()
    for phrase in ("should have", "could have", "failed to", "missed opportunity", "rep should"):
        if phrase in blob:
            W(f"possible editorialising: {phrase!r}")

    # Null discipline.
    for k in ("account_name","current_solution","next_step_description"):
        if d.get(k) in ("unknown","N/A","n/a",""):
            W(f"{k} is {d.get(k)!r} - use null")

print(f"validated {len(files)} extraction(s): {len(errors)} error(s), {len(warnings)} warning(s)")
for e in errors:   print(f"  ERROR  {e}")
for w in warnings: print(f"  warn   {w}")
sys.exit(1 if errors else 0)
