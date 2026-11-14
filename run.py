"""ตัวคุมหลัก: เรื่อง -> วีดีโอ Veo -> โพสต์ทุกแพลตฟอร์ม

ENV:
  SLOT      noon | evening       (รอบของวัน)
  MODE      story_only | video_only | post   (ค่าเริ่มต้น post)
  PLATFORMS facebook,youtube,tiktok (ค่าเริ่มต้นทั้งหมด; ข้ามอัตโนมัติถ้าไม่มี secret)
"""
import os, sys, json, traceback
from story import make_story, build_caption
from video import build_video
import posters

SLOT = os.environ.get("SLOT", "noon")
MODE = os.environ.get("MODE", "post")
PLATFORMS = [p.strip() for p in os.environ.get("PLATFORMS", "facebook,youtube,tiktok").split(",")]
OUT = "out"

REQUIRED = {
    "facebook": ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"],
    "youtube": ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"],
    "tiktok": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"],
}


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("ไม่มี GEMINI_API_KEY")
    os.makedirs(OUT, exist_ok=True)
    story = make_story(0 if SLOT == "noon" else 1)
    caption = build_caption(story)
    with open(f"{OUT}/story_{SLOT}.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print(caption, flush=True)
    if MODE == "story_only":
        print("MODE=story_only: ไม่สร้างวีดีโอ (ไม่เสียค่า Veo)")
        return

    path = build_video(story, OUT, f"reel_{SLOT}")
    if MODE == "video_only":
        print("MODE=video_only: สร้างคลิปแล้ว ไม่โพสต์")
        return

    failures = []
    for p in PLATFORMS:
        missing = [k for k in REQUIRED[p] if not os.environ.get(k)]
        if missing:
            print(f"[{p}] ข้าม: ไม่มี {missing}")
            continue
        try:
            if p == "facebook":
                posters.facebook(path, caption)
            elif p == "youtube":
                posters.youtube(path, story["title"], caption, story["hashtags"])
            elif p == "tiktok":
                posters.tiktok(path, caption)
        except Exception:
            failures.append(p)
            print(f"[{p}] ล้มเหลว:\n{traceback.format_exc()}", flush=True)
    if failures:
        sys.exit(f"โพสต์ไม่สำเร็จ: {failures}")


if __name__ == "__main__":
    main()
