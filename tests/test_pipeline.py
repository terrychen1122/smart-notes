"""Observable pipeline contracts; entirely offline with synthetic evidence."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "smart-notes"
sys.path.insert(0, str(SKILL / "scripts"))

from common import seconds, seek_url, video_url
from frame_selector import plan_frames, review_frames
from render_notes import render
from timeline import build_timeline
from transcript import normalize, parse_captions


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.metadata = json.loads((SKILL / "examples/metadata.json").read_text())
        self.transcript = normalize(parse_captions((SKILL / "examples/transcript.vtt").read_text(), ".vtt"), self.metadata)
        self.sections = json.loads((SKILL / "examples/sections.json").read_text())
        self.timeline = build_timeline(self.transcript, self.sections)
        self.notes = json.loads((SKILL / "examples/notes.json").read_text())

    def image(self):
        # A valid 1x1 PNG tests file handling, not visual interpretation.
        screenshot = self.work / "capture.png"
        screenshot.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8ZsAAAAASUVORK5CYII="))
        return screenshot

    def plan(self):
        return plan_frames(self.timeline, [{"section_id": "update", "timestamp": 46,
                                           "reason": "Inspect the worked example."}])

    def kept(self):
        return review_frames(self.plan(), [{"id": "frame-001", "decision": "keep",
                             "actual_timestamp": 49, "image": str(self.image()),
                             "visual_type": "equation", "description": "Synthetic image file test.",
                             "reason": "Fixture for asset copying only."}], self.work)

    def test_plain_ui_rows_infer_ends_and_preserve_unicode(self):
        raw = "00:00\nMinimize J(θ).\nSubject to θ ≥ 0.\n00:30 Update the parameter."
        result = normalize(parse_captions(raw, ".txt"), self.metadata)
        self.assertEqual(result["segments"][0]["text"], "Minimize J(θ). Subject to θ ≥ 0.")
        self.assertEqual([(c["start"], c["end"]) for c in result["segments"]], [(0, 30), (30, 90)])
        self.assertTrue(all(c["end_inferred"] for c in result["segments"]))
        self.assertTrue(any("inferred" in w for w in result["video"]["warnings"]))

    def test_vtt_tags_entities_settings_and_notes(self):
        raw = "WEBVTT\n\nNOTE ignore\nnot a cue\n\ncue-id\n00:01.250 --> 00:02.500 align:start\n<v Lecturer><c.green>x &lt; y</c> <00:01.500><b>θ</b>\n"
        self.assertEqual(parse_captions(raw, ".vtt"), [{"start": 1.25, "end": 2.5, "text": "x < y θ"}])

    def test_srt_comma_milliseconds_and_multiline(self):
        raw = "1\r\n00:00:01,500 --> 00:00:04,000\r\nFirst line\r\nsecond line\r\n"
        cue = parse_captions(raw, ".srt")[0]
        self.assertEqual(cue, {"start": 1.5, "end": 4, "text": "First line second line"})

    def test_json_duration_and_exact_duplicate_dedup(self):
        cue = {"start": 1, "duration": 2, "text": "Repeat"}
        result = normalize([cue, cue, {"start": 9, "text": "Repeat"}], self.metadata)
        self.assertEqual(len(result["segments"]), 2)
        self.assertEqual(result["segments"][0]["end"], 3)
        self.assertFalse(result["segments"][0]["end_inferred"])

    def test_overlapping_caption_text_is_not_silently_erased(self):
        result = normalize([{"start": 0, "end": 8, "text": "A definition"},
                            {"start": 5, "end": 12, "text": "A definition with more detail"}], self.metadata)
        self.assertEqual(len(result["segments"]), 2)
        self.assertEqual(result["segments"][0]["end"], 8)

    def test_invalid_times_and_caption_bounds(self):
        for value in (float("nan"), float("inf"), -1, True, "00:99", "1:99:00"):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                seconds(value)
        for cue in ({"start": 90, "text": "x"}, {"start": 0, "end": 91, "text": "x"},
                    {"start": 10, "end": 9, "text": "x"}):
            with self.subTest(cue=cue), self.assertRaises(ValueError):
                normalize([cue], self.metadata)
        with self.assertRaises(ValueError):
            normalize([], self.metadata)

    def test_hour_and_fractional_timestamps(self):
        self.assertEqual(seconds("01:02:03.125"), 3723.125)
        self.assertEqual(seconds("62:03,125"), 3723.125)

    def test_malformed_caption_input_fails_instead_of_partial_parse(self):
        for raw, suffix in (("UI label\n00:00 hello", ".txt"),
                            ("WEBVTT\n\n00:00 --> broken\nhello", ".vtt"),
                            ("WEBVTT\n\nthis cue lost its timing", ".vtt")):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_captions(raw, suffix)

    def test_youtube_url_canonicalization_and_timestamp_replacement(self):
        expected = "https://www.youtube.com/watch?v=DEMO0000001"
        for url in ("https://youtu.be/DEMO0000001?t=88", expected + "&list=abc&t=88",
                    "https://m.youtube.com/shorts/DEMO0000001", "https://youtube.com/live/DEMO0000001"):
            self.assertEqual(video_url(url), expected)
            self.assertEqual(seek_url(url, 12.9), expected + "&t=12s")
        for url in ("https://youtube.com.evil.invalid/watch?v=DEMO0000001", "file:///tmp/video", "https://youtu.be/bad"):
            with self.assertRaises(ValueError):
                video_url(url)

    def test_cue_crossing_section_boundary_is_in_both_sections(self):
        transcript = normalize([{"start": 0, "end": 35, "text": "Boundary context"},
                                {"start": 35, "end": 90, "text": "Rest"}], self.metadata)
        result = build_timeline(transcript, self.sections)
        self.assertIn("cue-0001", result["sections"][0]["segment_ids"])
        self.assertIn("cue-0001", result["sections"][1]["segment_ids"])

    def test_sections_cannot_drop_gaps_overlap_or_tail(self):
        for field, value in (("start", 31), ("start", 29), ("end", 73)):
            plan = copy.deepcopy(self.sections)
            plan[1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                build_timeline(self.transcript, plan)
        with self.assertRaises(ValueError):
            build_timeline(self.transcript, self.sections[:-1])

    def test_candidate_bounds_duplicates_and_budget(self):
        for candidates in ([{"section_id": "update", "timestamp": 74, "reason": "Outside"}],
                           [{"section_id": "missing", "timestamp": 1, "reason": "Unknown"}],
                           [{"section_id": "update", "timestamp": 46, "reason": "Duplicate"}] * 2,
                           [{"section_id": "update", "timestamp": t, "reason": "Too many"} for t in range(40, 44)]):
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                plan_frames(self.timeline, candidates)

    def test_kept_frame_requires_actual_time_in_section(self):
        review = {"id": "frame-001", "decision": "keep", "actual_timestamp": 80,
                  "image": str(self.image()), "visual_type": "diagram", "description": "Fixture", "reason": "Fixture"}
        with self.assertRaises(ValueError):
            review_frames(self.plan(), [review], self.work)

    def test_fake_image_is_rejected(self):
        fake = self.work / "capture.png"
        fake.write_text("<html>Sign in</html>")
        with self.assertRaises(ValueError):
            review_frames(self.plan(), [{"id": "frame-001", "decision": "keep", "actual_timestamp": 46,
                                        "image": str(fake), "visual_type": "diagram",
                                        "description": "Not a screenshot", "reason": "Fixture"}], self.work)

    def test_renderer_rejects_pending_frames_without_creating_output(self):
        output = self.work / "deliverable/notes.md"
        with self.assertRaises(ValueError):
            render(self.timeline, self.plan(), self.notes, output)
        self.assertFalse(output.parent.exists())

    def test_missing_screenshot_fails_before_render(self):
        kept = self.kept()
        Path(kept["frames"][0]["image"]).unlink()
        with self.assertRaises(ValueError):
            render(self.timeline, kept, self.notes, self.work / "notes.md")

    def test_portable_images_and_actual_frame_links(self):
        output = render(self.timeline, self.kept(), self.notes, self.work / "deliverable/study notes.md")
        markdown = output.read_text()
        self.assertIn("&t=49s)", markdown)
        self.assertIn("study%20notes.assets/", markdown)
        assets = list((output.parent / "study notes.assets").glob("*.png"))
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].read_bytes(), self.image().read_bytes())
        self.assertIn("\\theta_{k+1}", markdown)
        self.assertNotIn("Our aim is to minimize", markdown)

    def test_revised_rejection_removes_image_evidence(self):
        rejected = review_frames(self.kept(), [{"id": "frame-001", "decision": "reject", "reason": "Duplicate slide"}], self.work)
        self.assertNotIn("image", rejected["frames"][0])
        output = render(self.timeline, rejected, self.notes, self.work / "notes.md")
        self.assertNotIn("![", output.read_text())

    def test_wrong_video_manifest_is_rejected(self):
        manifest = plan_frames(self.timeline, [])
        manifest["video_url"] = "https://www.youtube.com/watch?v=OTHER000001"
        with self.assertRaises(ValueError):
            render(self.timeline, manifest, self.notes, self.work / "notes.md")

    def test_notes_must_cover_every_section_without_unknown_fields(self):
        for change in ("missing", "duplicate", "unknown"):
            notes = copy.deepcopy(self.notes)
            if change == "missing":
                notes["sections"].pop()
            elif change == "duplicate":
                notes["sections"].append(notes["sections"][0])
            else:
                notes["sections"][0]["unrendered_field"] = ["Do not lose this"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                render(self.timeline, plan_frames(self.timeline, []), notes, self.work / "notes.md")

    def test_partial_auto_caption_warnings_survive_rendering(self):
        metadata = dict(self.metadata, caption_source="auto", coverage="partial", warnings=["Missing 30–40 seconds."])
        transcript = normalize([{"start": 0, "end": 30, "text": "Observed opening"},
                                {"start": 40, "end": 90, "text": "Observed remainder"}], metadata)
        timeline = build_timeline(transcript, self.sections)
        output = render(timeline, plan_frames(timeline, []), self.notes, self.work / "notes.md")
        markdown = output.read_text()
        self.assertIn("Missing 30–40 seconds.", markdown)
        self.assertIn("Automatic captions", markdown)
        self.assertIn("Transcript coverage is partial", markdown)
        self.assertIn("no screenshot evidence", markdown)

    def test_cli_offline_pipeline(self):
        scripts = SKILL / "scripts"
        examples = SKILL / "examples"
        commands = [
            ["transcript.py", str(examples / "transcript.vtt"), "--metadata", str(examples / "metadata.json"), "--output", "transcript.json"],
            ["timeline.py", "transcript.json", "--sections", str(examples / "sections.json"), "--output", "timeline.json"],
            ["frame_selector.py", "plan", "timeline.json", "--candidates", str(examples / "candidates.json"), "--output", "plan.json"],
            ["frame_selector.py", "review", "plan.json", "--reviews", str(examples / "reviews.json"), "--output", "frames.json"],
            ["render_notes.py", "timeline.json", "--frames", "frames.json", "--notes", str(examples / "notes.json"), "--output", "notes.md"],
        ]
        for script, *args in commands:
            process = subprocess.run([sys.executable, str(scripts / script)] + args, cwd=self.work,
                                     capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
        markdown = (self.work / "notes.md").read_text()
        self.assertIn("Visual unavailable at 00:46", markdown)
        self.assertIn("Synthetic fixture", markdown)
        self.assertIn("Added explanations", markdown)


if __name__ == "__main__":
    unittest.main()
