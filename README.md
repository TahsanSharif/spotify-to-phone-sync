# Spotify to Phone Sync

A Windows-first project for maintaining a local music library from a Spotify playlist and safely copying it to a connected phone or removable-storage music player.

## Planned workflow

1. Check a configured Spotify playlist.
2. Obtain audio files through a separately configured, legally permitted source.
3. Keep a master music folder on the computer.
4. Detect a connected device and copy only new or changed files.
5. Preview changes before applying them.

## Safety principles

- The computer's master music folder is the source of truth.
- Copying is the default; device files are not automatically deleted.
- A dry-run/preview should be available before copying.
- Device destinations should be explicitly configured and validated.
- Never commit credentials, personal playlist URLs, local paths, logs, or private playlist data.

## Device support

- USB mass-storage devices and SD cards: planned initial transfer target.
- Android MTP: planned separately. It is not equivalent to a normal drive-letter device and will not be described as supported until implemented and tested.

## Project status

Initial repository documentation only. Implementation and automated tests are not yet included.

## Legal note

Only obtain, store, and transfer audio that you have the right to use. Follow Spotify's terms and the terms of any audio source or downloader used.
