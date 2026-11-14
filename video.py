"""สร้างช็อตด้วย Gemini Omni Flash -> ใส่ซับไทย + เสียงบรรยาย -> ต่อเป็นคลิปเดียว (9:16)"""
import os, glob, time, base64, subprocess
from google import genai
from PIL import Image, ImageDraw, ImageFont

VIDEO_MODEL = os.environ.get("VIDEO_MODEL", "gemini-omni-1.1-flash")
RESOLUTION = os.environ.get("VIDEO_RESOLUTION", "720p")
W, H = 1080, 1920


def _find_font() -> str:
    pats = [
        "/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf",
        "/usr/share/fonts/truetype/tlwg/Garuda-Bold.ttf",
        "/usr/share/fonts/**/NotoSansThai*Bold*.ttf",
        "/usr/share/fonts/**/*Thai*.ttf",
        "/usr/share/fonts/**/Loma*.ttf",
    ]
    for p in pats:
        hits = glob.glob(p, recursive=True)
        if hits:
            return hits[0]
    raise RuntimeError("ไม่พบฟอนต์ไทย (ติดตั้ง fonts-thai-tlwg)")


def _font(size):
    path = _find_font()
    try:
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(path, size)


def caption_png(lines, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font(66)
    y = 1380
    for line in lines:
        d.text((W // 2, y), line, font=f, fill="white", anchor="mm",
               stroke_width=7, stroke_fill="black")
        y += 108
    img.save(path)


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1500:])
    return r.stdout


def duration_of(path: str) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def generate_shot(client, prompt: str, out_path: str):
    full = (prompt + " Vertical 9:16, photorealistic found-footage look, handheld smartphone camera, "
            "natural lighting only, realistic skin and foliage detail. About 8 seconds long. "
            "Audio: natural forest ambience only (insects, wind, footsteps, breathing). "
            "No speech, no music, no on-screen text, no watermark.")
    last = None
    for attempt in range(3):
        try:
            inter = client.interactions.create(
                model=VIDEO_MODEL,
                input=full,
                response_format={"type": "video", "aspect_ratio": "9:16",
                                 "resolution": RESOLUTION, "delivery": "uri"},
            )
            ov = inter.output_video
            uri = getattr(ov, "uri", None)
            if uri:
                file_name = "files/" + uri.split("/files/")[1].split(":")[0].split("?")[0]
                t0 = time.time()
                while True:
                    info = client.files.get(name=file_name)
                    st = info.state.name
                    if st == "ACTIVE":
                        break
                    if st == "FAILED":
                        raise RuntimeError("Gemini สร้างวีดีโอไม่สำเร็จ (FAILED)")
                    if time.time() - t0 > 900:
                        raise TimeoutError("รอวีดีโอนานเกิน 15 นาที")
                    time.sleep(5)
                client.files.download(file=uri, destination=out_path)
            else:
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(ov.data))
            if os.path.getsize(out_path) < 10_000:
                raise RuntimeError("ไฟล์วีดีโอเล็กผิดปกติ")
            return
        except Exception as e:  # noqa
            last = e
            print(f"[video] ครั้งที่ {attempt+1} ล้มเหลว: {e}", flush=True)
            time.sleep(10)
    raise RuntimeError(f"สร้างช็อตไม่สำเร็จ: {last}")


def add_subtitles(src: str, lines, out_path: str, workdir: str):
    dur = duration_of(src)
    n = len(lines)
    pngs = []
    for i, ln in enumerate(lines):
        p = os.path.join(workdir, f"cap_{os.path.basename(src)}_{i}.png")
        caption_png([ln] if isinstance(ln, str) else ln, p)
        pngs.append(p)
    cmd = ["ffmpeg", "-y", "-i", src] + sum([["-i", p] for p in pngs], [])
    fc = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[b]"]
    last = "b"
    for i in range(n):
        a, b = i * dur / n, (i + 1) * dur / n
        fc.append(f"[{last}][{i+1}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{i}]")
        last = f"v{i}"
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", "30", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out_path]
    _run(cmd)


def mix_narration(src: str, wav: str, out_path: str):
    """ลดเสียงป่าลงแล้วใส่เสียงบรรยายทับ เริ่มที่ 0.6 วินาที"""
    _run(["ffmpeg", "-y", "-i", src, "-i", wav, "-filter_complex",
          "[0:a]volume=0.55[a0];[1:a]adelay=600|600,volume=1.8,apad[a1];"
          "[a0][a1]amix=inputs=2:duration=first:normalize=0[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
          "-ar", "44100", "-ac", "2", "-shortest", out_path])


def build_video(story: dict, outdir: str, name: str) -> str:
    from narration import synth
    os.makedirs(outdir, exist_ok=True)
    client = genai.Client()
    parts = []
    for i, shot in enumerate(story["shots"], 1):
        raw = os.path.join(outdir, f"{name}_raw{i}.mp4")
        sub = os.path.join(outdir, f"{name}_sub{i}.mp4")
        print(f"[Video] ช็อต {i}/3 ...", flush=True)
        generate_shot(client, shot["veo_prompt"], raw)
        add_subtitles(raw, shot["subtitles"], sub, outdir)
        if shot.get("narration"):
            try:
                wav = os.path.join(outdir, f"{name}_nar{i}.wav")
                voiced = os.path.join(outdir, f"{name}_voice{i}.mp4")
                synth(client, shot["narration"], wav)
                mix_narration(sub, wav, voiced)
                sub = voiced
            except Exception as e:  # ถ้า TTS พัง ยังโพสต์แบบเสียงป่าได้
                print(f"[TTS] ข้ามเสียงบรรยายช็อต {i}: {e}", flush=True)
        parts.append(sub)
    listfile = os.path.join(outdir, f"{name}_list.txt")
    with open(listfile, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    final = os.path.join(outdir, f"{name}.mp4")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
          "-c", "copy", "-movflags", "+faststart", final])
    print(f"[OK] {final} ({os.path.getsize(final)/1e6:.1f} MB, {duration_of(final):.1f}s)", flush=True)
    return final
