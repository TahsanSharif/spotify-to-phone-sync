from types import SimpleNamespace
import unittest

from playlist2phone.android import AndroidDetectionError, discover_mtp_devices


class FakeDevice:
    def __init__(self, name, description, storage_names):
        self.name = name
        self.description = description
        self._storage_names = storage_names
        self.closed = False

    def get_content(self):
        return [SimpleNamespace(name=name) for name in self._storage_names]

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


if __name__ == "__main__":
    unittest.main()
