# Phase 2/3 extraction spec

One JSON per call in `extracted/<file_id>.json`. Skip any file_id already present.

## Before extracting

Save the document's plain text to `cache/<file_id>.txt`. Every verbatim quote you
write is checked against that file by `build/validate_extraction.py`. A quote that
does not appear in the source is a hard failure, so quote by copying, never by
reconstructing from memory.

## Schema

```json
{
  "call_id": "", "file_name": "", "doc_url": "", "rep": "Bo | Jason",
  "date": "YYYY-MM-DD", "account_name": "", "account_source": "title | body | unresolved",
  "attendees": [{"name": "", "org": "prospect | courserev", "role": ""}],
  "prospect_seniority": "owner | GM | director_of_golf | head_pro | ops | board | unknown",
  "meeting_type": "discovery | demo | pricing | follow_up | negotiation | other",
  "content_tier": "rich | moderate | thin | stub",
  "pain_points": [], "current_solution": "", "demo_happened": true,
  "features_demoed": [], "prospect_questions": [], "unanswered_questions": [],
  "objections": [{
    "trigger_quote": "", "category": "price | integration | staff_adoption | call_volume_doubt | ai_quality_doubt | contract_terms | approval_authority | timing_seasonality | security_privacy | other",
    "quote_source": "verbatim_speech | summary_narration",
    "rep_response_summary": "",
    "response_tactic": "reference_customer | roi_math | feature_explanation | reframe | concession | pricing_flex | defer_to_followup | acknowledge_only | deflect",
    "prospect_next_move": "accepted | partially_accepted | deflected | re_raised_later | went_quiet | escalated",
    "resolved_in_call": true
  }],
  "sentiment": {
    "open":       {"score": 3, "evidence": "", "evidence_source": "verbatim_speech | summary_narration"},
    "post_demo":  {"score": 3, "evidence": "", "evidence_source": "verbatim_speech | summary_narration"},
    "at_pricing": {"score": 3, "evidence": "", "evidence_source": "verbatim_speech | summary_narration"},
    "close":      {"score": 3, "evidence": "", "evidence_source": "verbatim_speech | summary_narration"},
    "trajectory": "rising | flat | declining | v_shaped | insufficient_data"
  },
  "call_path": [], "pivot_points": [{"at_stage": "", "what_changed": "", "caused_by": ""}],
  "next_step_secured": true, "next_step_has_date": false, "next_step_description": "",
  "buying_signals": [], "stalls": [], "rep_commitments": [],
  "extraction_confidence": "high | medium | low", "confidence_notes": ""
}
```

## Rules - these matter more than filling the schema

1. **Never infer what is not there.** A summary-only doc with no dialogue means
   most fields are null and `extraction_confidence` is "low". A plausible-sounding
   invented objection is worse than an empty field.
2. **`prospect_next_move` is the most important field.** It is the only evidence
   that a response actually worked. If the source does not show what the prospect
   said next, it is **null**. Never infer it from tone. On a doc with no
   transcript it is almost always null - the validator enforces this.
3. **Every sentiment score needs evidence** - a short quote or a specific
   observation. A score with empty evidence is invalid. If a checkpoint never
   happened (pricing never came up), the whole checkpoint is null, NOT a
   middle score of 3.
4. **Quote sparingly and verbatim, and say what kind of quote it is.**
   Short quotes, for evidence only. Never paraphrase into quote marks.
   `quote_source` distinguishes two very different things:
   - `verbatim_speech` - the prospect's own words, lifted from a transcript.
   - `summary_narration` - Gemini's third-person description of the prospect's
     concern ("Taylor Johnson raised concerns about..."). Real evidence, but it
     is the notetaker's paraphrase, not speech.
   A doc with no Transcript section can only ever yield `summary_narration`.
   Sentiment checkpoints carry the same distinction in `evidence_source`.
   Put it in that field - never inline a tag into the evidence text itself,
   which corrupts the quote. Treating narration as speech would
   let Phase 4 quote a prospect saying something they never said.
5. **Zero objections is a real finding.** Do not manufacture one to fill the array.
6. **Do not editorialise about rep performance.** No "the rep should have...".
   Extraction only; evaluation happens later against actual outcomes.
7. `content_tier` comes from the triage record's real character count, not
   from Drive's fileSize.
8. **Never take the demo course as `account_name`.** Reps place a live call to a
   real existing client during the demo - Highland Creek, Tradition Golf Club and
   Greenway Pines all appear this way. That course is the demo target, not the
   prospect. The prospect is whoever the rep is talking TO. If the only course
   named in the doc is the one being dialled, `account_name` is null and
   `account_source` is "unresolved".
9. **A partner or vendor is not a prospect.** TenFore (golf software) and Pitch
   CRM are external but are not golf courses being sold to. Set
   `meeting_type: "other"` and say so in `confidence_notes`; do not model them as
   prospect calls.
10. **A scheduled call is not a held call.** At least one doc is a prospect
   no-show where the recorded audio is two CourseRev people talking. The title
   names an account; the call never happened. `demo_happened: false`, zero
   objections, and say so in `confidence_notes`.

## Null discipline

Use JSON `null`, not `""`, `0`, `"unknown"` or `"N/A"`, for anything the source
does not support. Empty arrays are fine where the thing genuinely did not occur.
