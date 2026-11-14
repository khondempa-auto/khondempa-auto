import os, datetime, sys, subprocess, urllib.request, urllib.parse, json

# เพจ คนเดินป่า - Page ID ตัวจริงจาก Access Token Debugger
PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "1442748642259773")
TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1" or "--dry-run" in sys.argv

STORIES = [
    ("เครือเขาหลง", "คืนนั้นในป่า ผมได้ยินเสียงเรียกชื่อผม ทั้งที่ไม่มีใครอยู่ตรงนั้น"),
    ("เสียงเรียกชื่อตอนตี 2", "ตี 2 ในป่าลึก เสียงเรียกชื่อดังมาจากหลังต้นไม้ใหญ่"),
    ("เสือสมิง", "รอยเท้าเสือที่เห็นตอนเช้า กลับกลายเป็นรอยเท้าคนตอนกลางคืน"),
    ("ผีบังตา", "เดินวนอยู่ 3 ชั่วโมง ทั้งที่ทางออกอยู่แค่ 10 เมตรข้างหน้า"),
    ("ป่าปิด", "ป่าที่เขาเตือนว่าอย่าเข้า หลังพระอาทิตย์ตก มันจะไม่เหมือนเดิม"),
    ("เงาในหมอก", "เงาดำๆ ยืนอยู่ในหมอก มันยืนนิ่ง ไม่ขยับ ไม่หายไป"),
    ("ทางเก่าที่หายไป", "ทางที่เดินมาตอนเช้า ตอนเย็นกลับหาไม่เจออีกเลย"),
]
idx = datetime.date.today().toordinal() % len(STORIES)
title, message = STORIES[idx]
caption = f"""คืนนี้ในป่า... เรื่อง {title} | คนเดินป่า [AI]

{message}

เรื่องนี้คือเรื่องเล่าจากป่า สร้างด้วย AI เพื่อความบันเทิง
โปรดใช้วิจารณญาณในการรับชม

#คนเดินป่า #เรื่องเล่าจากป่า #AI #Reels
"""
print(caption, flush=True)
print(f"Page ID: {PAGE_ID} DRY_RUN: {DRY_RUN}", flush=True)
if DRY_RUN:
    print("DRY_RUN=1 ไม่โพสต์จริง")
    raise SystemExit(0)
if not TOKEN:
    print("ERROR: ไม่มี FACEBOOK_PAGE_ACCESS_TOKEN")
    raise SystemExit(1)

# สร้างรูป + วีดีโอ 1080x1920 15 วิ
from PIL import Image, ImageDraw, ImageFont
W, H = 1080, 1920
img = Image.new("RGB", (W, H), (10, 30, 20))
draw = ImageDraw.Draw(img)
for y in range(H):
    r = int(10 + (y/H)*20); g = int(30 + (y/H)*40); b = int(20 + (y/H)*15)
    draw.line([(0, y), (W, y)], fill=(r, g, b))
draw.ellipse([(W//2-180, 180, W//2+180, 540)], fill=(255, 200, 80), outline=(255, 180, 0), width=6)
def font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()
draw.text((W//2, 700), "Khon Dern Pa", font=font(68), fill=(255, 230, 150), anchor="mm")
draw.text((W//2, 820), "Tonight in the forest...", font=font(44), fill=(200, 220, 180), anchor="mm")
draw.text((W//2, 1000), "Forest Story", font=font(64), fill=(255, 255, 255), anchor="mm")
draw.text((W//2, 1250), "AI Story for Entertainment", font=font(36), fill=(200, 220, 180), anchor="mm")
draw.text((W//2, 1750), "[AI] Khon Dern Pa", font=font(34), fill=(180, 200, 160), anchor="mm")
img.save("khondempa.jpg", quality=92)
print("สร้างรูปแล้ว", flush=True)
res = subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", "khondempa.jpg", "-t", "15", "-vf", "scale=1080:1920,format=yuv420p", "-c:v", "libx264", "-r", "25", "-movflags", "+faststart", "khondempa.mp4"], capture_output=True, text=True)
if res.returncode != 0:
    print(res.stderr[-2000:], flush=True)
    raise SystemExit(1)
print("สร้างวีดีโอแล้ว", flush=True)
file_size = os.path.getsize("khondempa.mp4")
print(f"ขนาดวีดีโอ: {file_size}", flush=True)

def fb_post(url, data_dict):
    data = urllib.parse.urlencode(data_dict).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode()
        print(f"FB {r.status}: {body[:800]}", flush=True)
        return json.loads(body)

def post_text():
    print("โพสต์แบบตัวอักษรสำรอง...", flush=True)
    url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/feed"
    data = urllib.parse.urlencode({"message": caption, "access_token": TOKEN}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Facebook ตอบ {r.status}: {r.read().decode()}", flush=True)
        print("DONE - โพสต์ตัวอักษรแล้ว", flush=True)

def post_videos():
    print("โพสต์แบบ Video...", flush=True)
    import uuid
    boundary = uuid.uuid4().hex
    def part(name, value):
        return f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8")
    body = b""
    body += part("description", caption)
    body += part("access_token", TOKEN)
    with open("khondempa.mp4", "rb") as f:
        vb = f.read()
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"khondempa.mp4\"\r\nContent-Type: video/mp4\r\n\r\n".encode() + vb + f"\r\n--{boundary}--\r\n".encode()
    url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/videos"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        print(f"Video ตอบ {r.status}: {r.read().decode()}", flush=True)
        print("DONE - โพสต์ Video แล้ว", flush=True)

def post_reels():
    print("โพสต์แบบ Reels...", flush=True)
    start_url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/video_reels"
    start = fb_post(start_url, {"access_token": TOKEN, "video_state": "PUBLISHED", "upload_phase": "start", "file_size": str(file_size), "description": caption})
    video_id = start.get("video_id")
    upload_url = start.get("upload_url")
    if not video_id or not upload_url:
        raise RuntimeError(f"start ไม่ได้ video_id/upload_url: {start}")
    print(f"video_id={video_id}", flush=True)
    with open("khondempa.mp4", "rb") as f:
        vb = f.read()
    up_req = urllib.request.Request(upload_url, data=vb, headers={"Authorization": f"OAuth {TOKEN}", "Content-Type": "application/octet-stream", "file_offset": "0"}, method="PUT")
    with urllib.request.urlopen(up_req, timeout=120) as r:
        print(f"Upload PUT {r.status}: {r.read().decode()[:500]}", flush=True)
    finish = fb_post(start_url, {"access_token": TOKEN, "video_state": "PUBLISHED", "upload_phase": "finish", "video_id": video_id, "description": caption})
    print("DONE - โพสต์ Reels แล้ว", flush=True)

try:
    post_reels()
except Exception as e:
    print(f"Reels พัง: {e} -> ลอง Video", flush=True)
    try:
        post_videos()
    except Exception as e2:
        print(f"Video พัง: {e2} -> ลองตัวอักษร", flush=True)
        post_text()
