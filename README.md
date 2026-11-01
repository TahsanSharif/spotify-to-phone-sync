# Spotify to Phone Sync

A Windows-first project for keeping a local MP3 library and safely syncing music to Android smartphones over USB using Media Transfer Protocol (MTP).

## Android device detection and folder inspection (read-only)

The Android commands can list MTP devices and inspect a selected folder. They do not upload music, create folders, modify files, or delete anything on the phone.

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer (the upstream MTP library documents testing with Python 3.12+)
- An Android phone connected by a USB data cable
- The phone unlocked, with **File transfer (MTP)** selected in its USB options

### Install for development

From the repository root, in PowerShell:

~~~powershell
py -3.13 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
py -m pip install -e ".[android]"
~~~

The Android extra installs `comtypes`. The Windows MTP adapter used by this milestone is included under `src/mtp` from the MIT-licensed upstream project [Heribert17/mtp](https://github.com/Heribert17/mtp), pinned to commit `9d05c1e9495d1c7614f3af1b42eae28c66742fa8`. Its MIT license is included at `THIRD_PARTY_LICENSES/mtp-MIT.txt`. This avoids the upstream repository's current packaging-layout error during pip installation.

### List connected MTP devices

Connect and unlock the phone, select **File transfer**, then run:

~~~powershell
playlist2phone-devices
~~~

This command reports device names and storage-root names only.

### Inspect the target folder

Use the exact device and storage names reported by the device command. For example:

~~~powershell
playlist2phone-inspect --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist"
~~~

The inspection is read-only. It reports whether the requested folder exists and counts MP3 files, subfolders, and other files directly inside it. It does not list private filenames or inspect nested folders. If the folder does not exist, the command only reports that; it does not create it.

If no device appears, try another USB data cable/port, unlock the phone, select **File transfer (MTP)**, and run the command again.

## Existing local-folder copy utility

The project also contains a generic preview-first MP3 folder-copy engine. This is for ordinary filesystem paths and removable folders; it does not yet copy directly to Android MTP storage.

Preview:

~~~powershell
playlist2phone --source "C:\\Music\\Master" --destination "E:\\Music"
~~~

Apply only after creating the marker file in the exact destination folder:

~~~powershell
New-Item -ItemType File -Path "E:\\Music\\.playlist2phone-target"
playlist2phone --source "C:\\Music\\Master" --destination "E:\\Music" --apply
~~~

The folder-copy utility copies new MP3s, skips identical files using SHA-256, updates changed files, and never deletes destination files. Android MTP transfer will be implemented separately after read-only inspection is tested with a real phone.

## Run tests

~~~powershell
py -m unittest discover -s tests -v
~~~

The MTP tests use a fake backend and do not require a physical Android phone. Real device detection and folder inspection still need to be verified on Windows with an actual phone.

## Planned workflow

1. Detect an Android phone over USB/MTP.
2. Inspect its available storage and the selected Music destination (read-only prototype).
3. Preview which MP3s are new, changed, or already identical.
4. Copy only approved changes to the phone.
5. Handle disconnect/reconnect safely; never delete phone files automatically.
6. Separately check the configured Spotify playlist and maintain the computer's master music folder.

## Safety and privacy

- The computer's master music folder is the source of truth.
- The Android detection and folder-inspection commands only read device metadata and folder contents.
- Device files must never be automatically deleted.
- Never commit credentials, personal playlist URLs, local paths, logs, or private playlist data.

## Legal note

Only obtain, store, and transfer audio that you have the right to use. Follow Spotify's terms and the terms of any audio source or downloader used.
