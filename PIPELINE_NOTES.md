# CourseRev Sales Call Extraction — Working Notes

Verified facts about the source data. Re-verify before contradicting.

## Access

Google Drive MCP connector, authenticated to the CourseRev workspace.
No credentials file / gcloud / service account involved.

| Rep | Folder | Drive folder ID | Owner |
|---|---|---|---|
| Bo | Google Meet | `1j7rYgVWX4OvzNi2CcKDOKBsY7dzGo_uo` | boferrando@courserev.ai |
| Jason | Meet Recordings | `1MjL86O-69I-LPiaz33Cv025O4rLmHShn` | jason@courserev.ai |

Both list, recurse, and read.

## Phase 0 verification

Target file `1BPJko8wI1WqBvBHy9SAXMRRCM-VGk8f7_D0MPgntmpc`
("CourseRev + Laughlin Ranch - Chat - 2026/08/12 11:00 PDT - Notes by Gemini")

- **29,125 characters** (5,199 words)
- Drive `fileSize`: 129,972 bytes
- Summary + Decisions + Next steps + full verbatim transcript
- Ends cleanly at `Transcription ended after 00:20:42`
- Cross-checked via `read_file_content` (markdown) and `download_file_content`
  (HTML export); both agree.

## Gotchas discovered

1. **`fileSize` is NOT text length.** It is the Google Docs internal size, which
   runs 4.5-6.7x the actual character count, and the ratio is not constant:

   | File | Bytes | Chars | Ratio |
   |---|---|---|---|
   | Laughlin Ranch | 129,972 | 29,125 | 4.5x |
   | Tilden Park | 443,209 | 66,296 | 6.7x |

   **SUPERSEDED - see finding 11. `fileSize` does not even order correctly.**

2. **Subfolder name is not a reliable date.** Folder
   `145VkPFdFH5zme7v0MNibSjrlHcErX7DT` is named
   "Chat: CourseRev + Cedaredge Golf Course - 2026/09/01 10:00 PDT" but contains
   notes docs for BOTH 2026/09/01 and 2026/09/04. Key date off the doc title.

3. **Bo's folder mixes nested subfolders with loose root-level files.**
   Old Greenwood sits at the root; Tilden and Cedaredge are in subfolders.
   Recursion is required, but so is handling root-level files.

4. **One meeting can have multiple mp4s.** Jason's 2026/09/09 "Live Demo" has
   three recordings (201 MB / 112 MB / 10.7 MB) plus a 112,725-byte notes doc,
   so it is covered, not `video_only`. mp4 count != gap count.

5. **`read_file_content` clips ~8 chars of trailing Google boilerplate**
   ("...after it was cre" instead of "...after it was created."). Zero
   substantive loss; the transcript body is intact.

## Context architecture

MCP tool results land in the agent's context. Oversized results (roughly
>40-60 K chars) are spilled to disk by the harness and can then be processed
with jq/python without being loaded. Mid-size docs (~10-40 K chars) land
directly in context.

At ~50 calls this is ~850 K+ tokens of raw transcript, which does not fit one
context window. Preferred approach: one subagent per call, writing
`extracted/<file_id>.json` and returning a one-line confirmation.

## Layout

- `extracted/` — one JSON per call (Phase 2/3), idempotent by `file_id`
- `cache/` — local copies of fetched docs (gitignored)
- `logs/` — run logs

## Phase 1 results

129 rows in `inventory.csv` = 85 readable docs + 9 recordings + 35 unreadable
shortcuts. Built from Drive metadata only; no documents were opened.

| rep | classification | stub | thin | moderate | rich | total |
|---|---|---|---|---|---|---|
| Bo | customer_call | 0 | 7 | 9 | 3 | 19 |
| Bo | unknown | 0 | 1 | 1 | 0 | 2 |
| Bo | internal | - | - | - | - | 0 (35 shortcuts) |
| Jason | customer_call | 0 | 5 | 4 | 0 | 9 |
| Jason | unknown | 13 | 10 | 7 | 5 | 35 |
| Jason | internal | 0 | 2 | 14 | 4 | 20 |

28 customer calls across 20 accounts. 37 readable docs remain `unknown`.

### Further gotchas found in Phase 1

