# Spotify to Phone Sync

A Windows-first project for keeping a local MP3 library and safely syncing music to Android smartphones over USB using Media Transfer Protocol (MTP).

## Android device detection (read-only milestone)

The first Android feature lists MTP devices visible to Windows and the storage roots exposed by each device. It does not browse personal files, upload music, create folders, or delete anything on the phone.

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

The optional Android extra installs mtp 2.0.9, a separate MIT-licensed package that wraps Windows Portable Devices (WPD) for MTP access. See https://github.com/Heribert17/mtp.

### List connected MTP devices

Connect and unlock the phone, select **File transfer**, then run:

~~~powershell
playlist2phone-devices
~~~

Or:

~~~powershell
py -m playlist2phone.android
~~~

This command is read-only. It reports device names and storage-root names only. Windows may show other portable MTP devices too; the output is not a cryptographic verification that a listed device is an Android phone.

If no device appears, try another USB data cable/port, unlock the phone, select **File transfer (MTP)**, and run the command again.

## Existing local-folder copy utility

The project also contains a generic preview-first MP3 folder-copy engine. This is for ordinary filesystem paths and removable folders; **it does not yet copy directly to Android MTP storage**.

Preview:

~~~powershell
playlist2phone --source "C:\Music\Master" --destination "E:\Music"
~~~

Apply only after creating the marker file in the exact destination folder:

~~~powershell
New-Item -ItemType File -Path "E:\Music\.playlist2phone-target"
playlist2phone --source "C:\Music\Master" --destination "E:\Music" --apply
~~~

The folder-copy utility copies new MP3s, skips identical files using SHA-256, updates changed files, and never deletes destination files. Android MTP transfer will be implemented separately after device detection is tested with a real phone.

## Run tests

~~~powershell
py -m unittest discover -s tests -v
~~~

The MTP discovery tests use a fake backend and do not require a physical Android phone. Real device detection still needs to be verified on Windows with an actual phone.

## Planned workflow

1. Detect an Android phone over USB/MTP. (Read-only prototype.)
2. Identify its available storage and let the user select a Music destination.
3. Preview which MP3s are new, changed, or already identical.
4. Copy only approved changes to the phone.
5. Handle disconnect/reconnect safely; never delete phone files automatically.
6. Separately check the configured Spotify playlist and maintain the computer's master music folder.

## Safety and privacy

- The computer's master music folder is the source of truth.
- The Android detection command only reads device and storage names.
- Device files must never be automatically deleted.
- Never commit credentials, personal playlist URLs, local paths, logs, or private playlist data.

## Legal note

Only obtain, store, and transfer audio that you have the right to use. Follow Spotify's terms and the terms of any audio source or downloader used.
