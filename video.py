"""สร้างช็อตด้วย Veo -> ใส่ซับไทย -> ต่อเป็นคลิปเดียว (9:16)"""
import os, glob, time, subprocess
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-fast-generate-preview")
W, H = 1080, 1920
SHOT_SECONDS = 8


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


def caption_png(lines, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(_find_font(), 66, layout_engine=ImageFont.Layout.RAQM)
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


def generate_shot(client, prompt: str, out_path: str):
    full = (prompt + " Vertical 9:16, photorealistic found-footage look, handheld smartphone camera, "
            "natural lighting only, realistic skin and foliage detail. Audio: natural forest ambience only "
            "(insects, wind, footsteps, breathing). No speech, no music, no on-screen text, no watermark.")
    op = client.models.generate_videos(
        model=VEO_MODEL,
        prompt=full,
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16", duration_seconds=SHOT_SECONDS, resolution="720p"
        ),
    )
    t0 = time.time()
    while not op.done:
        if time.time() - t0 > 900:
            raise TimeoutError("Veo ใช้เวลานานเกิน 15 นาที")
        time.sleep(10)
        op = client.operations.get(op)
    vids = getattr(op.response, "generated_videos", None)
    if not vids:
        raise RuntimeError(f"Veo ไม่คืนวีดีโอ (อาจโดนตัวกรองความปลอดภัย): {op.response}")
    v = vids[0]
    client.files.download(file=v.video)
    v.video.save(out_path)


def add_subtitles(src: str, lines, out_path: str, workdir: str):
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
        a, b = i * SHOT_SECONDS / n, (i + 1) * SHOT_SECONDS / n
        fc.append(f"[{last}][{i+1}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{i}]")
        last = f"v{i}"
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", "30", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out_path]
    _run(cmd)


def mix_narration(src: str, wav: str, out_path: str):
    """ลดเสียงป่า (Veo) ลงแล้วใส่เสียงบรรยายทับ เริ่มที่ 0.6 วินาที"""
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
        print(f"[Veo] ช็อต {i}/3 ...", flush=True)
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
    print(f"[OK] {final} ({os.path.getsize(final)/1e6:.1f} MB)", flush=True)
    return final
