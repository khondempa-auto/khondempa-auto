"""โพสต์วีดีโอไป Facebook Reels / YouTube Shorts / TikTok"""
import os, requests

FB_VER = "v21.0"


def facebook(path: str, caption: str):
    page = os.environ["FACEBOOK_PAGE_ID"]
    tok = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]
    base = f"https://graph.facebook.com/{FB_VER}/{page}/video_reels"
    size = os.path.getsize(path)
    s = requests.post(base, data={"access_token": tok, "upload_phase": "start"}, timeout=60)
    s.raise_for_status()
    j = s.json()
    video_id, upload_url = j["video_id"], j["upload_url"]
    with open(path, "rb") as f:
        r = requests.post(upload_url, data=f, timeout=600, headers={
            "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)})
    r.raise_for_status()
    fin = requests.post(base, timeout=60, data={
        "access_token": tok, "video_id": video_id, "upload_phase": "finish",
        "video_state": "PUBLISHED", "description": caption})
    fin.raise_for_status()
    print("[FB] ", fin.text[:300], flush=True)


def youtube(path: str, title: str, description: str, tags: list):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": f"{title} #Shorts"[:100],
            "description": description[:4900],
            "tags": [t.lstrip("#") for t in tags][:15],
            "categoryId": "24",
        },
        "status": {
            "privacyStatus": os.environ.get("YT_PRIVACY", "public"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # ติดป้ายว่าเป็นเนื้อหาสังเคราะห์/AI
        },
    }
    req = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(path, mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    print("[YT] video id:", resp.get("id"), flush=True)


def tiktok(path: str, title: str):
    # ขอ access token ใหม่จาก refresh token
    r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", timeout=30, data={
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"]})
    r.raise_for_status()
    tok = r.json()["access_token"]
    size = os.path.getsize(path)
    init = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/", timeout=60,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"},
        json={
            "post_info": {
                "title": title[:2200],
                # แอปที่ยังไม่ผ่านการตรวจ TikTok โพสต์ได้เฉพาะ SELF_ONLY
                "privacy_level": os.environ.get("TIKTOK_PRIVACY", "SELF_ONLY"),
                "is_aigc": True,  # ติดป้ายเนื้อหาที่สร้างด้วย AI
            },
            "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                            "chunk_size": size, "total_chunk_count": 1},
        })
    init.raise_for_status()
    d = init.json()
    if d.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(d)
    up = d["data"]["upload_url"]
    with open(path, "rb") as f:
        put = requests.put(up, data=f, timeout=600, headers={
            "Content-Type": "video/mp4", "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size-1}/{size}"})
    put.raise_for_status()
    print("[TT] publish_id:", d["data"].get("publish_id"), flush=True)
