# How to use smart-notes

smart-notes turns YouTube lectures and academic videos into timestamped Markdown
study notes, using captions and useful screenshots as evidence. It can preserve
equations, definitions, diagrams, worked examples, and review questions.

Codex runs the workflow and writes the notes. The included Python scripts organize
and validate the evidence; they do not independently watch or summarize a video.

## 1. Open the project

Open this project folder in Codex:

```text
/Users/xuchen/Developer/Github/smart-notes
```

The skill entry point is inside the project:

```text
smart-notes/SKILL.md
```

The repeated name is intentional: the outer folder is the project, and the inner
folder contains the reusable skill.

You need:

- Python 3.9 or newer for the helper scripts.
- Codex with access to the project files and the ability to run the scripts.
- For live videos: a working Browser capability that can read YouTube's transcript
  panel, seek the video, capture screenshots, and save them locally.

The Python helpers need no third-party packages or API key. The skill is stored
locally in this project and has not been installed globally; reference its file
path in your request.

## 2. Give Codex a video URL

Copy this prompt and replace `<YOUTUBE_URL>`:

```text
Use the skill at smart-notes/SKILL.md to create detailed study notes
for this lecture: <YOUTUBE_URL>

Preserve important equations, definitions, worked examples, and useful
slides or diagrams. Include timestamp links and flag uncertain captions.
Save the final Markdown and any images under output/my-lecture/deliverable/.
```

Choose a different output folder for each lecture. You do not need to manually
prepare JSON files or run the pipeline commands for normal use; ask Codex to handle
the complete workflow.

## 3. Choose a note style

Natural-language instructions are sufficient. The supported modes are:

| Mode | Use it for | Example request after the skill path and URL |
| --- | --- | --- |
| `notes` | Detailed study notes; the default | “Include definitions, intuition, equations, and examples.” |
| `detailed` | A thorough section-by-section summary | “Preserve the argument, assumptions, and intermediate reasoning.” |
| `exam-review` | Recall questions and practice | “Focus on worked problems, common mistakes, and review questions.” |
| `concepts` | Understanding relationships | “Explain the key concepts, prerequisites, and how they connect.” |
| `quick` | A short overview | “Give me the main ideas and a concise timestamped outline.” |

For example:

```text
Use smart-notes/SKILL.md in exam-review mode for <YOUTUBE_URL>.
Include the important equations, worked steps, and practice questions.
```

```text
Use smart-notes/SKILL.md in quick mode for <YOUTUBE_URL>.
Keep it concise and include links to the main sections.
```

You can also specify the output language, topics to emphasize, or whether to omit
screenshots. Review questions are generated study aids, not predictions about an exam.

## 4. What happens during a run

1. Codex records the video metadata and obtains timestamped captions.
2. The transcript helper normalizes the captions and flags inferred timing bounds.
3. Codex identifies semantic sections; the timeline helper aligns captions with them.
4. Codex proposes useful screenshot timestamps, usually up to three per section.
5. Codex seeks, captures, and inspects those frames, retaining only useful evidence.
6. Codex writes notes grounded in the transcript and retained frames.
7. The renderer checks the artifacts and creates Markdown with timestamp links.

Frames are not selected simply because a fixed interval has elapsed. A readable
equation or diagram can be useful; a duplicate slide or speaker-only shot may be
rejected. A run can legitimately finish with no retained frames.

## 5. Open and share the result

For the first example prompt, expect:

```text
output/my-lecture/deliverable/
├── notes.md
└── notes.assets/   # Created only when screenshots are retained
```

Open `notes.md` in a Markdown viewer. A viewer with LaTeX math support will display
equations more clearly. Timestamp links open the corresponding point on YouTube.

Keep `notes.md` and `notes.assets/` together when moving or sharing the result.
Images use relative links. Working files such as transcripts, timeline JSON, and
review records may also be saved under the lecture's output folder; they are not
needed to read the final Markdown.

Check the evidence limitations near the top of the notes. They indicate issues
such as partial captions, uncertain terminology, or unavailable screenshots.

## 6. Use saved captions instead of live acquisition

Supported inputs are timestamped `.txt`, `.srt`, `.vtt`, and segment `.json` files.
Place your captions in the project, for example `output/my-lecture/raw.vtt`, then ask:

```text
Use smart-notes/SKILL.md to create study notes from
output/my-lecture/raw.vtt.

Source URL: <YOUTUBE_URL>
Title: <LECTURE_TITLE>
Channel: <CHANNEL_NAME>
Video duration: <DURATION_IN_SECONDS>
Caption source: <creator, auto, unknown, or user-provided>
Caption language: <LANGUAGE>
Coverage: <complete, partial, or unknown>

Make this transcript-only. State that visuals were not inspected.
Save the result under output/my-lecture/deliverable/.
```

Use the observed video duration rather than estimating it from the last caption.
Mark coverage `complete` only when the full transcript is present. If you also
provide screenshots, include each image's playback timestamp and ask Codex to
inspect them before using them as evidence.

## 7. Try the offline demo

The bundled demo uses invented gradient-descent captions. It exercises the local
pipeline without a browser, video download, or model API call. Its notes are already
authored, and its screenshot candidate is explicitly marked unavailable.

Run these commands from the project root, in order:

```sh
python3 smart-notes/scripts/transcript.py smart-notes/examples/transcript.vtt --metadata smart-notes/examples/metadata.json --output output/demo/transcript.json
python3 smart-notes/scripts/timeline.py output/demo/transcript.json --sections smart-notes/examples/sections.json --output output/demo/timeline.json
python3 smart-notes/scripts/frame_selector.py plan output/demo/timeline.json --candidates smart-notes/examples/candidates.json --output output/demo/frame-plan.json
python3 smart-notes/scripts/frame_selector.py review output/demo/frame-plan.json --reviews smart-notes/examples/reviews.json --output output/demo/frames.json
python3 smart-notes/scripts/render_notes.py output/demo/timeline.json --frames output/demo/frames.json --notes smart-notes/examples/notes.json --output output/demo/notes.md
```

Open `output/demo/notes.md`, or read the included
[sample output](smart-notes/examples/sample-output.md).

To run the offline tests:

```sh
python3 -m unittest discover -s tests -v
```

## 8. Troubleshooting and current limits

| Issue | What to do |
| --- | --- |
| Codex does not locate the skill | Include the full path: `/Users/xuchen/Developer/Github/smart-notes/smart-notes/SKILL.md`. |
| A command cannot find a script | Run it from the outer project folder, alongside `README.md`. |
| Browser connection fails | Supply saved captions and request transcript-only notes, or restore browser access before retrying. |
| YouTube has no accessible transcript | Provide an existing caption file. V1 does not transcribe audio. |
| Captions are incomplete or technically inaccurate | Ask for explicit coverage limitations and localized uncertainty; provide corrected evidence when available. |
| Rendering reports pending frames | Review each candidate as `keep`, `reject`, or `unavailable` before rendering. |
| A retained image is missing | Restore the capture file or revise its review, then render again. |
| Images disappear after sharing | Share the sibling `notes.assets/` folder as well as the Markdown file. |

Live YouTube capture has not yet been validated in this environment because browser
setup failed. The offline pipeline and its tests have passed. V1 does not include
automatic video downloading, OCR, perceptual frame-change detection, audio
transcription, or PDF/HTML/Notion export.

For custom pipeline work, see the
[artifact formats and commands](smart-notes/references/artifacts.md). For browser
acquisition details, see the
[browser workflow](smart-notes/references/browser-workflow.md).
