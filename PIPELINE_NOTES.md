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

   Fine as an ordering proxy; misleading in absolute terms. The 10-40 KB
   "moderate" band is only ~2-9 K chars (summary, no dialogue). Record true
   `char_count` during extraction and re-tier before any analysis depends on it.

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
