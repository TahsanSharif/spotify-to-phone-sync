# Spotify to Phone Sync

A Windows-first project for keeping a local MP3 library and safely previewing music sync to Android smartphones over USB using Media Transfer Protocol (MTP).

## Android device detection and folder inspection (read-only)

The Android commands can list MTP devices, inspect a selected folder, and preview local-vs-phone MP3 differences. All three commands are read-only: they do not create, modify, upload, or delete device files.

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- An Android phone connected by a USB data cable
- The phone unlocked, with **File transfer (MTP)** selected in its USB options

### Install for development

From the repository root, in PowerShell:

~~~powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[android]"
~~~

The Android extra installs `comtypes`. The Windows MTP adapter is included under `src/mtp` from the MIT-licensed upstream project [Heribert17/mtp](https://github.com/Heribert17/mtp), pinned to commit `9d05c1e9495d1c7614f3af1b42eae28c66742fa8`. Its MIT license is included at `THIRD_PARTY_LICENSES/mtp-MIT.txt`.

### List connected MTP devices

Connect and unlock the phone, select **File transfer**, then run:

~~~powershell
playlist2phone-devices
~~~

### Inspect the target folder

Use the exact device and storage names reported above:

~~~powershell
playlist2phone-inspect --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist"
~~~

This reports whether the folder exists and counts MP3 files, subfolders, and other files directly inside it. It does not list private filenames or inspect nested folders. A missing folder is not created.

### Preview the computer-to-phone comparison (read-only)

Run this with the path to your computer's master MP3 folder:

~~~powershell
playlist2phone-android-preview --source "C:\Music\Master" --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist"
~~~

The preview walks MP3s in the computer master folder and recursively reads MP3 names and file sizes in the selected phone folder. It reports:

- **NEW** — no MP3 at that relative path was found on the phone.
- **SIZE DIFFERS** — the same relative path exists but file sizes differ; this is a possible update/conflict.
- **SAME SIZE - UNVERIFIED** — relative path and size match, but the audio contents have not been hashed or compared. This is not proof that the files are identical.

The preview does not download phone files, upload files, create folders, overwrite, or delete anything. If the phone folder is missing, it reports all local MP3s as new; it does not create the folder. Keep the phone unlocked during the scan.

## Existing local-folder copy utility

The generic preview-first copy engine is for ordinary filesystem paths and removable folders, not Android MTP storage.

Preview:

~~~powershell
playlist2phone --source "C:\Music\Master" --destination "E:\Music"
~~~

Apply only after creating the marker file in the exact destination folder:

~~~powershell
New-Item -ItemType File -Path "E:\Music\.playlist2phone-target"
playlist2phone --source "C:\Music\Master" --destination "E:\Music" --apply
~~~

It copies new MP3s, skips identical files using SHA-256, updates changed files, and never deletes destination files.

## Run tests

~~~powershell
py -m unittest discover -s tests -v
~~~

The Android tests use a fake MTP backend and do not require a physical phone. Real device detection, inspection, and preview still need to be tested on Windows with an actual phone.

## Planned workflow

1. Paste a Spotify playlist link and download/update the computer's master music folder.
2. Detect an Android phone over USB/MTP.
3. Preview which MP3s are new, possibly changed, or same-size on the phone.
4. Add a separately approved copy operation with safe folder creation and no automatic deletions.
5. Handle disconnect/reconnect safely.

## Safety and privacy

- The computer's master music folder is the source of truth.
- Current Android commands are read-only.
- Device files must never be automatically deleted.
- Never commit credentials, personal playlist URLs, local paths, logs, or private playlist data.

## Legal note

Only obtain, store, and transfer audio that you have the right to use. Follow Spotify's terms and the terms of any audio source or downloader used.
