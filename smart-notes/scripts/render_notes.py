"""Render Codex-authored study notes and reviewed images as portable Markdown."""
import argparse
import hashlib
import re
import shutil
from pathlib import Path
from urllib.parse import quote

from common import image_file, nonempty, read_json, require, run_cli, seek_url, stamp, strings, validate_timeline
from frame_selector import validate_manifest

MODES = ("notes", "detailed", "exam-review", "concepts", "quick")
FIELDS = {
    "key_ideas": "Key ideas",
    "definitions": "Definitions",
    "equations": "Important equations",
    "examples": "Worked examples",
    "instructor_intuition": "Instructor's intuition",
    "common_mistakes": "Common mistakes",
    "added_explanations": "Added explanations (not attributed to the speaker)",
    "uncertainties": "Uncertainties",
}


def escape(text):
    text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_\[\]])", r"\\\1", " ".join(text.split()))


def validate_notes(notes, timeline):
    require(isinstance(notes, dict), "Notes must be an object")
    require(not (set(notes) - {"mode", "overview", "visual_status", "sections", "key_concepts", "review_points", "warnings"}),
            "Unknown notes field; see references/artifacts.md")
    require(notes.get("mode") in MODES, "Invalid notes mode")
    nonempty(notes.get("overview"), "notes.overview")
    nonempty(notes.get("visual_status"), "notes.visual_status")
    for field in ("key_concepts", "review_points", "warnings"):
        strings(notes.get(field, []), "notes." + field)
    require(isinstance(notes.get("sections"), list), "notes.sections must be a list")
    ids = set()
    for section in notes["sections"]:
        require(not (set(section) - {"id", "summary"} - set(FIELDS)), "Unknown notes section field")
        nonempty(section.get("id"), "notes section ID")
        require(section["id"] not in ids, "Duplicate notes section ID")
        ids.add(section["id"])
        nonempty(section.get("summary"), "section.summary")
        for field in FIELDS:
            strings(section.get(field, []), field)
    require(ids == {s["id"] for s in timeline["sections"]}, "Notes must cover exactly the timeline sections")


def render(timeline, manifest, notes, output):
    # Validate all inputs and retained files before creating the deliverable.
    validate_timeline(timeline)
    validate_manifest(manifest, timeline, final=True)
    validate_notes(notes, timeline)
    output = Path(output).resolve()
    require(output.suffix.lower() == ".md", "Output must be a .md file")
    asset_dir = output.parent / (output.stem + ".assets")
    copied, transfers = {}, []
    for frame in manifest["frames"]:
        if frame["status"] != "keep":
            continue
        source = image_file(frame["image"])
        # Content-derived filenames avoid overwriting a different capture on rerun.
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        destination = asset_dir / (digest + source.suffix.lower())
        require(source != output, "Output cannot overwrite a source image")
        transfers.append((source, destination))
        copied[frame["id"]] = quote(destination.relative_to(output.parent).as_posix(), safe="/")

    video = timeline["video"]
    lines = ["# " + escape(video["title"]), "",
             f"[Watch video]({video['url']}) · {escape(video['channel'])} · {stamp(video['duration'])}", "",
             f"Mode: {notes['mode']} · Captions: {escape(video['caption_source'])} · "
             f"Language: {escape(video.get('language', 'unknown'))} · Coverage: {video['coverage']}", "",
             "Visual inspection: " + notes["visual_status"], ""]
    warnings = list(video.get("warnings", [])) + notes.get("warnings", [])
    if video["coverage"] != "complete":
        warnings.insert(0, "Transcript coverage is " + video["coverage"] + "; these notes may omit unobserved material.")
    for frame in manifest["frames"]:
        if frame["status"] == "unavailable":
            warnings.append("Visual unavailable at " + stamp(frame["timestamp"]) + ": " + frame["review_reason"])
    if not copied:
        warnings.append("No key frames retained; the notes contain no screenshot evidence.")
    if warnings:
        lines += ["## Evidence limitations", ""]
        lines += ["- " + item for item in dict.fromkeys(warnings)] + [""]
    lines += ["## Overview", "", notes["overview"], ""]
    by_id = {s["id"]: s for s in notes["sections"]}
    for index, section in enumerate(timeline["sections"], 1):
        content = by_id[section["id"]]
        lines += [f"## {index}. {escape(section['title'])}", "",
                  f"[{stamp(section['start'])}–{stamp(section['end'])}]({seek_url(video['url'], section['start'])})",
                  "", content["summary"], ""]
        for field, heading in FIELDS.items():
            values = content.get(field, [])
            if values:
                lines += ["### " + heading, ""]
                if field == "equations":
                    for equation in values:
                        lines += ["$$", equation, "$$", ""]
                elif field == "examples":
                    for example in values:
                        lines += [example, ""]
                else:
                    for value in values:
                        lines.append("- " + value.replace("\n", "\n  "))
                    lines.append("")
        for frame in sorted(manifest["frames"], key=lambda f: f.get("actual_timestamp", f["timestamp"])):
            if frame["section_id"] == section["id"] and frame["status"] == "keep":
                caption = escape(frame["description"])
                lines += [f"![{caption}]({copied[frame['id']]})", "",
                          f"Key frame [{stamp(frame['actual_timestamp'])}]({seek_url(video['url'], frame['actual_timestamp'])})"
                          f" — {caption}", ""]
    for field, heading in (("key_concepts", "Key concepts"), ("review_points", "Review points (generated study aids)")):
        if notes.get(field):
            lines += ["## " + heading, ""]
            lines += ["- " + value.replace("\n", "\n  ") for value in notes[field]] + [""]
    lines += ["## Timeline", ""]
    lines += [f"- [{stamp(s['start'])}]({seek_url(video['url'], s['start'])}) — {escape(s['title'])}"
              for s in timeline["sections"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    for source, destination in transfers:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source != destination:
            shutil.copyfile(source, destination)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline")
    parser.add_argument("--frames", required=True, help="Reviewed frame manifest, including an empty plan if no visuals")
    parser.add_argument("--notes", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = render(read_json(args.timeline), read_json(args.frames), read_json(args.notes), args.output)
    print("Rendered " + str(output))


if __name__ == "__main__":
    run_cli(main)
