"""Local Narayaneeyam video builder. All paths are relative to config.json."""
import argparse
import hashlib
import json
import logging
import math
from fractions import Fraction
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

AUDIO = {'.mp3', '.m4a', '.wav', '.aac'}
LOG = logging.getLogger('lahari')

def number(name):
    stem = Path(name).stem
    labelled = re.findall(r'(?:dasakam|dashakam|dasak(?:a)?m|దశకం)\s*[-_. ]*([0-9౦-౯]{1,3})(?!\d)', stem, re.I)
    values = labelled or re.findall(r'(?<!\d)[0-9౦-౯]{1,3}(?!\d)', stem)
    values = {int(v) for v in values}
    if len(values) != 1 or not 1 <= next(iter(values), 0) <= 100:
        raise ValueError(f'Cannot safely identify one Dasakam number (1–100): {name}')
    return values.pop()

def plan(paths):
    items = {}
    duplicates = set()
    for p in paths:
        if p.suffix.lower() not in AUDIO:
            continue
        try:
            n = number(p.name)
        except ValueError as exc:
            LOG.warning('SKIP %s', exc)
            continue
        if n in items:
            LOG.warning('SKIP duplicate Dasakam %s: %s and %s. Keep one recording.', n, items[n], p)
            duplicates.add(n)
        items[n] = p
    return sorted((n,p) for n,p in items.items() if n not in duplicates)

def oauth_download(url, destination, dry, excluded, only):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    token = Path('token.json')
    creds = Credentials.from_authorized_user_file(str(token), scopes) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes).run_local_server(port=0)
        token.write_text(creds.to_json(), encoding='utf-8')
    service = build('drive', 'v3', credentials=creds)
    match = re.search(r'/folders/([\w-]+)', url)
    if not match:
        raise ValueError('Expected a Google Drive folder URL')
    records = []
    def walk(folder, parents):
        page = None
        while True:
            response = service.files().list(q=f"'{folder}' in parents and trashed = false", pageToken=page,
                fields='nextPageToken,files(id,name,mimeType,size,md5Checksum)', pageSize=1000,
                supportsAllDrives=True, includeItemsFromAllDrives=True).execute(num_retries=3)
            for f in response.get('files', []):
                if f['mimeType'] == 'application/vnd.google-apps.folder':
                    if f['id'] not in parents:
                        walk(f['id'], parents | {f['id']})
                elif Path(f['name']).suffix.lower() in AUDIO and f['name'] not in excluded:
                    records.append(f)
            page = response.get('nextPageToken')
            if not page:
                break
    walk(match[1], {match[1]})
    # File IDs prevent collisions and unsafe remote names; keep original names for matching.
    valid = {p.name for n,p in plan([Path(f['name']) for f in records]) if only is None or n == only}
    for f in records:
        if f['name'] not in valid:
            continue
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', f['name']).rstrip(' .')
        target = destination / f['id'] / safe
        LOG.info('Drive: %s', f['name'])
        if dry:
            continue
        if target.exists() and target.stat().st_size == int(f.get('size', -1)):
            if not f.get('md5Checksum') or hashlib.md5(target.read_bytes()).hexdigest() == f['md5Checksum']:
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + '.partial')
        with partial.open('wb') as handle:
            dl = MediaIoBaseDownload(handle, service.files().get_media(fileId=f['id'], supportsAllDrives=True))
            done = False
            while not done:
                _, done = dl.next_chunk(num_retries=3)
        if f.get('md5Checksum') and hashlib.md5(partial.read_bytes()).hexdigest() != f['md5Checksum']:
            raise ValueError(f'Download checksum mismatch: {safe}')
        partial.replace(target)

