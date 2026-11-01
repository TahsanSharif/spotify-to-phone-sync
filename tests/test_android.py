from types import SimpleNamespace
import unittest

from playlist2phone.android import (
    AndroidDetectionError,
    discover_mtp_devices,
    inspect_mtp_folder,
)


class FakeEntry:
    def __init__(self, name, content_type=2, children=None):
        self.name = name
        self.content_type = content_type
        self._children = children or []

    def get_child(self, name):
        return next((child for child in self._children if child.name == name), None)

    def get_children(self):
        return iter(self._children)


class FakeDevice:
    def __init__(self, name, description, storage_names):
        self.name = name
        self.description = description
        self._storage_names = storage_names
        self.closed = False
        self.roots = {
            storage_name: FakeEntry(storage_name, 0, [
                FakeEntry("Music", 1, [
                    FakeEntry("Proplaylist", 1, [
                        FakeEntry("song.mp3"),
                        FakeEntry("cover.jpg"),
                        FakeEntry("nested", 1),
                    ])
                ])
            ])
            for storage_name in storage_names
        }

    def get_content(self):
        return [self.roots[name] for name in self._storage_names]

    def close(self):
        self.closed = True


class FakeBackend:
    def __init__(self, devices):
        self.devices = devices

    def get_portable_devices(self):
        return self.devices


class AndroidDiscoveryTests(unittest.TestCase):
    def test_lists_device_names_and_storage_roots(self):
        device = FakeDevice("Example Android", "Example Android phone", ["Internal storage", "SD card"])
        result = discover_mtp_devices(backend=FakeBackend([device]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Example Android")
        self.assertEqual(result[0].description, "Example Android phone")
        self.assertEqual(result[0].storage_names, ("Internal storage", "SD card"))
        self.assertTrue(device.closed)

    def test_returns_empty_list_when_no_devices(self):
        self.assertEqual(discover_mtp_devices(backend=FakeBackend([])), [])

    def test_closes_all_devices_when_storage_read_fails(self):
        class BrokenDevice(FakeDevice):
            def get_content(self):
                raise OSError("device became unavailable")

        first = BrokenDevice("Example Android", "", [])
        second = FakeDevice("Another Android", "", ["Internal storage"])
        with self.assertRaises(AndroidDetectionError):
            discover_mtp_devices(backend=FakeBackend([first, second]))
        self.assertTrue(first.closed)
        self.assertTrue(second.closed)

    def test_does_not_include_serial_number_in_display_model(self):
        device = FakeDevice("Example Android", "Example", ["Internal storage"])
        device.serialnumber = "PRIVATE-SERIAL"
        result = discover_mtp_devices(backend=FakeBackend([device]))
        self.assertNotIn("PRIVATE-SERIAL", repr(result))

    def test_inspects_target_folder_counts_only_immediate_items(self):
        device = FakeDevice("Example Android", "", ["Internal storage"])
        result = inspect_mtp_folder(
            "Example Android", "Internal storage", "Music/Proplaylist",
            backend=FakeBackend([device]),
        )
        self.assertTrue(result.exists)
        self.assertEqual(result.mp3_count, 1)
        self.assertEqual(result.subfolder_count, 1)
        self.assertEqual(result.other_file_count, 1)
        self.assertTrue(device.closed)

    def test_reports_missing_folder_without_writing(self):
        device = FakeDevice("Example Android", "", ["Internal storage"])
        result = inspect_mtp_folder(
            "Example Android", "Internal storage", "Music/Missing",
            backend=FakeBackend([device]),
        )
        self.assertFalse(result.exists)
        self.assertTrue(device.closed)

    def test_rejects_parent_traversal_and_absolute_paths(self):
        device = FakeDevice("Example Android", "", ["Internal storage"])
        backend = FakeBackend([device])
        for path in ("../Music", "/Music", "C:/Music"):
            with self.subTest(path=path), self.assertRaises(AndroidDetectionError):
                inspect_mtp_folder("Example Android", "Internal storage", path, backend=backend)

    def test_rejects_ambiguous_device_name(self):
        devices = [
            FakeDevice("Example Android", "", ["Internal storage"]),
            FakeDevice("Example Android", "", ["Internal storage"]),
        ]
        with self.assertRaises(AndroidDetectionError):
            inspect_mtp_folder("Example Android", "Internal storage", "Music/Proplaylist", backend=FakeBackend(devices))
        self.assertTrue(all(device.closed for device in devices))


if __name__ == "__main__":
    unittest.main()
