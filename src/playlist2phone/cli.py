"""Command-line interface for preview-first MP3 copying."""

from __future__ import annotations

import argparse
import sys

from .sync import SyncSafetyError, sync_mp3s


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playlist2phone",
        description="Preview or copy MP3 files to a marked USB music folder.",
    )
    parser.add_argument("--source", required=True, help="Master music folder on this computer")
    parser.add_argument("--destination", required=True, help="Existing USB/SD music folder")
    parser.add_argument(
        "--marker",
        default=".playlist2phone-target",
        help="Marker file that must already exist in the destination for --apply",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy/update files. Without this flag, only preview changes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        actions = sync_mp3s(
            args.source,
            args.destination,
            marker_name=args.marker,
            apply=args.apply,
        )
    except (OSError, SyncSafetyError) as exc:
        print(f"Safety check failed: {exc}", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "PREVIEW"
    print(f"{mode}: {len(actions)} MP3 file(s) checked")
    for item in actions:
        print(f"{item.action.upper():6} {item.relative_path} — {item.reason}")
    print("No destination files were deleted.")
    if not args.apply:
        print("Preview only. Add --apply to copy; an existing marker file is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
