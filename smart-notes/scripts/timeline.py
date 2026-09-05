"""Align a Codex-authored semantic section plan to normalized transcript cues."""
import argparse

from common import read_json, require, run_cli, seconds, validate_timeline, write_json


def build_timeline(transcript, plan):
    require(isinstance(plan, list) and bool(plan), "Section plan must be a nonempty list")
    sections = []
    for section in plan:
        start, end = seconds(section["start"]), seconds(section["end"])
        sections.append({"id": section["id"], "title": section["title"], "start": start, "end": end,
                         "segment_ids": [c["id"] for c in transcript["segments"]
                                         if c["start"] < end and c["end"] > start]})
    result = dict(transcript, sections=sections)
    validate_timeline(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--sections", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build_timeline(read_json(args.transcript), read_json(args.sections))
    write_json(args.output, result)
    print(f"Aligned {len(result['sections'])} sections → {args.output}")


if __name__ == "__main__":
    run_cli(main)
