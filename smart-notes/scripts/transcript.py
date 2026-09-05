"""Normalize saved captions; acquisition is performed by the browser workflow."""
import argparse
import html
import re
from pathlib import Path

from common import nonempty, read_json, require, run_cli, seconds, validate_video, video_url, write_json

TIME = r"\d+:\d{2}(?::\d{2})?(?:[.,]\d+)?"


def clean_caption(text):
    # Remove WebVTT markup before decoding entities (so &lt;x&gt; is preserved).
    text = re.sub(r"</?(?:c|v|lang|b|i|u|ruby|rt)(?=[\s.>/])[^>]*>", "", text)
    text = re.sub(r"<" + TIME + r">", "", text)
    return " ".join(html.unescape(text).split())


def parse_captions(raw, suffix):
    raw = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if suffix == ".json":
        import json
        parsed = json.loads(raw)
        result = parsed.get("segments") if isinstance(parsed, dict) else parsed
        require(isinstance(result, list), "JSON input must be a segment list or {segments: [...]} ")
        return result
    if suffix in (".srt", ".vtt") or "-->" in raw:
        result = []
        for block in re.split(r"\n\s*\n", raw.strip()):
            if re.match(r"^(?:NOTE|STYLE|REGION)(?:\s|$)", block):
                continue
            lines = block.splitlines()
            timing_indices = [i for i, line in enumerate(lines) if "-->" in line]
            if not timing_indices:
                require(not block.strip() or block.startswith("WEBVTT"), "Caption block has no timing line")
                continue
            require(len(timing_indices) == 1, "Caption cues must be separated by blank lines")
            index = timing_indices[0]
            match = re.fullmatch(r"\s*(" + TIME + r")\s+-->\s+(" + TIME + r")(?:\s+.*)?", lines[index])
            require(match is not None, "Malformed caption timing: " + lines[index])
            text = clean_caption(" ".join(lines[index + 1:]))
            if text:
                result.append({"start": seconds(match[1]), "end": seconds(match[2]), "text": text})
        return result
    result, current = [], None
    for line in raw.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"\s*(" + TIME + r")(?:\s+(.*))?\s*", line)
        if match:
            current = {"start": seconds(match[1]), "text": (match[2] or "").strip()}
            result.append(current)
        else:
            require(current is not None, "Text before first timestamp; export only transcript rows")
            current["text"] += " " + line.strip()
    return result


def normalize(raw_segments, metadata):
    video = dict(metadata)
    video.setdefault("coverage", "unknown")
    video.setdefault("caption_source", "unknown")
    video.setdefault("warnings", [])
    validate_video(video)
    video["url"] = video_url(video["url"])
    video["duration"] = seconds(video["duration"])
    require(bool(raw_segments), "No transcript available; nothing to normalize")
    cleaned, seen = [], set()
    for cue in raw_segments:
        require(isinstance(cue, dict), "Each transcript cue must be an object")
        text = " ".join(nonempty(cue.get("text"), "caption text").split())
        start = seconds(cue["start"])
        end = seconds(cue["end"]) if cue.get("end") is not None else None
        if end is None and cue.get("duration") is not None:
            end = start + seconds(cue["duration"])
        require(start < video["duration"], "Cue starts at or beyond video duration")
        if end is not None:
            require(start < end <= video["duration"], "Cue ends outside its valid interval")
        key = (start, end, text)
        if key not in seen:
            cleaned.append({"start": start, "end": end, "text": text})
            seen.add(key)
    cleaned.sort(key=lambda c: c["start"])
    starts = sorted({cue["start"] for cue in cleaned})
    next_start = dict(zip(starts, starts[1:] + [video["duration"]]))
    for index, cue in enumerate(cleaned):
        cue["id"] = f"cue-{index + 1:04d}"
        cue["end_inferred"] = cue["end"] is None
        if cue["end"] is None:
            cue["end"] = next_start[cue["start"]]
    warnings = list(video["warnings"])
    if any(c["end_inferred"] for c in cleaned):
        warnings.append("Missing cue ends were inferred from the next distinct start or video duration; these are alignment bounds, not verified speech durations.")
    if video["caption_source"] == "auto":
        warnings.append("Automatic captions may misrecognize terminology and equations; check affected passages against visuals.")
    video["warnings"] = list(dict.fromkeys(warnings))
    return {"schema_version": 1, "video": video, "segments": cleaned}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Saved .txt, .srt, .vtt, or segment .json")
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = Path(args.input)
    data = normalize(parse_captions(path.read_text(encoding="utf-8"), path.suffix.lower()), read_json(args.metadata))
    write_json(args.output, data)
    print(f"Normalized {len(data['segments'])} cues → {args.output}")


if __name__ == "__main__":
    run_cli(main)