def image(config, n, target):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(config['template']).convert('RGB')
    box = config['number_box']
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height):
        raise ValueError('number_box must fit inside the template')
    draw = ImageDraw.Draw(im)
    for size in range(config['font_size'], 9, -1):
        font = ImageFont.truetype(config['font'], size)
        bounds = draw.textbbox((0, 0), str(n), font=font, stroke_width=config['stroke_width'])
        if bounds[2]-bounds[0] <= x1-x0 and bounds[3]-bounds[1] <= y1-y0:
            break
    else:
        raise ValueError('Number does not fit number_box')
    x = x0 + (x1-x0-(bounds[2]-bounds[0]))/2-bounds[0]
    y = y0 + (y1-y0-(bounds[3]-bounds[1]))/2-bounds[1]
    draw.text((x,y), str(n), font=font, fill=config['fill'], stroke_width=config['stroke_width'], stroke_fill=config['stroke_fill'])
    from PIL import ImageOps
    im = ImageOps.pad(im, (1080,1920), method=Image.Resampling.LANCZOS, color='black')
    im.save(target)

def audio_duration(ffmpeg, path):
    result = subprocess.run([ffmpeg,'-v','error','-nostdin','-i',str(path),'-map','0:a:0',
        '-vn','-progress','pipe:1','-f','null','-'], capture_output=True, text=True)
    times = re.findall(r'out_time_us=(\d+)', result.stdout)
    if result.returncode or not times or int(times[-1]) <= 0:
        raise ValueError('Cannot decode audio: '+result.stderr)
    return int(times[-1])/1000000

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def download_file(gdown, record, target):
    """A blocked file must not prevent other downloads or local rendering."""
    try:
        if not gdown.download(id=record.id, output=str(target), resume=True,
                              use_cookies=False, timeout=60, retries=3):
            raise RuntimeError('Downloader returned no completed file')
        return True
    except Exception as exc:
        LOG.warning('DOWNLOAD FAILED %s: %s. Continuing; rerun later to retry.', record.path, exc)
        return False