6. **Bo's recurring internal meetings are Drive shortcuts, not files.**
   All 35 return `{}` from `read_file_content` and carry no `fileSize`.
   Tiering them is impossible, hence `content_tier = shortcut_unreadable`
   (an addition to the spec's enum). The underlying docs ARE recoverable by
   title search - they live in other users' folders - as confirmed for
   TenFore (`1H_esx8w...`) and the Summit doc (`1XXCqQ91...`).

7. **`- Transcript` is not reliably a 1,024-byte stub.** Only 3 of 9 are.
   The other 6 run 7,639-22,920 bytes and carry real content. Tier on size,
   never on the title.

8. **No video-only gaps.** Every one of the 9 recordings has a notes doc from
   the same rep on the same day. Two of those pairings are inferred rather
   than certain: "Stonebridge Meadows Meeting Notes" and "Meeting Notes with
   Deerhurst" carry no date in the title and were matched to the recordings
   of 2026-08-06 and 2026-07-02 via Drive `createdTime`.

9. **Three docs carry no date in the title** and were backfilled from
   `createdTime` (see `DATE_BACKFILL` in `build/build_inventory.py`):
   Stonebridge Meadows, Deerhurst, Scott Lake.

10. **The data's centre of mass is in `unknown`, not `customer_call`.**
    The five largest readable docs in the corpus are all Jason files titled
    "Meeting started ..." or "Live Demo ..." (112 KB - 285 KB). Named
    customer calls skew thin/moderate. Resolving the unknowns is where the
    transcript volume actually is.

## Finding 11 - `fileSize` is not a content proxy at all (supersedes 1)

Measured by opening the documents:

| doc | bytes | tier by bytes | actual chars | transcript? |
|---|---|---|---|---|
| Old Greenwood | 31,843 | moderate | 55,382 | YES - 49:40, 322 turns |
| Tilden Park | 443,209 | rich | 66,296 | YES - 53:31, 355 turns |
| Laughlin Ranch | 129,972 | rich | 31,744 | YES - 20:42 |
| Bristol Ridge | 20,285 | moderate | ~30,000 | YES - 22:21 |
| Meeting started 2026/08/11 09:31 | 285,331 | rich | ~7,000 | NO |

A 32 KB doc holds a 49-minute verbatim transcript - more text than the 443 KB
file. A 285 KB doc holds no dialogue at all.

Cause: Gemini embeds **screenshots** in the notes. Images dominate `fileSize`
and contribute no text. Docs whose Details section contains the line "Did the
screenshots in this section make your notes better or worse?" carry images;
those without it do not.

Consequences:
- The `content_tier` column in `inventory.csv` is unreliable. Do not build on it.
- Transcript presence can only be established by opening the document and
  looking for a top-level "Transcript" heading. `build/probe.py` does this.
- The transcript-bearing population is plausibly 15-25 calls rather than the 2
  that the byte-based tiers implied.

## Corpus-size ceiling on the Phase 4 objection analysis

Best case ~20 transcript calls x ~3 objections = ~60 objections. The schema has
10 objection categories x 9 response tactics = 90 cells; at n>=5 per cell that
needs ~450 observations. Roughly 7x short, so the category x tactic x outcome
cross-tab cannot be populated at any extraction quality. Transcribing the mp4s
adds ~3-4 calls (every recording already has a same-day notes doc), which does
not change the order of magnitude.

Survives at this N: objection frequency (descriptive), call_path shapes,
unanswered-question collation, and a collapsed
top-3-categories x resolved-in-call table (~15 obs/category).
Does not survive: tactic-to-outcome correlation, sentiment-trajectory patterns.

## Character counts are rendering-dependent (about 3%)

The same document measures differently depending on how it is exported:

| rendering | Laughlin Ranch |
|---|---|
| HTML export, tags stripped (Phase 0) | 29,125 |
| HTML export via probe.py | 31,744 |
| Docs markdown export (`read_file_content`) | 32,655 |

Markdown escapes and expanded mailto/anchor URLs account for the spread; the
content is identical. All `triage/*.json` counts come from the markdown export,
so they are internally consistent and comparable to each other. Do not mix them
with the Phase 0 HTML figure.
