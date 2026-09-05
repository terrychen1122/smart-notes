# Artifact contracts and commands

All helpers require Python 3.9+ and its standard library only. All times are seconds
(finite, nonnegative numbers) in normalized files. Input timestamp fields may also
use `MM:SS`, `HH:MM:SS`, or fractional clock values. Cue and section intervals are
half-open `[start, end)`; overlapping cues are permitted. Every pipeline output uses
`schema_version: 1`. Invalid data exits nonzero with `Error: ...`.

The helpers perform deterministic transformations. **Codex authors semantic sections,
candidate reasons, visual reviews, and notes**; the scripts do not infer their content.
`schemas/notes.schema.json` describes the authored notes format for editors and
external validators; runtime checks use the Python helpers without a schema package.

## Acquisition

`metadata.json` is a JSON object:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID_11",
  "title": "Observed video title",
  "channel": "Observed channel or Unknown",
  "duration": 120,
  "caption_source": "auto",
  "language": "en",
  "coverage": "partial",
  "description": "Observed description, if available",
  "chapters": [{"start": 0, "title": "Introduction"}],
  "warnings": ["Only the first minute of captions was accessible."]
}
```

Replace `VIDEO_ID_11` with the actual 11-character ID. Duration is the observed video
duration, not an estimate from the last transcript row. `title`, `channel`, `url`,
and positive `duration` are required. Caption source defaults to `unknown`; coverage
defaults to `unknown`. Allowed values are in SKILL.md/browser-workflow.md. Optional
metadata is preserved. Only mark coverage complete after checking extraction.

Supported caption inputs:

- `.json`: `[{"start": 0, "text": "..."}]` or `{"segments": [...]}`. Optional `end`
  or `duration` on each cue; `end` takes precedence. Text is literal Unicode.
- `.txt`: timestamp on its own line followed by text, or `00:00 Caption text`.
  Following lines belong to that cue until the next timestamp. Export the panel
  rows only, without UI labels or comments. Timestamp-looking mathematical text
  should use JSON to avoid ambiguity.
- `.srt` / `.vtt`: timed cues with multiline text. WebVTT cue settings, style/note
  blocks, voice tags, and inline timestamps are handled. Rolling caption overlaps
  are preserved, not aggressively deduplicated; the writer must avoid repeating them.

Exact duplicate cues are removed. Missing ends use the next distinct start, or
video duration for the last cue, and set `end_inferred: true`. These inferred bounds
do not prove speech continues through silence. Explicit intervals are never stretched.

```sh
python3 smart-notes/scripts/transcript.py output/lecture/raw.txt --metadata output/lecture/metadata.json --output output/lecture/transcript.json
```

The result has `video` (normalized metadata) and `segments` (objects with `id`,
`start`, `end`, `text`, `end_inferred`). Cue IDs remain stable for downstream files
only while the normalized transcript is unchanged.

## Semantic timeline

Codex writes `sections.json`, a chronological list:

```json
[
  {"id": "s1", "title": "Objective", "start": 0, "end": 40},
  {"id": "s2", "title": "Update rule", "start": 40, "end": 120}
]
```

Require unique nonempty IDs, positive intervals, no gaps or overlaps, and coverage
from zero through video duration. Represent known gaps/noninstructional material
explicitly; do not fabricate speech in them. Chapter boundaries can be revised.

```sh
python3 smart-notes/scripts/timeline.py output/lecture/transcript.json --sections output/lecture/sections.json --output output/lecture/timeline.json
```

`timeline.json` adds `sections`, each with `segment_ids` for all overlapping cues.
Join those IDs against the top-level `segments`. Cues crossing a boundary appear in
both sections as context. An empty `segment_ids` means there is no captured speech
for that interval; distinguish known silence from missing acquisition.

## Visual candidates and reviews

Codex writes `candidates.json`:

```json
[
  {"section_id": "s2", "timestamp": 52, "reason": "Inspect the diagram referenced when explaining the update direction."}
]
```

```sh
python3 smart-notes/scripts/frame_selector.py plan output/lecture/timeline.json --candidates output/lecture/candidates.json --output output/lecture/frame-plan.json
```

Use `--max-per-section 1` for quick mode and `2` for concepts. Empty lists are valid.
The plan stores the video URL, section bounds, and `frames` with IDs, requested times,
reasons, `seek_url`, and `status: pending`. These candidates are not selected evidence
until visually reviewed. Keep this file synchronized if the timeline is revised.

After browser capture and inspection, Codex writes `reviews.json`:

```json
[
  {
    "id": "frame-001",
    "decision": "keep",
    "actual_timestamp": 54,
    "image": "captures/frame-001.png",
    "visual_type": "diagram",
    "description": "Contour plot with the gradient normal to a level curve.",
    "reason": "The geometric direction is shown visually but not fully described in speech."
  }
]
```

For `reject` and `unavailable`, only `id`, `decision`, and `reason` are required.
Kept frames require all displayed fields; actual times must stay within the assigned
section. Images must be existing PNG/JPEG/WebP files and have matching file signatures.
This is a basic file check, not proof of image legibility; Codex must inspect them.
Image paths are relative to the reviews file, or absolute. The reviewed manifest
stores absolute paths for working use. Reviews can be incremental; rerun `review`
against the latest manifest to continue or revise decisions. Final rendering rejects
any remaining pending frame.

```sh
python3 smart-notes/scripts/frame_selector.py review output/lecture/frame-plan.json --reviews output/lecture/reviews.json --output output/lecture/frames.json
```

## Authored notes and rendering

Codex writes `notes.json`:

```json
{
  "mode": "notes",
  "overview": "A transformed synthesis grounded in the observed lecture.",
  "visual_status": "One diagram inspected and retained; other sections checked for useful visual candidates.",
  "sections": [
    {"id": "s1", "summary": "Section explanation."},
    {
      "id": "s2",
      "summary": "Section explanation with assumptions and intuition.",
      "equations": ["\\theta_{k+1}=\\theta_k-\\alpha\\nabla J(\\theta_k)"],
      "definitions": ["Explain each variable using evidence from this section."],
      "added_explanations": ["Clearly labeled supplementary reasoning."],
      "uncertainties": ["Specify the affected term and why its reading is uncertain."]
    }
  ],
  "key_concepts": ["Relationships across the lecture."],
  "review_points": ["A generated recall or practice question."],
  "warnings": []
}
```

Required: `mode`, `overview`, `visual_status`, and `sections`. Every timeline section
must have exactly one notes entry with its `id` and nonempty `summary`. Other optional
section fields are string lists: `key_ideas`, `definitions`, `equations`, `examples`,
`instructor_intuition`, `common_mistakes`, `added_explanations`, `uncertainties`.
Unknown fields are rejected to prevent silently losing authored content.

Prose fields support Markdown. Equations are bare LaTeX strings without `$$` wrappers;
JSON requires doubled backslashes. Explain symbols in definitions or prose. Examples
may use paragraphs, numbered steps, and fenced code blocks. Do not add generic
equations or examples merely to fill a category.

```sh
python3 smart-notes/scripts/render_notes.py output/lecture/timeline.json --frames output/lecture/frames.json --notes output/lecture/notes.json --output output/lecture/deliverable/notes.md
```

Rendering validates timeline alignment, exact notes coverage, reviewed frames, image
files, and matching video identity before writing. It carries source warnings into
the notes, marks partial coverage, embeds only kept images, and uses observed frame
times for links. It copies images to `notes.assets/` with relative links, so share
the Markdown and that directory together. Files are reused by content hash; reruns
do not delete older assets. The raw transcript is not included in the Markdown.

The synthetic fixture in `examples/` exercises the same commands entirely offline.
