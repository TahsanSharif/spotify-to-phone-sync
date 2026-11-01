"""Read-only discovery of Windows MTP devices (including Android phones).

This module deliberately does not create, modify, upload, or delete device files.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any


class AndroidDetectionError(RuntimeError):
    """Raised when Windows MTP device discovery cannot be performed."""


@dataclass(frozen=True)
class MTPDeviceInfo:
    """Non-sensitive display information about a connected MTP device."""

    name: str
    description: str
    storage_names: tuple[str, ...]


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


def discover_mtp_devices(*, backend: Any | None = None) -> list[MTPDeviceInfo]:
    """Return connected MTP device names and storage roots, without writing.

    backend is an injectable adapter used by tests. In normal use, the
    Windows MTP backend is loaded automatically.
    """
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
                name = str(getattr(device, "name", "") or "Unnamed MTP device").strip()
                description = str(getattr(device, "description", "") or "").strip()
                found.append(
                    MTPDeviceInfo(
                        name=name or "Unnamed MTP device",
                        description=description,
                        storage_names=storage_names,
                    )
                )
            except Exception as exc:
                raise AndroidDetectionError(
                    "Windows detected an MTP device but could not read its storage list. "
                    "Keep the phone unlocked and reconnect it."
                ) from exc
    finally:
        # The backend holds COM/WPD resources; always release every opened device.
        for device in devices:
            try:
                device.close()
            except Exception:
                # A failed close must not hide the discovery result or original error.
                pass

    return found


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playlist2phone-devices",
        description="List connected Windows MTP devices and their storage roots (read-only).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
