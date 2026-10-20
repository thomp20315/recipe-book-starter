#!/usr/bin/env python3
"""Pick the best food shot from a video (URL or file) or image candidates.

Usage:
  pick_food_frame.py <video_url_or_file> <out.jpg> [--cover cover.jpg] [--title 'Recipe title'] [--min 0.0]
  pick_food_frame.py --score img1.jpg [img2.jpg ...]     # print food scores

Score = P(food prompts) - P(person prompts) (CLIP ViT-B-32, softmax over all
prompts) + small sharpness bonus. Frames come from ffmpeg at --fps (default 1, max 90 s) plus the last 3 s at 3 fps;
frames with a face also get a face-free crop candidate. Drink prompts count as food.
If --cover is given, the cover is used only if it beats the best frame.
Output: JPEG, long side <= 1200 px, quality 85. Exit 0 on success, 2 if no
candidate scored above --min (default 0.0), 1 on download/extract failure.
Needs the venv at /workspace/venv (torch, open_clip_torch, opencv).
"""
import sys, os, glob, subprocess, tempfile, argparse
FOOD = ["a photo of plated food", "a close-up photo of a finished dish",
        "a bowl of food", "a photo of a meal on a plate", "a photo of baked goods",
        "a photo of food in a pan", "a cocktail in a glass", "a glass of a drink",
        "a latte in a cup", "a smoothie", "a spritz cocktail with ice"]
PERSON = ["a photo of a person talking to the camera", "a selfie", "a close-up of a face",
          "a photo of a woman", "a photo of a man", "a person holding food near their face",
          "a text graphic or screenshot", "raw ingredients being prepared",
          "a kitchen stove or oven", "an empty kitchen counter",
          "food cooking in an air fryer basket", "uncooked food in a pot or slow cooker"]
_m = None
FPS = 1.0
_feat = {}
def model():
    global _m
    if _m is None:
        import torch, open_clip
        m, _, pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        tok = open_clip.get_tokenizer('ViT-B-32')
        with torch.no_grad():
            t = m.encode_text(tok(FOOD + PERSON)); t /= t.norm(dim=-1, keepdim=True)
        _m = (m.eval(), pre, t)
    return _m
def sharp(path):
    import cv2
    g = cv2.imread(path, 0)
    if g is None: return 0.0
    return float(cv2.Laplacian(cv2.resize(g, (320, 320)), cv2.CV_64F).var())
def scores(paths, bs=32):
    import torch
    from PIL import Image
    m, pre, t = model(); out = []
    for i in range(0, len(paths), bs):
        ims = torch.stack([pre(Image.open(p).convert('RGB')) for p in paths[i:i+bs]])
        with torch.no_grad():
            f = m.encode_image(ims); f /= f.norm(dim=-1, keepdim=True)
            for p, v in zip(paths[i:i+bs], f): _feat[p] = v
            pr = (100 * f @ t.T).softmax(-1)
        for p, row in zip(paths[i:i+bs], pr):
            food = float(row[:len(FOOD)].sum()); per = float(row[len(FOOD):].sum())
            out.append({'path': p, 'food': food, 'person': per, 'clip': food - per})
    return out
def title_sim(paths, title):
    import torch, open_clip
    from PIL import Image
    m, pre, _ = model(); tok = open_clip.get_tokenizer('ViT-B-32')
    with torch.no_grad():
        t = m.encode_text(tok([f"a close-up photo of finished {title}, ready to eat"])); t /= t.norm(dim=-1, keepdim=True)
        f = torch.stack([_feat[p] for p in paths])
        return (f @ t.T).squeeze(1).tolist()
