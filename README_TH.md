# Forest Reels — เรื่องเล่าคนเดินป่า วันละ 2 คลิป

Gemini เขียนเรื่อง → Veo สร้างวีดีโอ 3 ช็อต (24 วิ) → เสียงบรรยายไทย + ซับ → โพสต์ Facebook Reels / YouTube Shorts / TikTok
รันบน GitHub Actions เวลา 12:00 และ 19:00 (เวลาไทย)

## ติดตั้ง (ทำตามลำดับ)

### 1) เพิกถอนของเก่าที่รั่ว (สำคัญที่สุด)
- Meta for Developers → แอป → Settings → Basic → **Reset App Secret** (token เก่าทั้งหมดจะใช้ไม่ได้)
- AI Studio → ลบ Gemini API key เก่าทุกอัน แล้วสร้างใหม่ 1 อัน

### 2) อัปโหลดไฟล์ขึ้น repo `khondempa-auto`
- แตก zip แล้วอัปโหลดทุกไฟล์/โฟลเดอร์ (รวม `.github/workflows/reels.yml`)
  - ถ้าเว็บ GitHub ไม่ยอมอัปโหลดโฟลเดอร์ซ่อน ให้ใช้ Add file → Create new file แล้วตั้งชื่อ `.github/workflows/reels.yml` วางเนื้อหาแทน
- **ลบ** `.github/workflows/main.yml` และ `Auto-Khondempa.py` เดิม

### 3) ทำ Facebook Page token แบบไม่หมดอายุ
token ที่เห็นในหน้า Debugger หมดอายุภายใน ~1 ชั่วโมง ใช้กับระบบรายวันไม่ได้
1. Graph API Explorer → เลือกแอป → **User Token** → เพิ่มสิทธิ์ `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` (และ `publish_video` ถ้ามีให้เลือก) → Generate Access Token
2. ในเครื่องที่มี Python รัน `python tools/get_fb_page_token.py`
3. ใส่ App Secret และ User token ตามที่ถาม (พิมพ์แล้วไม่แสดงบนจอ)
4. สคริปต์จะพิมพ์ Page token และต้องขึ้นว่า "ไม่หมดอายุ" → คัดลอกไปวางใน GitHub Secrets ที่เดียว

### 4) GitHub Secrets
Settings → Secrets and variables → Actions:
| ชื่อ | ค่า |
|---|---|
| `GEMINI_API_KEY` | คีย์ใหม่จาก AI Studio (ต้องเปิดบิล) |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | จากข้อ 3 |
| `FACEBOOK_PAGE_ID` | ไม่ต้องใส่ก็ได้ (ตั้งค่าเริ่มต้น 1442748642259773 ไว้แล้ว) |

YouTube/TikTok: เพิ่มภายหลัง (`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`) ถ้าไม่มีค่าระบบจะข้ามแพลตฟอร์มนั้นเอง

### 5) ทดสอบ (Actions → Forest Reels 2x/day → Run workflow)
1. `story_only` — ฟรี ดู log ว่าได้เรื่องไทย
2. `video_only` — เสียงเงิน Veo แต่ไม่โพสต์ โหลดคลิปจาก Artifacts ไปดู
3. `post` — โพสต์ขึ้น Facebook จริง
ดูคลิปหลายรอบก่อนปล่อยให้ระบบรันอัตโนมัติ

## ค่าใช้จ่ายและข้อควรระวัง
- Veo คิดเงินตามวินาที: 2 คลิป × 24 วินาที ต่อวัน ตั้งเพดานงบใน Google Cloud Billing
- ปรับรุ่น/เสียงได้ด้วยตัวแปร: `VEO_MODEL`, `TTS_MODEL`, `TTS_VOICE`, `TEXT_MODEL`
- TikTok ก่อนแอปผ่านการตรวจ โพสต์ได้เฉพาะแบบส่วนตัว (`TIKTOK_PRIVACY=SELF_ONLY`)
- ห้ามวาง token/คีย์ในแชท ในโค้ด หรือในภาพหน้าจอ
