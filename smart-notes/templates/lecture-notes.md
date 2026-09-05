# {{title}}

Source, channel, duration, and only the reader-useful caption or coverage note.

If the requested note language differs from the video language, place the original
language first and the translation directly below it in every learner-facing block.
State the language pair once in the metadata/header; avoid repeating language labels
before every block when the order is already clear.

## Overview

In 1–2 paragraphs, state what the lecture teaches, how the main ideas connect,
and the central takeaway. If bilingual output is requested, provide both versions
in the same overview. Do not turn this into a transcript or capture report.

## {{section number}}. {{section title}}

Linked start–end timestamps.

Explain the teaching point concisely, then include only supported definitions,
equations (with variables explained), worked steps, or common mistakes that help a
learner. Embed retained player-only key frames at their actual timestamps with
short explanatory captions. Label added explanations and local uncertainty locally;
omit internal capture history and rejected-frame details.

## Key concepts

Synthesize relationships across the sections without merely repeating the outline.

## Review points

Recall questions and practice prompts grounded in the lecture; identify these as
generated study aids. For exam-review mode, prioritize worked reasoning and pitfalls.

## Timeline

Link every semantic section to the video.

Use this as writing guidance for notes.json; render_notes.py supplies the layout.
Omit empty or unsupported categories, and honor the user's requested structure.
