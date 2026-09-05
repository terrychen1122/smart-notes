# Browser acquisition and frame capture

Read the installed Browser skill and its selected browser's documentation before
controlling the browser. Use its supported screenshot and file-export operations.
This reference describes observable UI steps, not a fixed DOM implementation.
If that capability is unavailable, request timestamped captions and, when needed,
user-provided screenshots. Do not substitute an undocumented network endpoint.

## Language confirmation, transcript, and metadata

Before acquisition, ask the user to confirm the desired note language beside the
video's own language. Once the source language is visible, state it explicitly and
ask whether the notes should remain in that language or include another language.
Record the source language in `metadata.language` and the confirmed note language in
`metadata.note_language`. If they differ, the final notes must contain both source
and translated text in the same Markdown and PDF deliverables.

1. Open the supplied watch URL. Confirm the title and channel of the requested
   video. For playlists, operate on the requested video unless the user asked for
   the playlist. Distinguish ads from the lecture player before recording time.
2. Inspect visible duration and expand the description (`…more` or its current
   localized equivalent). Record description text and creator chapters if present.
   Use a fresh accessibility/DOM snapshot to find controls; labels can change.
3. In the description/transcript area, find **Show transcript**. Open it and inspect
   the language menu. Select the requested language, favoring creator captions if
   available; record any **auto-generated** or translation label exactly in metadata.
   If no provenance is visible, record `caption_source: unknown`. Caption source
   values are `creator`, `auto`, `unknown`, and `user-provided`.
4. Keep timestamps visible. Extract only observed transcript rows as `{start, text}`
   (and `end` only if actually provided). Use supported DOM reads when available;
   otherwise copy the timestamped panel text. Scroll the transcript panel through
   its end and re-inspect: a virtualized panel may expose only visible rows. Merge
   scroll batches using exact timestamp-and-text matches, not text alone.
5. Check early, middle, and final coverage against the player duration and chapters.
   A late final cue does not prove that middle rows were captured. Record whether
   the full panel was traversed and any known missing intervals in `warnings`.
   If coverage cannot be established, set `coverage: partial` or `unknown`.
6. Save metadata and raw captions locally with the available file-writing tool.
   Preserve Unicode, mathematical symbols, language, and timestamps. Do not scrape
   comments, recommendations, account data, or hidden application stores.

If **Show transcript** is absent, inspect visible caption/language controls once.
If no usable captions are exposed, report the limitation and request an existing
SRT/VTT/transcript. A sign-in, consent, age, region, or unavailable-video block
should be handled according to the Browser skill. Stop after one supported retry
for transient failure; do not claim success or completeness when blocked.

## Seek, capture, and review

For each pending frame:

1. Use its `seek_url` (YouTube watch URL with `t=<seconds>s`) or a visible transcript
   timestamp/player seek control. Inspect the current page before interacting.
2. Let seeking finish. Confirm the displayed player position near the requested
   time; pause with the visible player control if playing. Record the actual
   displayed time. A URL parameter alone does not verify a successful seek.
3. If a slide is transitioning, seek a few seconds within the same section and
   verify again. If useful content lies in another section, revise the candidate
   plan rather than assigning the wrong section. Limit retries to two nearby
   positions for a candidate; then reject or mark unavailable with the reason.
4. Capture the player area using a supported element/region screenshot if
   available. The crop must be the complete visible video rectangle: include the
   full top, bottom, left, and right edges of the frame, but exclude browser chrome,
   the page title, recommendations, comments, transcript panels, and other page
   content. If only a page screenshot is available, crop it to the player bounds
   before saving and verify that no part of the video frame was cut off. Move the
   pointer away and dismiss player overlays using observed controls when possible.
   Save to the working directory with a stable filename, for example
   `captures/frame-001.png`. Never save an HTML/login page as an image.
5. Visually inspect the capture. Keep it only if legible and useful beyond speech.
   Describe the actual information, not the hoped-for content. Reject near-duplicate
   slides unless a changed equation or example step matters. Do not reject a frame
   merely because the speaker is visible: a clear exercise setup, gesture, posture,
   demonstration, or side-by-side comparison is valid lecture evidence. Reject a
   generic talking-head frame that adds no visual information.
6. Record a review entry. Allowed visual types: `slide`, `diagram`, `equation`,
   `chart`, `code`, `worked-example`, `demonstration`, `comparison`. Record
   rejected/unavailable candidates too.
   The helper resolves image paths relative to the reviews file. Do not use
   screenshots of the whole transcript as key frames.

When the browser can display but cannot export screenshots, describe that limitation
and mark the candidates unavailable. Complete transcript-grounded notes if the
transcript is accessible; do not leave broken image placeholders.

## Official UI references

- [YouTube: View video transcripts](https://support.google.com/youtube/answer/15930243?hl=en)
  describes opening **Show transcript** from the description and seeking by clicking rows.
- [YouTube: Use automatic captioning](https://support.google.com/youtube/answer/6373554?hl=en)
  explains possible recognition errors and caption availability limitations.

These references describe the feature; inspect the live page for current controls.
