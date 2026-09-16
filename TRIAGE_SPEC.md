# Triage spec

Goal: for each Gemini notes doc, find out what is actually IN it. This is a
cheap survey, not the Phase 2 extraction. Do not extract objections, sentiment
or call paths.

## Procedure per file_id

1. Skip if `triage/<file_id>.json` already exists.
2. Call `mcp__Google_Drive__read_file_content` with the file_id.
3. The result is `{"fileContent": "..."}`. If it is too large it is saved to a
   file instead and you are told the path - in that case do NOT try to read the
   whole thing into your context. Use
   `python3 build/probe.py '<path>::<label>'` for the mechanical counts, and
   `jq -r '.fileContent' <path> | head -c 4000` to read the summary header,
   which is where attendees and the account name live.
4. Write `triage/<file_id>.json` with exactly these fields.

## Fields

```json
{
  "file_id": "",
  "rep": "Bo | Jason",
  "char_count": 0,
  "has_transcript": true,
  "transcript_chars": 0,
  "transcript_turns": 0,
  "transcript_duration": "HH:MM:SS or null",
  "has_screenshots": true,
  "account_name": "the prospect organisation, or null",
  "account_source": "title | body | unresolved",
  "attendees": [{"name": "", "org": "prospect | courserev"}],
  "is_customer_call": true,
  "call_type_note": "one short line: what kind of meeting this is",
  "confidence": "high | medium | low"
}
```

## Rules

- `has_transcript` is true only if the doc contains a top-level "Transcript"
  heading followed by `**Speaker:**` dialogue lines. A "Transcript" LINK in the
  "Meeting records" header does not count - almost every doc has one.
- `has_screenshots` is true if the text contains "Did the screenshots in this
  section make your notes".
- `account_name` is the GOLF COURSE or prospect company. Never "CourseRev".
  Take it from the attendee email domains in the header when the title does not
  give it (e.g. `<mjackson@laughlinranch.com>` -> "Laughlin Ranch"). If you
  genuinely cannot tell, use null and `"account_source": "unresolved"`.
- `is_customer_call` false for CourseRev-internal meetings: team syncs, 1:1s,
  demo practice, huddles, strategy sessions, and calls where every attendee is
  @courserev.ai. Set `confidence: "low"` if you are unsure rather than guessing.
- An empty or near-empty doc ("a meeting happened") is still a valid record:
  `has_transcript: false`, low confidence, null account.
- Never invent an account name, an attendee, or a duration. null is correct.
