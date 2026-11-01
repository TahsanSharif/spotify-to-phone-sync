"""Read-only discovery, inspection, and preview of Windows MTP devices.

This module deliberately does not create, modify, upload, or delete device files.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
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


@dataclass(frozen=True)
class MTPPreviewItem:
    """One source MP3 and its read-only comparison with the phone."""
    relative_path: str
    source_size: int
    status: str
    phone_size: int | None = None


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


def _validated_parts(relative_path: str) -> list[str]:
    parts = [part for part in relative_path.replace("\\", "/").split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise AndroidDetectionError("The phone folder path must be a non-empty relative path without '..'.")
    if relative_path.startswith(("/", "\\\\")) or ":" in relative_path:
        raise AndroidDetectionError("The phone folder path must be relative to the selected storage.")
    return parts


def _open_mtp_target(device_name: str, storage_name: str, relative_path: str, backend: Any):
    """Open a target folder and return (devices, device, folder, normalized path)."""
    parts = _validated_parts(relative_path)
    try:
        devices = backend.get_portable_devices()
    except Exception as exc:
        raise AndroidDetectionError("Windows could not enumerate MTP devices. Reconnect and unlock the phone.") from exc
    try:
        matches = [device for device in devices if _device_label(device).casefold() == device_name.casefold()]
        if len(matches) != 1:
            raise AndroidDetectionError(f"Expected one connected device named '{device_name}', found {len(matches)}.")
        device = matches[0]
        storages = [item for item in device.get_content() if str(getattr(item, "name", "")).casefold() == storage_name.casefold()]
        if len(storages) != 1:
            raise AndroidDetectionError(f"Expected one storage named '{storage_name}', found {len(storages)}.")
        current = storages[0]
        for index, part in enumerate(parts):
            current = current.get_child(part)
            if current is None or (index < len(parts) - 1 and getattr(current, "content_type", 1) != 1):
                return devices, device, None, "/".join(parts)
        if getattr(current, "content_type", 1) != 1:
            raise AndroidDetectionError("The selected phone path exists but is not a folder.")
        return devices, device, current, "/".join(parts)
    except Exception:
        for item in devices:
            try:
                item.close()
            except Exception:
                pass
        raise


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
                storage_names = tuple(
                    str(storage.name).strip()
                    for storage in device.get_content()
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
    device_name: str, storage_name: str, relative_path: str, *, backend: Any | None = None,
) -> MTPFolderInfo:
    """Check a folder and count its immediate contents; never writes to the phone."""
    mtp_backend = backend if backend is not None else _load_windows_mtp_backend()
    devices, _device, current, normalized = _open_mtp_target(device_name, storage_name, relative_path, mtp_backend)
    try:
        if current is None:
            return MTPFolderInfo(device_name, storage_name, normalized, False)
        entries = list(current.get_children())
        mp3_count = sum(1 for entry in entries if getattr(entry, "content_type", 2) == 2 and str(getattr(entry, "name", "")).casefold().endswith(".mp3"))
        folder_count = sum(1 for entry in entries if getattr(entry, "content_type", 2) == 1)
        other_count = sum(1 for entry in entries if getattr(entry, "content_type", 2) == 2 and not str(getattr(entry, "name", "")).casefold().endswith(".mp3"))
        return MTPFolderInfo(device_name, storage_name, normalized, True, mp3_count, folder_count, other_count)
    except AndroidDetectionError:
        raise
    except Exception as exc:
        raise AndroidDetectionError("The phone was detected, but Windows could not inspect that folder. Keep the phone unlocked and reconnect it.") from exc
    finally:
        for device in devices:
            try:
                device.close()
            except Exception:
                pass


def _local_mp3_files(source: Path) -> dict[str, int]:
    if not source.exists() or not source.is_dir():
        raise AndroidDetectionError(f"Source master folder does not exist or is not a directory: {source}")
    result: dict[str, int] = {}
    folded: set[str] = set()
    for root, dirs, files in os.walk(source, followlinks=False):
        root_path = Path(root)
        dirs[:] = [name for name in dirs if not (root_path / name).is_symlink()]
        for name in files:
            path = root_path / name
            if path.is_symlink() or path.suffix.casefold() != ".mp3":
                continue
            relative = path.relative_to(source).as_posix()
            key = relative.casefold()
            if key in folded:
                raise AndroidDetectionError(f"Source contains filenames that collide on a case-insensitive phone: {relative}")
            folded.add(key)
            result[relative] = path.stat().st_size
    return result


def _remote_mp3_files(folder: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    folded: set[str] = set()

    def walk(parent: Any, prefix: str = "") -> None:
        for entry in parent.get_children():
            name = str(getattr(entry, "name", ""))
            if not name or name in {".", ".."} or "/" in name or "\\\\" in name:
                raise AndroidDetectionError("The phone returned an invalid filename; preview was stopped.")
            relative = f"{prefix}/{name}" if prefix else name
            kind = getattr(entry, "content_type", -1)
            if kind == 1:
                walk(entry, relative)
            elif kind == 2 and name.casefold().endswith(".mp3"):
                key = relative.casefold()
                if key in folded:
                    raise AndroidDetectionError(f"Phone contains ambiguous case-insensitive MP3 paths: {relative}")
                folded.add(key)
                result[relative] = int(getattr(entry, "size", 0))
    walk(folder)
    return result


def preview_mtp_sync(
    source: str | os.PathLike[str], device_name: str, storage_name: str, relative_path: str,
    *, backend: Any | None = None,
) -> list[MTPPreviewItem]:
    """Compare local MP3 paths/sizes with MTP files. No phone files are read or written."""
    local = _local_mp3_files(Path(source))
    mtp_backend = backend if backend is not None else _load_windows_mtp_backend()
    devices, _device, target, _normalized = _open_mtp_target(device_name, storage_name, relative_path, mtp_backend)
    try:
        remote = _remote_mp3_files(target) if target is not None else {}
        remote_by_key = {path.casefold(): (path, size) for path, size in remote.items()}
        items: list[MTPPreviewItem] = []
        for path, size in sorted(local.items(), key=lambda pair: pair[0].casefold()):
            match = remote_by_key.get(path.casefold())
            if match is None:
                items.append(MTPPreviewItem(path, size, "NEW"))
            elif match[1] == size:
                items.append(MTPPreviewItem(path, size, "SAME_SIZE_UNVERIFIED", match[1]))
            else:
                items.append(MTPPreviewItem(path, size, "SIZE_DIFFERS", match[1]))
        return items
    except AndroidDetectionError:
        raise
    except Exception as exc:
        raise AndroidDetectionError("Could not safely read the phone folder for preview. Keep the phone unlocked and reconnect it.") from exc
    finally:
        for device in devices:
            try:
                device.close()
            except Exception:
                pass


def _print_device_error(exc: Exception, operation: str) -> int:
    print(f"{operation} failed: {exc}", file=sys.stderr)
    return 2


def devices_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="playlist2phone-devices", description="List connected Windows MTP devices (read-only).").parse_args(argv)
    try:
        devices = discover_mtp_devices()
    except AndroidDetectionError as exc:
        return _print_device_error(exc, "Device detection")
    if not devices:
        print("No MTP devices found. Unlock your phone, connect by USB, and choose File transfer (MTP).")
        return 0
    print(f"Found {len(devices)} MTP device(s):")
    for index, device in enumerate(devices, start=1):
        print(f"\n{index}. {device.name}")
        if device.description and device.description != device.name:
            print(f"   Description: {device.description}")
        print("   Storage:")
        for storage_name in device.storage_names:
            print(f"   - {storage_name}")
    print("\nRead-only check complete. No phone files were changed.")
    return 0


def inspect_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="playlist2phone-inspect", description="Inspect a phone folder over USB/MTP (read-only).")
    parser.add_argument("--device", required=True)
    parser.add_argument("--storage", required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args(argv)
    try:
        info = inspect_mtp_folder(args.device, args.storage, args.path)
    except AndroidDetectionError as exc:
        return _print_device_error(exc, "Folder inspection")
    print(f"Device: {info.device_name}\nStorage: {info.storage_name}\nFolder: {info.relative_path}")
    if not info.exists:
        print("Status: Folder not found")
    else:
        print(f"Status: Folder exists\nMP3 files: {info.mp3_count}\nSubfolders: {info.subfolder_count}\nOther files: {info.other_file_count}")
    print("\nRead-only inspection complete. No phone files were changed.")
    return 0


def preview_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="playlist2phone-android-preview", description="Preview local MP3 changes for an Android MTP folder. Read-only.")
    parser.add_argument("--source", required=True, help="Computer master MP3 folder")
    parser.add_argument("--device", required=True, help="Exact MTP device name")
    parser.add_argument("--storage", required=True, help="Exact storage name")
    parser.add_argument("--path", required=True, help="Destination folder, relative to storage")
    args = parser.parse_args(argv)
    try:
        items = preview_mtp_sync(args.source, args.device, args.storage, args.path)
    except (AndroidDetectionError, OSError) as exc:
        return _print_device_error(exc, "Android preview")
    counts = {status: sum(item.status == status for item in items) for status in ("NEW", "SIZE_DIFFERS", "SAME_SIZE_UNVERIFIED")}
    print(f"PREVIEW ONLY: {len(items)} local MP3 file(s)")
    print(f"New on phone: {counts['NEW']}")
    print(f"Same path and size (not verified identical): {counts['SAME_SIZE_UNVERIFIED']}")
    print(f"Same path but different size: {counts['SIZE_DIFFERS']}")
    for item in items:
        if item.status == "NEW":
            print(f"NEW                  {item.relative_path} ({item.source_size} bytes)")
        elif item.status == "SIZE_DIFFERS":
            print(f"SIZE DIFFERS         {item.relative_path} (PC {item.source_size}; phone {item.phone_size} bytes)")
        else:
            print(f"SAME SIZE - UNVERIFIED {item.relative_path} ({item.source_size} bytes)")
    print("\nRead-only preview complete. No phone files were changed.")
    print("A matching filename and size do not prove the audio contents are identical.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return devices_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())


@dataclass(frozen=True)
class MTPTransferResult:
    copied: tuple[str, ...]
    skipped: tuple[str, ...]
    conflicts: tuple[str, ...]
    failed: tuple[str, ...]
    created_folders: tuple[str, ...]
    pending: tuple[str, ...] = ()


def _ensure_mtp_folder(parent: Any, name: str) -> tuple[Any, bool]:
    matches = [x for x in parent.get_children() if str(getattr(x, "name", "")).casefold() == name.casefold()]
    if len(matches) > 1:
        raise AndroidDetectionError(f"Multiple phone entries match '{name}'.")
    if matches:
        if getattr(matches[0], "content_type", -1) != 1:
            raise AndroidDetectionError(f"Phone path component '{name}' is not a folder.")
        return matches[0], False
    return parent.create_content(name), True


def transfer_new_mtp_files(source, device_name, storage_name, relative_path, *, backend=None, apply=False):
    """Copy only missing MP3 paths. Dry-run by default; never overwrite or delete."""
    root = Path(source)
    local = _local_mp3_files(root)
    if not apply:
        items = preview_mtp_sync(root, device_name, storage_name, relative_path, backend=backend)
        return MTPTransferResult((), tuple(x.relative_path for x in items if x.status == "SAME_SIZE_UNVERIFIED"),
                                 tuple(x.relative_path for x in items if x.status == "SIZE_DIFFERS"), (), (), tuple(x.relative_path for x in items if x.status == "NEW"))

    target_parts = _validated_parts(relative_path)
    mtp_backend = backend if backend is not None else _load_windows_mtp_backend()
    try:
        devices = mtp_backend.get_portable_devices()
    except Exception as exc:
        raise AndroidDetectionError("Windows could not enumerate MTP devices. Reconnect and unlock the phone.") from exc
    copied, skipped, conflicts, failed, created = [], [], [], [], []
    try:
        matches = [d for d in devices if _device_label(d).casefold() == device_name.casefold()]
        if len(matches) != 1:
            raise AndroidDetectionError(f"Expected one device named '{device_name}', found {len(matches)}.")
        storages = [s for s in matches[0].get_content() if str(getattr(s, "name", "")).casefold() == storage_name.casefold()]
        if len(storages) != 1:
            raise AndroidDetectionError(f"Expected one storage named '{storage_name}', found {len(storages)}.")
        storage = storages[0]

        target = storage
        exists = True
        for part in target_parts:
            found = [x for x in target.get_children() if str(getattr(x, "name", "")).casefold() == part.casefold()]
            if len(found) > 1:
                raise AndroidDetectionError(f"Ambiguous phone folder component '{part}'.")
            if not found:
                exists = False
                break
            target = found[0]
            if getattr(target, "content_type", -1) != 1:
                raise AndroidDetectionError(f"Phone path component '{part}' is not a folder.")
        remote = _remote_mp3_files(target) if exists else {}
        remote_sizes = {name.casefold(): size for name, (_entry, size) in remote.items()}
        pending = []
        for relative, (local_file, size) in sorted(local.items(), key=lambda x: x[0].casefold()):
            old_size = remote_sizes.get(relative.casefold())
            if old_size is None:
                pending.append((relative, local_file, size))
            elif old_size == size:
                skipped.append(relative)
            else:
                conflicts.append(relative)
        if not pending:
            return MTPTransferResult((), tuple(skipped), tuple(conflicts), (), ())

        target = storage
        for index, part in enumerate(target_parts):
            target, made = _ensure_mtp_folder(target, part)
            if made:
                created.append("/".join(target_parts[:index + 1]))

        for relative, local_file, expected_size in pending:
            try:
                parent = target
                parent_parts = []
                components = relative.split("/")
                for component in components[:-1]:
                    parent_parts.append(component)
                    parent, made = _ensure_mtp_folder(parent, component)
                    if made:
                        created.append("/".join(target_parts + parent_parts))
                filename = components[-1]
                collision = [x for x in parent.get_children() if str(getattr(x, "name", "")).casefold() == filename.casefold()]
                if collision:
                    conflicts.append(relative)
                    continue
                if local_file.is_symlink() or not local_file.is_file() or local_file.stat().st_size != expected_size:
                    failed.append(relative)
                    continue
                parent.upload_file(filename, str(local_file))
                uploaded = parent.get_child(filename)
                if uploaded is None or int(getattr(uploaded, "size", -1)) != expected_size:
                    failed.append(relative)
                else:
                    copied.append(relative)
            except Exception:
                failed.append(relative)
        return MTPTransferResult(tuple(copied), tuple(skipped), tuple(conflicts), tuple(failed), tuple(created))
    except AndroidDetectionError:
        raise
    except Exception as exc:
        raise AndroidDetectionError("MTP transfer stopped due to a device error. Reconnect and run preview again.") from exc
    finally:
        for device in devices:
            try:
                device.close()
            except Exception:
                pass


def transfer_main(argv=None):
    parser = argparse.ArgumentParser(prog="playlist2phone-android-transfer",
        description="Copy missing MP3s to Android over USB/MTP. Dry-run by default; --apply is required to write.")
    parser.add_argument("--source", required=True, help="Computer master MP3 folder")
    parser.add_argument("--device", required=True)
    parser.add_argument("--storage", required=True)
    parser.add_argument("--path", required=True, help="Destination folder relative to storage")
    parser.add_argument("--apply", action="store_true", help="Create missing folders and copy missing MP3s.")
    args = parser.parse_args(argv)
    try:
        result = transfer_new_mtp_files(args.source, args.device, args.storage, args.path, apply=args.apply)
    except (AndroidDetectionError, OSError) as exc:
        print(f"Android transfer failed: {exc}", file=sys.stderr)
        return 2
    mode = "TRANSFER" if args.apply else "DRY RUN"
    print(f"{mode}: to copy {len(result.pending)}, copied {len(result.copied)}, skipped {len(result.skipped)}, conflicts {len(result.conflicts)}, failed {len(result.failed)}")
    if result.created_folders:
        print("Created folders:")
        for name in result.created_folders:
            print(f"  {name}")
    for label, values in (("TO COPY", result.pending), ("COPIED", result.copied), ("SKIPPED", result.skipped), ("CONFLICT", result.conflicts), ("FAILED", result.failed)):
        for name in values:
            print(f"{label:9} {name}")
    print("Existing files are never overwritten; no phone files were deleted.")
    if not args.apply:
        print("Dry run only. Add --apply to copy missing files.")
    return 1 if result.conflicts or result.failed else 0