def run():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', default=str(Path(__file__).with_name('config.json')))
    ap.add_argument('--download', choices=['shared', 'oauth'])
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--preview', type=int, metavar='NUMBER')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', type=int, metavar='NUMBER', help='Download/render just one Dasakam')
    args = ap.parse_args()
    if args.only is not None and not 1 <= args.only <= 100:
        raise ValueError('--only must be 1–100')
    cfgpath = Path(args.config).resolve()
    os.chdir(cfgpath.parent)
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler('logs/run.log', encoding='utf-8')])
    c = json.loads(cfgpath.read_text(encoding='utf-8'))
    audio, output = Path(c['audio_dir']), Path(c['output_dir'])
    download_failures = []
    if args.preview is not None:
        if not 1 <= args.preview <= 100:
            raise ValueError('Preview number must be 1–100')
        output.mkdir(parents=True, exist_ok=True)
        image(c, args.preview, output / f'preview_{args.preview:03}.png')
        return
    if args.download:
        if args.download == 'oauth':
            oauth_download(c['drive_url'], audio, args.dry_run, c.get('exclude_names', []), args.only)
        else:
            import gdown
            try:
                files = gdown.download_folder(url=c['drive_url'], output=str(audio.resolve()),
                    skip_download=True, use_cookies=False, timeout=60)
            except Exception as exc:
                LOG.warning('Cannot list Drive folder: %s. Continuing with local audio.', exc)
                download_failures.append('Drive folder listing')
                files = []
            files = [f for f in files if Path(f.path).name not in c.get('exclude_names', [])]
            remote = [Path(f.path) for f in files]
            valid = {str(p) for n,p in plan(remote) if args.only is None or n == args.only}
            files = [f for f in files if f.path in valid]
            for f in files:
                n = number(Path(f.path).name)
                LOG.info('PLAN Audio: %s | Dasakam: %s | Image number: %s | Output: Dasakam_%03d.mp4', f.path, n, n, n)
            if not args.dry_run:
                for f in files:
                    if Path(f.path).suffix.lower() not in AUDIO:
                        continue
                    target = Path(f.local_path).resolve()
                    if not target.is_relative_to(audio.resolve()):
                        raise ValueError('Unsafe remote download path')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.is_file() and target.stat().st_size > 0:
                        LOG.info('SKIP downloaded %s', target)
                        continue
                    if not download_file(gdown, f, target):
                        download_failures.append(f.path)
    if download_failures:
        LOG.warning('Downloads pending (%s): %s', len(download_failures), ', '.join(download_failures))
    jobs = plan(p for p in audio.rglob('*') if p.name not in c.get('exclude_names', [])) if audio.exists() else []
    jobs = [(n,p) for n,p in jobs if args.only is None or n == args.only]
    if not jobs:
        LOG.info('No local audio found. Use --download shared or place recordings in audio/.')
        return
    if args.dry_run:
        for n, src in jobs:
            LOG.info('PLAN %s -> Dasakam_%03d.mp4', src, n)
        return
    import imageio_ffmpeg
    ffmpeg = c.get('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe()
    output.mkdir(parents=True, exist_ok=True)
    numbered = Path('numbered_images')
    numbered.mkdir(exist_ok=True)
    errors = 0
    for n, src in jobs:
        dest = output / f'Dasakam_{n:03}.mp4'
        receipt = dest.with_suffix('.json')
        previous = output / f'Narayaneeyam_Dasakam_{n:03}.mp4'
        if previous.exists() and not dest.exists():
            previous.rename(dest)
            previous_receipt = previous.with_suffix('.json')
            if previous_receipt.exists() and not receipt.exists():
                previous_receipt.rename(receipt)
            LOG.info('RENAMED %s -> %s', previous.name, dest.name)
        signature = {'audio':digest(src), 'template':digest(c['template']), 'font':digest(c['font']), 'settings':c, 'number':n}
        try:
            if not args.force and dest.exists() and receipt.exists():
                saved = json.loads(receipt.read_text(encoding='utf-8'))
                if saved.get('inputs') == signature and saved.get('video_sha256') == digest(dest):
                    LOG.info('SKIP completed %s', dest)
                    continue
            with tempfile.TemporaryDirectory(prefix='lahari-', dir=output) as temp:
                duration = audio_duration(ffmpeg, src)
                # Distribute an integer count of static frames over the exact audio duration.
                # This avoids rounding the ending to a whole second at a fixed 1 fps.
                frames = max(1, math.ceil(duration * c['fps']))
                rate = (Fraction(frames) / Fraction(str(duration))).limit_denominator(1000000)
                still = numbered / f'Dasakam_{n:03}.png'
                video = Path(temp)/'video.mp4'
                image(c, n, still)
                probe = subprocess.run([ffmpeg,'-hide_banner','-i',str(src)], capture_output=True, text=True)
                audio_options = ['-c:a','copy'] if re.search(r'Audio: aac\b', probe.stderr) else ['-c:a','aac','-b:a','192k']
                command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                    '-loop', '1', '-framerate', str(rate), '-i', str(still), '-i', str(src),
                    '-map', '0:v:0', '-map', '1:a:0',
                    '-c:v', 'libx264', '-tune', 'stillimage', '-preset', 'medium', '-crf', str(c['crf']),
                    '-pix_fmt', 'yuv420p', *audio_options, '-t', str(duration),
                    '-video_track_timescale', '1000000', '-movflags', '+faststart', str(video)]
                LOG.info('RENDER Audio: %s | Dasakam: %s | Image number: %s | Output: %s | Audio seconds: %.3f', src, n, n, dest, duration)
                result = subprocess.run(command, capture_output=True, text=True, errors='replace')
                if result.returncode:
                    raise RuntimeError(result.stderr)
                check = subprocess.run([ffmpeg, '-v','error','-i',str(video),'-map','0:v:0','-map','0:a:0',
                    '-fps_mode','passthrough','-enc_time_base:v','1:1000000','-f','null','-'], capture_output=True, text=True)
                if check.returncode or check.stderr.strip():
                    raise RuntimeError('Output validation failed: '+check.stderr)
                video.replace(dest)
                receipt.write_text(json.dumps({'inputs':signature,'video_sha256':digest(dest)}, indent=2), encoding='utf-8')
        except Exception:
            LOG.exception('FAILED Dasakam %s', n)
            errors += 1
    if errors:
        raise RuntimeError(f'{errors} video(s) failed; see logs/run.log. Rerun to retry.')
    if download_failures:
        raise RuntimeError('Local video processing finished, but some downloads are pending. See logs/run.log and rerun later.')

if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        LOG.error('%s', exc)
        sys.exit(1)
