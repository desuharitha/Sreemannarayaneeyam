# Sreemannarayaneeyam video tool

A small Windows 11 tool using Python, Pillow and local FFmpeg. No paid APIs, subscriptions, cloud rendering or billing setup. The only ongoing resources are your computer's electricity, disk space and internet access. The template and your Drive URL are already configured.

## Start in three steps

1. Install Python 3.11 or newer from https://www.python.org/downloads/windows/ if needed. Enable **Add Python to PATH**. Double-click **setup.bat** once. It installs free dependencies into `.venv` in this folder, including a roughly 31 MB FFmpeg package; no separate FFmpeg installation or system configuration is needed.
2. Open the included `videos/Narayaneeyam_Dasakam_001.mp4` sample. Double-click **test_one.bat** to test Dasakam 1 on your computer. It skips the included completed sample when inputs are unchanged.
3. Double-click **run.bat** to download missing recordings and build the batch. Finished MP4s appear in `videos`. When you add new recordings to Drive, double-click it again.

Do not run two copies at once. You may move the entire folder elsewhere; keep its contents together. Keep the small JSON receipt next to each MP4 so completed outputs can be verified and skipped.

## What it does

- Finds the number in each filename, sorts numerically, draws that same number and names the video `Narayaneeyam_Dasakam_001.mp4` through `100.mp4`.
- Handles MP3, M4A, WAV and AAC. Existing AAC audio is copied to MP4; other audio is converted once to AAC at 192 kb/s.
- Preserves the Telugu lettering baked into the image. Only the Arabic numeral is drawn in maroon with a gold outline. The completed image is proportionally fitted to 1080×1920 without cropping, then encoded as H.264 with approximately 1 static frame per second and fast-start MP4 playback.
- Measures decoded audio duration and distributes static frames over that duration. Tiny differences due to AAC packets and container time bases are normal; the complete recording is retained.
- Skips unknown/ambiguous numbers and all recordings for duplicate numbers, reporting them in `logs/run.log`. It does not guess or choose between duplicate recordings.
- Excludes `Naarayaneeyam dyana slokas.m4a`, which is not a numbered Dasakam.
- Downloads only numbered audio. Completed downloads are reused; interrupted shared downloads resume. A failed download stops that run so you can retry. Videos render to temporary files and only become completed outputs after a full decode check.
- Verifies source, template, font, settings and output hashes before skipping completed videos. A changed local recording or changed overlay settings triggers rendering again.

Filename examples: `Dasakam 7.mp3`, `Narayaneeyam dasakam 42.m4a`, `దశకం - ౪౨.wav`. A labelled number takes priority over unrelated digits; unlabelled filenames must contain exactly one distinct number from 1–100. Filename matching cannot verify whether a recording's spoken content agrees with its filename; check the supplied recordings' labels.

## Preview and dry run

Double-click `preview.bat` to view a “100” preview (the widest number). Double-click `dry_run.bat` to list the Drive plan without downloading audio or rendering. Dry run still contacts Drive and writes the log.

From a terminal opened in this folder:

```powershell
.\.venv\Scripts\python.exe dasakam.py --preview 12
.\.venv\Scripts\python.exe dasakam.py --download shared --dry-run
.\.venv\Scripts\python.exe dasakam.py --download shared --only 12
.\.venv\Scripts\python.exe dasakam.py --only 1 --force
.\.venv\Scripts\python.exe dasakam.py
```

The last command processes only local files in `audio`, without accessing Drive. Put manually downloaded recordings there if needed.

## Adjust number placement

Edit `config.json` in Notepad. `number_box` is `[left, top, right, bottom]` in the original template's pixel coordinates. The number is centered in this box and shrinks if necessary to fit three digits. Current box: `[700,1195,790,1295]`. Change `font_size`, `fill` (maroon), `stroke_fill` (gold) or `stroke_width` as desired. `font` points to Windows Times New Roman Bold. Set a different local font file if unavailable. Preview again before batching.

`fps` is the target low frame rate; actual timing adjusts slightly to match audio duration. Increase to 2 or 5 only if a particular upload service needs it. `crf` controls image compression: 20 is the default; higher values reduce file size and detail.

## Drive access and changed recordings

Your supplied folder was successfully listed and Dasakam 1 downloaded without authentication. Keep that folder shareable to people with its link, with downloading allowed. Google may impose download quotas; wait and retry if that happens. Shared downloading uses [gdown](https://pypi.org/project/gdown/).

Existing shared downloads are reused rather than checked for remote edits on every run. If you replace a recording in Drive while keeping the same filename, remove its local copy from `audio` and run again. The changed audio hash will trigger a new video. `--force` forces video rendering, not downloading. Remove both copies of a duplicate from local/Drive folders except the recording you intend to use.

## Optional private-folder OAuth fallback

This is unnecessary for the supplied public folder and is not installed by default. No billing account is required for this tool. Follow Google's [Drive Python quickstart](https://developers.google.com/workspace/drive/api/quickstart/python) for the current screens:

1. Create a Google Cloud project and enable **Google Drive API**.
2. Configure OAuth consent. For a personal Gmail account use External/Testing, add your account as a test user, and add the `https://www.googleapis.com/auth/drive.readonly` scope. A Workspace organization can use Internal when available.
3. Create an OAuth client of type **Desktop app**, download its JSON and save it here as `credentials.json`.
4. Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-oauth.txt
.\.venv\Scripts\python.exe dasakam.py --download oauth --only 1
```

Sign in as an account that can access the folder. The read-only scope allows access to readable Drive files; the tool only downloads the configured folder. `token.json` stores authorization locally; keep it and `credentials.json` private. Testing-mode consent may require reauthorization. For subsequent OAuth batches replace `shared` with `oauth` in `run.bat`. Avoid switching modes with an already populated audio folder because the two modes use different folder layouts; consolidate local copies first to prevent duplicates.

## Included verification

One complete real recording, Dasakam 1, was downloaded and rendered first; the entire batch was not processed. The sample uses the supplied audio and template. Verification covers 1080×1920 resolution, H.264/AAC streams, complete decoding, number placement and audio duration. Short test recordings also cover all four audio formats, ambiguity/duplicate handling and completed-output skipping. OAuth is provided but has not been tested against a private account.

Folders: `assets` (original template), `audio` (recordings), `numbered_images` (numbered stills), `videos` (MP4s and receipts), `logs` (run history). `setup.bat`, `test_one.bat`, `run.bat`, `dry_run.bat` and `preview.bat` provide the Windows actions.



