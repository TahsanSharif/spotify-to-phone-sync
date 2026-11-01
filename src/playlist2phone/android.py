"""Read-only discovery and inspection of Windows MTP devices.

This module deliberately does not create, modify, upload, or delete device files.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


class AndroidDetectionError(RuntimeError):
    """Raised when Windows MTP operations cannot be performed."""


@dataclass(frozen=True)
class MTPDeviceInfo:
    """Non-sensitive display information about a connected MTP device."""
    name: str
    description: str
    storage_names: tuple[str, ...]


@dataclass(frozen=True)
class MTPFolderInfo:
    """Read-only summary of a folder on an MTP storage."""
    device_name: str
    storage_name: str
    relative_path: str
    exists: bool
    mp3_count: int = 0
    subfolder_count: int = 0
    other_file_count: int = 0


def _load_windows_mtp_backend() -> Any:
    if sys.platform != "win32":
        raise AndroidDetectionError(
            "Android USB/MTP detection currently requires Windows 10 or 11."
        )
    try:
        from mtp import win_access
    except ImportError as exc:
        raise AndroidDetectionError(
            'The optional MTP dependency is missing. Install it with: '
            'py -m pip install -e ".[android]"'
        ) from exc
    return win_access


def _device_label(device: Any) -> str:
    return str(getattr(device, "name", "") or getattr(device, "devicename", "") or "Unnamed MTP device").strip()


def discover_mtp_devices(*, backend: Any | None = None) -> list[MTPDeviceInfo]:
    """Return connected MTP device names and storage roots, without writing."""
    mtp_backend = backend if backend is not None else _load_windows_mtp_backend()
    try:
        devices = mtp_backend.get_portable_devices()
    except Exception as exc:
        raise AndroidDetectionError(
            "Windows could not enumerate MTP devices. Check the USB connection, "
            "unlock the phone, and select File transfer (MTP)."
        ) from exc

    found: list[MTPDeviceInfo] = []
    try:
        for device in devices:
            try:
                storages = device.get_content()
                storage_names = tuple(
                    str(storage.name).strip()
                    for storage in storages
                    if str(getattr(storage, "name", "")).strip()
                )
                name = _device_label(device)
                description = str(getattr(device, "description", "") or "").strip()
                found.append(MTPDeviceInfo(name, description, storage_names))
            except Exception as exc:
                raise AndroidDetectionError(
                    "Windows detected an MTP device but could not read its storage list. "
                    "Keep the phone unlocked and reconnect it."
                ) from exc
    finally:
        for device in devices:
            try:
                device.close()
            except Exception:
                pass
    return found


def inspect_mtp_folder(
    device_name: str,
    storage_name: str,
    relative_path: str,
    *,
    backend: Any | None = None,
) -> MTPFolderInfo:
    """Check a folder and count its immediate contents; never writes to the phone."""
    parts = [part for part in relative_path.replace("\\", "/").split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise AndroidDetectionError("The phone folder path must be a non-empty relative path without '..'.")
    if relative_path.startswith(("/", "\\")) or ":" in relative_path:
        raise AndroidDetectionError("The phone folder path must be relative to the selected storage.")

    mtp_backend = backend if backend is not None else _load_windows_mtp_backend()
    try:
        devices = mtp_backend.get_portable_devices()
    except Exception as exc:
        raise AndroidDetectionError("Windows could not enumerate MTP devices. Reconnect and unlock the phone.") from exc

    try:
        matches = [device for device in devices if _device_label(device).casefold() == device_name.casefold()]
        if len(matches) != 1:
            raise AndroidDetectionError(
                f"Expected one connected device named '{device_name}', found {len(matches)}."
            )
        device = matches[0]
        try:
            storages = [item for item in device.get_content() if str(getattr(item, "name", "")).casefold() == storage_name.casefold()]
            if len(storages) != 1:
                raise AndroidDetectionError(
                    f"Expected one storage named '{storage_name}', found {len(storages)}."
                )
            current = storages[0]
            for part in parts:
                current = current.get_child(part)
                if current is None:
                    return MTPFolderInfo(device_name, storage_name, "/".join(parts), False)
                if part != parts[-1] and getattr(current, "content_type", 1) != 1:
                    return MTPFolderInfo(device_name, storage_name, "/".join(parts), False)

            entries = list(current.get_children())
            mp3_count = sum(
                1 for entry in entries
                if getattr(entry, "content_type", 2) == 2 and str(getattr(entry, "name", "")).casefold().endswith(".mp3")
            )
            folder_count = sum(1 for entry in entries if getattr(entry, "content_type", 2) == 1)
            other_count = sum(
                1 for entry in entries
                if getattr(entry, "content_type", 2) == 2 and not str(getattr(entry, "name", "")).casefold().endswith(".mp3")
            )
            return MTPFolderInfo(device_name, storage_name, "/".join(parts), True, mp3_count, folder_count, other_count)
        except AndroidDetectionError:
            raise
        except Exception as exc:
            raise AndroidDetectionError(
                "The phone was detected, but Windows could not inspect that folder. "
                "Keep the phone unlocked and reconnect it."
            ) from exc
    finally:
        for device in devices:
            try:
                device.close()
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playlist2phone-devices",
        description="List connected Windows MTP devices and storage roots (read-only).",
    )
    return parser


def devices_main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    try:
        devices = discover_mtp_devices()
    except AndroidDetectionError as exc:
        print(f"Device detection failed: {exc}", file=sys.stderr)
        return 2
    if not devices:
        print("No MTP devices found.")
        print("Unlock your Android phone, connect it by USB, and choose File transfer (MTP).")
        return 0
    print(f"Found {len(devices)} MTP device(s):")
    for index, device in enumerate(devices, start=1):
        print(f"\n{index}. {device.name}")
        if device.description and device.description != device.name:
            print(f"   Description: {device.description}")
        if device.storage_names:
            print("   Storage:")
            for storage_name in device.storage_names:
                print(f"   - {storage_name}")
        else:
            print("   Storage: Windows did not report any storage roots.")
    print("\nRead-only check complete. No phone files were changed.")
    return 0


def inspect_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="playlist2phone-inspect",
        description="Inspect one folder on an Android phone over USB/MTP (read-only).",
    )
    parser.add_argument("--device", required=True, help="Exact device name shown by playlist2phone-devices")
    parser.add_argument("--storage", required=True, help="Storage name shown by playlist2phone-devices")
    parser.add_argument("--path", required=True, help="Folder path relative to storage, e.g. Music/Proplaylist")
    args = parser.parse_args(argv)
    try:
        info = inspect_mtp_folder(args.device, args.storage, args.path)
    except AndroidDetectionError as exc:
        print(f"Folder inspection failed: {exc}", file=sys.stderr)
        return 2
    print(f"Device: {info.device_name}")
    print(f"Storage: {info.storage_name}")
    print(f"Folder: {info.relative_path}")
    if not info.exists:
        print("Status: Folder not found")
    else:
        print("Status: Folder exists")
        print(f"MP3 files in this folder: {info.mp3_count}")
        print(f"Subfolders: {info.subfolder_count}")
        print(f"Other files: {info.other_file_count}")
    print("\nRead-only inspection complete. No phone files were changed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return devices_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
