from pathlib import Path
import tempfile
import unittest

from playlist2phone.sync import SyncSafetyError, sync_mp3s


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "master"
        self.destination = self.root / "phone"
        self.source.mkdir()
        self.destination.mkdir()
        (self.destination / ".playlist2phone-target").write_text("This folder is the intended sync target.\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_does_not_copy(self):
        (self.source / "Track.mp3").write_bytes(b"audio")
        result = sync_mp3s(self.source, self.destination)
        self.assertEqual([(x.action, x.relative_path) for x in result], [("copy", "Track.mp3")])
        self.assertFalse((self.destination / "Track.mp3").exists())

    def test_apply_copies_after_marker_check(self):
        (self.source / "Track.mp3").write_bytes(b"audio")
        result = sync_mp3s(self.source, self.destination, apply=True)
        self.assertEqual(result[0].action, "copy")
        self.assertEqual((self.destination / "Track.mp3").read_bytes(), b"audio")

    def test_identical_file_is_skipped(self):
        (self.source / "Track.mp3").write_bytes(b"audio")
        (self.destination / "Track.mp3").write_bytes(b"audio")
        result = sync_mp3s(self.source, self.destination, apply=True)
        self.assertEqual(result[0].action, "skip")

    def test_changed_file_is_updated(self):
        (self.source / "Track.mp3").write_bytes(b"new audio")
        (self.destination / "Track.mp3").write_bytes(b"old audio")
        result = sync_mp3s(self.source, self.destination, apply=True)
        self.assertEqual(result[0].action, "update")
        self.assertEqual((self.destination / "Track.mp3").read_bytes(), b"new audio")

    def test_apply_requires_marker(self):
        (self.destination / ".playlist2phone-target").unlink()
        with self.assertRaises(SyncSafetyError):
            sync_mp3s(self.source, self.destination, apply=True)

    def test_preview_does_not_require_marker(self):
        (self.destination / ".playlist2phone-target").unlink()
        self.assertEqual(sync_mp3s(self.source, self.destination), [])

    def test_rejects_nested_roots(self):
        with self.assertRaises(SyncSafetyError):
            sync_mp3s(self.source, self.source / "inside")

    def test_ignores_non_mp3_files(self):
        (self.source / "cover.jpg").write_bytes(b"image")
        (self.source / "notes.txt").write_text("not audio")
        self.assertEqual(sync_mp3s(self.source, self.destination), [])

    def test_never_deletes_extra_destination_files(self):
        extra = self.destination / "keep-me.mp3"
        extra.write_bytes(b"keep")
        sync_mp3s(self.source, self.destination, apply=True)
        self.assertTrue(extra.exists())


if __name__ == "__main__":
    unittest.main()
