"""Validate semantic capture candidates and record human/model visual review."""
import argparse
from pathlib import Path

from common import image_file, nonempty, read_json, require, run_cli, seconds, seek_url, validate_timeline, write_json

VISUAL_TYPES = ("slide", "diagram", "equation", "chart", "code", "worked-example")


def plan_frames(timeline, candidates, maximum=3):
    validate_timeline(timeline)
    require(isinstance(candidates, list), "Candidates must be a list")
    require(1 <= maximum <= 3, "Maximum must be between 1 and 3")
    sections = {s["id"]: s for s in timeline["sections"]}
    counts, seen, frames = {}, set(), []
    for candidate in candidates:
        section_id = candidate["section_id"]
        require(section_id in sections, "Unknown candidate section: " + str(section_id))
        section = sections[section_id]
        time = seconds(candidate["timestamp"])
        require(section["start"] <= time < section["end"], "Candidate must lie within its section")
        require((section_id, time) not in seen, "Duplicate candidate timestamp")
        seen.add((section_id, time))
        counts[section_id] = counts.get(section_id, 0) + 1
        require(counts[section_id] <= maximum, "Too many candidates for " + section_id)
        reason = nonempty(candidate.get("reason"), "candidate.reason")
        frames.append({"id": f"frame-{len(frames) + 1:03d}", "section_id": section_id,
                       "timestamp": time, "reason": reason, "status": "pending",
                       "seek_url": seek_url(timeline["video"]["url"], time)})
    return {"schema_version": 1, "video_url": timeline["video"]["url"],
            "sections": [{k: s[k] for k in ("id", "start", "end")} for s in timeline["sections"]],
            "frames": frames}


def validate_manifest(manifest, timeline=None, final=False):
    require(manifest.get("schema_version") == 1, "Expected frame schema_version 1")
    sections = {s["id"]: s for s in manifest["sections"]}
    if timeline is not None:
        validate_timeline(timeline)
        require(manifest["video_url"] == timeline["video"]["url"], "Frames belong to a different video")
        require(manifest["sections"] == [{k: s[k] for k in ("id", "start", "end")}
                                         for s in timeline["sections"]], "Frame sections do not match timeline")
    seen = set()
    require(isinstance(manifest["frames"], list), "frames must be a list")
    for frame in manifest["frames"]:
        frame_id = nonempty(frame.get("id"), "frame.id")
        require(frame_id not in seen, "Duplicate frame ID")
        seen.add(frame_id)
        require(frame["section_id"] in sections, "Unknown frame section")
        section = sections[frame["section_id"]]
        require(section["start"] <= seconds(frame["timestamp"]) < section["end"], "Invalid candidate timestamp")
        require(frame["status"] in ("pending", "keep", "reject", "unavailable"), "Invalid frame status")
        if final:
            require(frame["status"] != "pending", "Review all frame candidates before rendering")
        if frame["status"] != "pending":
            nonempty(frame.get("review_reason"), "frame.review_reason")
        if frame["status"] == "keep":
            require(section["start"] <= seconds(frame["actual_timestamp"]) < section["end"],
                    "Actual frame timestamp must lie within its section")
            require(frame.get("visual_type") in VISUAL_TYPES, "Invalid visual_type")
            nonempty(frame.get("description"), "frame.description")
            image_file(frame["image"])


def review_frames(manifest, reviews, base_directory):
    validate_manifest(manifest)
    require(isinstance(reviews, list), "Reviews must be a list")
    frames = {frame["id"]: dict(frame) for frame in manifest["frames"]}
    seen = set()
    for review in reviews:
        frame_id = review["id"]
        require(frame_id in frames, "Review refers to an unknown frame")
        require(frame_id not in seen, "Duplicate review ID")
        seen.add(frame_id)
        status = review["decision"]
        require(status in ("keep", "reject", "unavailable"), "Invalid review decision")
        frame = frames[frame_id]
        for key in ("actual_timestamp", "image", "description", "visual_type"):
            frame.pop(key, None)
        frame.update(status=status, review_reason=nonempty(review.get("reason"), "review.reason"))
        if status == "keep":
            frame.update(actual_timestamp=seconds(review["actual_timestamp"]),
                         image=str(image_file(Path(base_directory) / review["image"])),
                         description=nonempty(review.get("description"), "review.description"),
                         visual_type=review["visual_type"])
    result = dict(manifest, frames=list(frames.values()))
    validate_manifest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("timeline")
    plan.add_argument("--candidates", required=True)
    plan.add_argument("--max-per-section", type=int, default=3)
    plan.add_argument("--output", required=True)
    review = commands.add_parser("review")
    review.add_argument("manifest")
    review.add_argument("--reviews", required=True)
    review.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        result = plan_frames(read_json(args.timeline), read_json(args.candidates), args.max_per_section)
    else:
        result = review_frames(read_json(args.manifest), read_json(args.reviews), Path(args.reviews).resolve().parent)
    write_json(args.output, result)
    print(f"Saved {len(result['frames'])} frame records → {args.output}")


if __name__ == "__main__":
    run_cli(main)
