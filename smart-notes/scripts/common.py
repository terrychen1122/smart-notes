"""Shared validation and file utilities; standard library only."""
import json
import math
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


def require(condition, message):
    if not condition:
        raise ValueError(message)


def seconds(value):
    require(not isinstance(value, bool), "A timestamp cannot be a boolean")
    if isinstance(value, str) and ":" in value:
        require(re.fullmatch(r"\d+:\d{2}(?::\d{2})?(?:[.,]\d+)?", value) is not None,
                "Invalid timestamp: " + value)
        parts = [float(p) for p in value.replace(",", ".").split(":")]
        require(all(p < 60 for p in parts[1:]), "Invalid clock timestamp: " + value)
        result = 0.0
        for part in parts:
            result = result * 60 + part
    else:
        result = float(value)
    require(math.isfinite(result) and result >= 0, "Time must be finite and nonnegative")
    return result


def stamp(value):
    total = int(seconds(value))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}" if hours else f"{minutes:02}:{secs:02}"


def video_url(value):
    require(isinstance(value, str), "video.url must be a YouTube URL")
    parsed = urlparse(value)
    require(parsed.scheme in ("http", "https"), "video.url must use HTTP(S)")
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        video_id = parsed.path.strip("/")
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.fullmatch(r"/(?:shorts|embed|live)/([\w-]+)/*", parsed.path)
            video_id = match.group(1) if match else ""
    else:
        raise ValueError("Expected a YouTube video URL")
    require(re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) is not None,
            "Expected an 11-character YouTube video ID")
    return "https://www.youtube.com/watch?" + urlencode({"v": video_id})


def seek_url(url, time):
    return video_url(url) + "&t=" + str(int(seconds(time))) + "s"


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " must be nonempty text")
    return value.strip()


def strings(value, label):
    require(isinstance(value, list), label + " must be a list")
    for item in value:
        nonempty(item, label + " item")
    return value


def read_json(filename):
    return json.loads(Path(filename).read_text(encoding="utf-8"),
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError("Invalid JSON number: " + v)))


def write_json(filename, value):
    destination = Path(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def validate_video(video):
    require(isinstance(video, dict), "video must be an object")
    nonempty(video.get("title"), "video.title")
    nonempty(video.get("channel"), "video.channel (use 'Unknown' if unavailable)")
    video_url(video.get("url"))
    require(seconds(video.get("duration")) > 0, "video.duration must be positive")
    require(video.get("caption_source") in ("creator", "auto", "unknown", "user-provided"),
            "Invalid caption_source")
    require(video.get("coverage") in ("complete", "partial", "unknown"), "Invalid coverage")
    strings(video.get("warnings", []), "video.warnings")


def validate_timeline(data):
    require(isinstance(data, dict) and data.get("schema_version") == 1, "Expected schema_version 1")
    validate_video(data["video"])
    duration = seconds(data["video"]["duration"])
    segments = data["segments"]
    require(isinstance(segments, list) and bool(segments), "Transcript is empty")
    ids = set()
    previous = -1.0
    for cue in segments:
        nonempty(cue.get("id"), "segment.id")
        require(cue["id"] not in ids, "Duplicate segment ID")
        ids.add(cue["id"])
        start, end = seconds(cue["start"]), seconds(cue["end"])
        require(previous <= start < end <= duration, "Invalid or unsorted cue interval")
        previous = start
        nonempty(cue.get("text"), "segment.text")
    sections = data["sections"]
    require(isinstance(sections, list) and bool(sections), "Sections are required")
    section_ids, previous_end = set(), 0.0
    for section in sections:
        nonempty(section.get("id"), "section.id")
        nonempty(section.get("title"), "section.title")
        require(section["id"] not in section_ids, "Duplicate section ID")
        section_ids.add(section["id"])
        start, end = seconds(section["start"]), seconds(section["end"])
        require(abs(start - previous_end) < 0.001 and start < end <= duration,
                "Sections must be contiguous, ordered, and within the video")
        expected = [c["id"] for c in segments if c["start"] < end and c["end"] > start]
        require(section.get("segment_ids") == expected, "Incorrect section-to-transcript mapping")
        previous_end = end
    require(abs(previous_end - duration) < 0.001, "Sections must cover the full video duration")


def image_file(filename):
    path = Path(filename).resolve()
    require(path.is_file(), "Missing image: " + str(path))
    with path.open("rb") as handle:
        header = handle.read(12)
    valid = ((path.suffix.lower() == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n")) or
             (path.suffix.lower() in (".jpg", ".jpeg") and header.startswith(b"\xff\xd8\xff")) or
             (path.suffix.lower() == ".webp" and header[:4] == b"RIFF" and header[8:12] == b"WEBP"))
    require(valid, "Expected a PNG, JPEG, or WebP screenshot: " + str(path))
    return path


def run_cli(main):
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError) as error:
        raise SystemExit("Error: " + str(error)) from None
