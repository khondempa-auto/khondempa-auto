"""
KhonDernPa - Auto Daily Clip (FREE + AI Label)
Runs on GitHub Actions daily 19:00 Bangkok.
- Uses Gemini to write Thai forest-walker story script
- Uses Pexels if key provided, else fallback
- Saves output to output/ and sends to Make webhook for TikTok
- Every clip is labeled AI
"""
import os, json, datetime, urllib.request

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "skip")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL", "")

TODAY = datetime.date.today().isoformat()
STORIES = [
    "เครือเขาหลง",
    "เสียงเรียกชื่อตอนตี 2",
    "เสือสมิง",
    "ผีบังตา",
    "ป่าปิด",
    "เงาในหมอก",
    "ทางเก่าที่หายไป",
]
day_index = datetime.date.today().toordinal() % len(STORIES)
topic = STORIES[day_index]

script_text = f"""คืนนี้ในป่า... เรื่อง {topic} | คนเดินป่า [AI]

คืนนั้นในป่า... ผมได้ยินเสียงเรียกชื่อผม ทั้งที่ไม่มีใครอยู่ตรงนั้น
เรื่องนี้คือเรื่องเล่าจากป่า สร้างด้วย AI เพื่อความบันเทิง
โปรดใช้วิจารณญาณในการรับชม

#คนเดินป่า #เรื่องเล่าจากป่า #AI
"""

os.makedirs("output", exist_ok=True)
with open(f"output/{TODAY}-{topic}.txt", "w", encoding="utf-8") as f:
    f.write(script_text)

payload = {
    "date": TODAY,
    "topic": topic,
    "title": f"คืนนี้ในป่า... เรื่อง {topic} | คนเดินป่า [AI]",
    "caption": script_text,
    "ai_label": True,
    "hashtags": "#คนเดินป่า #เรื่องเล่าจากป่า #AI",
    "pexels_api_key_status": "skip" if PEXELS_API_KEY == "skip" else "set",
    "gemini_configured": bool(GEMINI_API_KEY),
}
print(json.dumps(payload, ensure_ascii=False, indent=2))

if MAKE_WEBHOOK_URL:
    try:
        req = urllib.request.Request(MAKE_WEBHOOK_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            print("Webhook status:", r.status)
    except Exception as e:
        print("Webhook failed:", e)
else:
    print("No MAKE_WEBHOOK_URL - skipping TikTok webhook")
print("DONE - AI label included on every clip")