def rank(paths, title=None):
    """score = clip(food-other) + 3*(title cosine-0.25) + sharpness bonus + late-frame bonus."""
    s = scores(paths)
    ts = title_sim(paths, title) if title else [0.25] * len(paths)
    n = max(len(paths) - 1, 1)
    for i, (d, t) in enumerate(zip(s, ts)):
        d['sharp'] = sharp(d['path']); d['title'] = t
        bn = os.path.basename(d['path'])
        late = (0.12 if bn.startswith('f9') else 0.05 * i / n) if bn.startswith('f') else 0.03
        d['score'] = d['clip'] + 3 * (t - 0.25) + min(d['sharp'], 400) / 4000 + late
    return sorted(s, key=lambda d: -d['score'])
def face_crop(path):
    """If a face is detected, write a crop of the largest face-free band (below or beside it). Returns new path or None."""
    import cv2
    im = cv2.imread(path); h, w = im.shape[:2]
    cc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    f = cc.detectMultiScale(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), 1.1, 6, minSize=(int(w * .08), int(w * .08)))
    if not len(f): return None
    x, y, fw, fh = max(f, key=lambda r: r[2] * r[3])
    bands = [im[min(h, y + int(fh * 1.6)):, :], im[:max(0, y - int(fh * .3)), :]]
    bands = [b for b in bands if b.shape[0] >= max(w * 0.6, 200)]
    if not bands: return None
    b = max(bands, key=lambda b: b.shape[0]); outp = path[:-4] + '_crop.jpg'; cv2.imwrite(outp, b); return outp
def save(src, out):
    from PIL import Image
    im = Image.open(src).convert('RGB'); im.thumbnail((1200, 1200)); im.save(out, 'JPEG', quality=85)
def frames(src, tmp):
    if not os.path.exists(src):
        vid = os.path.join(tmp, 'v.%(ext)s')
        for _ in range(3):
            r = subprocess.run(['yt-dlp', '-q', '--no-warnings', '--retries', '5', '-f', 'b[height<=1080]/b/bv*',
                                '--max-filesize', '200M', '-o', vid, src], capture_output=True, timeout=240)
            if glob.glob(os.path.join(tmp, 'v.*')): break
        vs = glob.glob(os.path.join(tmp, 'v.*'))
        if not vs: raise RuntimeError('download failed: ' + r.stderr.decode()[-200:])
        src = vs[0]
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', src, '-vf', f'fps={FPS}', '-frames:v', str(int(90 * FPS)),
                    '-q:v', '2', os.path.join(tmp, 'f%03d.jpg')], timeout=300)
    # last ~3 s at 3 fps (finished dish usually shown at the end); named f9xx so they sort last
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-sseof', '-3', '-i', src, '-vf', 'fps=3',
                    '-q:v', '2', '-start_number', '900', os.path.join(tmp, 'f%03d.jpg')], timeout=120)
    fs = sorted(glob.glob(os.path.join(tmp, 'f*.jpg')))
    if not fs: raise RuntimeError('no frames extracted')
    return fs
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src', nargs='+'); ap.add_argument('--cover'); ap.add_argument('--title'); ap.add_argument('--fps', type=float, default=1.0)
    ap.add_argument('--min', type=float, default=0.0); ap.add_argument('--score', action='store_true')
    a = ap.parse_args()
    if a.score:
        for d in rank(a.src, a.title): print(f"{d['score']:+.3f} food={d['food']:.2f} person={d['person']:.2f} {d['path']}")
        return 0
    global FPS; FPS = a.fps
    src, out = a.src[0], a.src[1]
    with tempfile.TemporaryDirectory() as tmp:
        try: fs = frames(src, tmp)
        except Exception as e:
            print('ERR', e, file=sys.stderr); fs = []
        cand = fs + ([a.cover] if a.cover and os.path.exists(a.cover) else [])
        if not cand: return 1
        r = rank(cand, a.title)
        crops = [c for c in (face_crop(d['path']) for d in r[:6]) if c]
        if crops: r = rank(cand + crops, a.title)
        best = r[0]
        print(f"best {best['score']:+.3f} {'cover' if best['path']==a.cover else os.path.basename(best['path'])}")
        if best['score'] < a.min: return 2
        save(best['path'], out)
    return 0
if __name__ == '__main__': sys.exit(main())
