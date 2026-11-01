# Spotify to Phone Sync

A Windows-first tool for keeping a computer music library in sync with phones. The computer's music library is the source of truth; phones are destinations.

## Current status

This is the **first development milestone**. It contains a tested, copy-only sync core for phones or SD cards that appear as a normal drive/folder (USB mass storage).

Included now:
- Preview-first sync: it shows what would be copied until you explicitly pass `--apply`.
- Copies MP3 files from a master library to a marked destination folder.
- Skips files whose contents are already identical.
- Updates changed files with the same relative path.
- Leaves destination-only files alone. It does not mirror or delete.
- Requires a marker file in the exact destination folder to reduce the risk of writing to the wrong place.

Not implemented yet:
- Spotify playlist inspection and audio downloading.
- Automatic USB arrival detection.
- Android MTP transfer (MTP devices do not normally appear as drive letters).
- Device-specific feature-phone workflows.

## Requirements

- Windows 10/11 is the initial target platform.
- Python 3.10 or newer.
- No third-party Python packages are required for this milestone.

## Quick start

1. Clone or download this repository, then open PowerShell in the project folder.
2. Install the local package: `py -m pip install -e .`
3. Copy `config.example.json` to `config.json`.
4. Edit `library_directory` to point to your master MP3 folder.
5. Connect the phone in USB mass-storage mode, or insert its SD card.
6. Create the destination folder on the phone/SD card (for example, `Music/Playlist2Phone`).
7. Inside that exact folder, create a text file named `.playlist2phone-target` containing this exact text:

   ```text
   playlist2phone-target-v1
   ```

8. Set `phone_directory` in `config.json` to that marked folder.
9. Preview the operation:

   ```powershell
   py -m playlist2phone --config config.json
   ```

10. Review the paths and counts. Only when they are correct, perform the copy:

   ```powershell
   py -m playlist2phone --config config.json --apply
   ```

The program never formats a device, changes playlists, or deletes destination files. Disconnecting the phone does not affect the master library.

## Configuration

See [`config.example.json`](config.example.json). Keep your personal `config.json` local. It is ignored by Git.

Paths can be absolute Windows paths (for example, `D:/Music`) or paths relative to the directory from which the program is run. The target directory must already exist and contain the safety marker.

## Run tests

```powershell
py -m unittest discover -s tests -v
```

## Project direction

The planned data flow is:

```text
Spotify playlist
      |
      v
Master MP3 library on computer
      |
      +---- USB mass-storage backend (feature phones / SD cards)
      |
      +---- Android MTP backend (planned separately)
```

Spotify ingestion and each phone transport will be separate modules. MTP will not be treated as a drive letter, and ADB will not be silently substituted for MTP.

## Safety and legal note

Use audio files that you are legally entitled to download and transfer. Users are responsible for complying with Spotify's terms, the terms of any third-party services, and applicable copyright law. This project does not distribute music or Spotify credentials.

## Licensing status

No license file is included yet; the project owner should choose a license before accepting outside contributions or distributing releases.

## Contributing

Issues and pull requests are welcome. Please do not include personal playlist URLs, local paths, logs containing account data, API keys, cookies, or downloaded audio in issues or commits.
