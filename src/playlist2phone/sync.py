"""Preview-first copying of MP3 files to a marked destination."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


class SyncSafetyError(ValueError):
    """Raised when a sync target fails a safety check."""


@dataclass(frozen=True)
class SyncAction:
    relative_path: str
    action: str  # "copy", "update", or "skip"
    reason: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_roots(source: Path, destination: Path) -> tuple[Path, Path]:
    if not source.is_dir():
        raise SyncSafetyError(f"Source folder does not exist: {source}")
    if not destination.is_dir():
        raise SyncSafetyError(
            f"Destination folder must already exist: {destination}"
        )

    source_root = source.resolve()
    destination_root = destination.resolve()
    if source_root == destination_root:
        raise SyncSafetyError("Source and destination must be different folders.")
    if source_root in destination_root.parents or destination_root in source_root.parents:
        raise SyncSafetyError("Source and destination must not contain one another.")
    return source_root, destination_root


def sync_mp3s(
    source: str | Path,
    destination: str | Path,
    *,
    marker_name: str = ".playlist2phone-target",
    apply: bool = False,
) -> list[SyncAction]:
    """Plan or perform a copy-only MP3 sync.

    Preview is the default. Applying changes requires an existing marker file
    directly inside the destination. Existing files are compared by SHA-256.
    No destination files are ever deleted.
    """
    source_root, destination_root = _validate_roots(
        Path(source).expanduser(), Path(destination).expanduser()
    )

    if not marker_name or Path(marker_name).name != marker_name:
        raise SyncSafetyError("Marker name must be a single file name.")
    marker = destination_root / marker_name
    if apply and (not marker.is_file() or marker.is_symlink()):
        raise SyncSafetyError(
            f"Apply mode requires a real marker file in the destination: {marker}"
        )

    actions: list[SyncAction] = []
    for item in sorted(source_root.rglob("*")):
        if item.is_symlink() or not item.is_file() or item.suffix.lower() != ".mp3":
            continue

        relative = item.relative_to(source_root)
        target = destination_root / relative
        if target.is_symlink():
            raise SyncSafetyError(f"Refusing to overwrite a symbolic link: {target}")

        if not target.exists():
            action = SyncAction(relative.as_posix(), "copy", "not present on device")
        elif not target.is_file():
            raise SyncSafetyError(f"Destination path is not a regular file: {target}")
        elif _sha256(item) == _sha256(target):
            action = SyncAction(relative.as_posix(), "skip", "identical content")
        else:
            action = SyncAction(relative.as_posix(), "update", "content differs")

        actions.append(action)
        if apply and action.action in {"copy", "update"}:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".playlist2phone-tmp")
            try:
                with item.open("rb") as source_stream, temporary.open("wb") as target_stream:
                    for chunk in iter(lambda: source_stream.read(1024 * 1024), b""):
                        target_stream.write(chunk)
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()

    return actions
