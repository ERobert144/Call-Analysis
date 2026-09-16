#!/usr/bin/env python3
"""Map free-text call_path stages onto a controlled vocabulary.

Phase 4 asks for the most common call_path sequences. Workers write stages as
prose ("Discovery: pro shop staffing problems, phone service pulled back..."),
which is useful detail but means no two calls ever share a sequence. Normalise
to tokens so sequences can actually be compared; keep the prose alongside.
"""
import re

# Order matters: first pattern that matches wins.
RULES = [
    ("next_step",   r"next step|follow.?up|wrap|agreement sent|contact detail|schedul"),
    ("onboarding",  r"onboard|implementation|go.?live|setup|kickoff|knowledge base"),
    ("objection",   r"objection|concern|push.?back|blocker|hesitat|ultimatum"),
    ("pricing",     r"pricing|price|cost|rate|fee|commercial|billing|per round"),
    ("demo",        r"demo|live call|roleplay|role.?play|screen ?share|walkthrough|showcase"),
    ("integration", r"integrat|tee sheet|platform|lightspeed|club caddy|access|troon|api"),
    ("discovery",   r"discovery|current|pain|problem|staffing|operation|volume|metric|context|how .* work"),
    ("rapport",     r"rapport|intro|small talk|greeting|pre.?call|weather|banter|waiting"),
]

def token(stage):
    s = (stage or "").lower()
    for tok, pat in RULES:
        if re.search(pat, s):
            return tok
    return "other"

def normalise(path):
    """Tokenise, then collapse immediate repeats (discovery x3 -> discovery)."""
    out = []
    for st in path or []:
        t = token(st)
        if not out or out[-1] != t:
            out.append(t)
    return out
