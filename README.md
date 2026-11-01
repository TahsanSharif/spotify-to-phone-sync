# Spotify to Phone Sync

Windows-first tools for maintaining a local MP3 master folder and syncing music to Android phones over USB MTP.

## Install

Windows 10/11, Python 3.10+, USB data cable, Android phone unlocked with **File transfer (MTP)** selected.

~~~powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[android]"
~~~

The MTP adapter is vendored from MIT-licensed [Heribert17/mtp](https://github.com/Heribert17/mtp), pinned to commit \`9d05c1e9495d1c7614f3af1b42eae28c66742fa8\`; see \`THIRD_PARTY_LICENSES/mtp-MIT.txt\`.

## Detect and inspect

~~~powershell
playlist2phone-devices
playlist2phone-inspect --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist"
~~~

## Preview (read-only)

~~~powershell
playlist2phone-android-preview --source "C:\Music\Master" --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist"
~~~

Statuses are \`NEW\`, \`SIZE_DIFFERS\`, and \`SAME_SIZE_UNVERIFIED\`. Matching filename and size do not prove identical contents.

## Copy missing files to Android

The transfer command is **dry-run by default**:

~~~powershell
playlist2phone-android-transfer --source "C:\Music\Master" --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist"
~~~

After reviewing the dry run, add \`--apply\` to create missing folders and copy only MP3s whose relative paths are not already on the phone:

~~~powershell
playlist2phone-android-transfer --source "C:\Music\Master" --device "Tauhida's A23" --storage "Internal storage" --path "Music/Proplaylist" --apply
~~~

Safety:
- No phone files are deleted.
- Existing paths are never overwritten.
- Same-size existing files are skipped (not hash-verified).
- Same-name files with different sizes are conflicts and remain untouched.
- Uploaded file size is checked after transfer.
- An interrupted MTP upload may leave a partial file; inspect the phone before retrying. The program does not delete partial files automatically.

## Existing local-folder utility

~~~powershell
playlist2phone --source "C:\Music\Master" --destination "E:\Music"
~~~

The generic filesystem utility previews by default and is separate from Android MTP.

## Tests

~~~powershell
py -m unittest discover -s tests -v
~~~

MTP tests use a fake backend. Test with a small temporary folder on a real phone before transferring a whole library.

## Privacy and legal

Never commit credentials, personal playlist URLs, local paths, logs, or private playlist data. Only transfer audio you have the right to use and follow applicable service terms.
