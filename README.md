# Spotify to Phone Sync

A Windows-first project for maintaining a local music library and safely copying it to a connected phone or removable-storage music player.

## Current feature: safe MP3 folder sync

The first implementation copies MP3 files from a master folder to an existing USB/SD destination. It is deliberately preview-first and copy-only.

### Requirements

- Python 3.10 or newer
- A destination folder that is already mounted and accessible
- An existing marker file in the destination before applying changes

### Install for development

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
```

### Preview (default)

```powershell
playlist2phone --source "C:\Music\Master" --destination "E:\Music"
```

Or without installing the command:

```powershell
py -m playlist2phone.cli --source "C:\Music\Master" --destination "E:\Music"
```

Preview does not write files. To apply changes, first create the marker file yourself in the exact destination folder:

```powershell
New-Item -ItemType File -Path "E:\Music\.playlist2phone-target"
```

Then explicitly apply:

```powershell
playlist2phone --source "C:\Music\Master" --destination "E:\Music" --apply
```

The marker is a safety check, not a security boundary. Double-check the destination path before using `--apply`.

### Sync behaviour

- Copies new MP3 files and preserves subfolders.
- Skips files whose content is already identical (SHA-256 comparison).
- Replaces changed files.
- Ignores non-MP3 files and source symlinks.
- Never deletes files from the destination.
- Requires an existing marker file for apply mode.
- Rejects identical or nested source/destination folders.

### Run tests

```powershell
py -m unittest discover -s tests -v
```

## Planned workflow

1. Check a configured Spotify playlist.
2. Obtain audio files through a separately configured, legally permitted source.
3. Keep a master music folder on the computer.
4. Detect a connected device and copy only new or changed files.
5. Preview changes before applying them.

## Device support status

- USB mass-storage devices and SD cards: basic folder-copy engine implemented; automatic device detection is not implemented yet.
- Android MTP: not implemented. MTP is not equivalent to a normal drive-letter device and needs a separate, tested backend.
- Spotify playlist checking and audio acquisition: not implemented.

## Safety and privacy

- The computer's master music folder is the source of truth.
- Device files are never automatically deleted.
- Never commit credentials, personal playlist URLs, local paths, logs, or private playlist data.
- The marker file helps avoid selecting the wrong destination, but does not replace checking the path.

## Legal note

Only obtain, store, and transfer audio that you have the right to use. Follow Spotify's terms and the terms of any audio source or downloader used.
