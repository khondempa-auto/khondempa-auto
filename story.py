"""สร้างเรื่องเล่า + prompt สำหรับ Veo ด้วย Gemini (ข้อความ)"""
import os, json, datetime
from google import genai
from google.genai import types

TEXT_MODEL = os.environ.get("TEXT_MODEL", "gemini-3.8-flash")

TOPICS = [
    "เสียงเรียกชื่อกลางป่าตอนตี 2",
    "เสือสมิง รอยเท้าเสือกลายเป็นรอยเท้าคน",
    "ผีบังตา เดินวนไม่ออกจากป่า ทั้งที่ทางออกอยู่ข้างหน้า",
    "เงาดำในหมอกที่ยืนนิ่งไม่ขยับ",
    "ทางเก่าที่เดินมาตอนเช้า ตอนเย็นหาไม่เจอ",
    "แสงไฟกลางป่าลึกที่ไม่มีหมู่บ้านอยู่ใกล้ๆ",
    "เสียงเคาะเต็นท์กลางดึก ทั้งที่อยู่คนเดียว",
    "ลูกหาบแปลกหน้าที่ไม่มีใครรู้จักเดินตามมา",
    "เสียงกลองจากหุบเขาร้างตอนเที่ยงคืน",
    "นกและจิ้งหรีดเงียบทั้งป่าก่อนเกิดเรื่อง",
    "รอยมือบนเต็นท์ด้านใน ตอนตื่นเช้า",
    "เสียงเดินตามหลังที่หยุดเมื่อเราหยุด",
]

PROMPT = """คุณเป็นนักเขียนเรื่องเล่าสยองขวัญสั้นสำหรับเพจ "คนเดินป่า" (วีดีโอแนวตั้ง 24 วินาที = 3 ช็อต ช็อตละ 8 วินาที)

หัวข้อ: {topic}

ตอบเป็น JSON เท่านั้น โครงสร้าง:
{{
  "title": "ชื่อเรื่องภาษาไทย สั้น ดึงดูด ไม่เกิน 50 ตัวอักษร",
  "caption": "แคปชั่นภาษาไทย 2-3 ประโยค เล่าปมเรื่องแบบทิ้งท้ายให้อยากรู้ต่อ",
  "hashtags": ["คนเดินป่า", "เรื่องเล่าจากป่า", "..."],
  "shots": [
    {{
      "veo_prompt": "English prompt for Veo, see rules below",
      "narration": "คำบรรยายเสียงเล่าเรื่องภาษาไทย 1-2 ประโยค ความยาวไม่เกิน 75 ตัวอักษร",
      "subtitles": ["บรรทัดซับไทยสั้น", "บรรทัดที่สอง", "บรรทัดที่สาม"]
    }}
  ]
}}

กฎของ shots (ต้องมี 3 ช็อตพอดี):
- ช็อต 1 = เปิดเรื่อง/บรรยากาศ, ช็อต 2 = เหตุการณ์ผิดปกติเริ่มขึ้น, ช็อต 3 = จุดพีค ทิ้งท้ายน่าขนลุก (cliffhanger)
- veo_prompt เขียนเป็นภาษาอังกฤษ ละเอียด ถ่ายแนวตั้ง 9:16 แบบกล้องมือถือ/ไฟฉายคาดหัว POV ป่าดิบชื้นเมืองไทยตอนกลางคืนหรือใกล้ค่ำ สมจริงแบบวีดีโอสารคดี/found footage
- ทุก veo_prompt ต้องระบุตัวละครและสถานที่ซ้ำให้เหมือนกัน (เช่น "a Thai male hiker in his 30s, olive rain jacket, headlamp, same dense tropical forest trail") เพื่อให้ภาพต่อเนื่อง
- ระบุเสียงใน prompt: เสียงธรรมชาติเท่านั้น (จิ้งหรีด ลม ฝีเท้า หายใจ) ไม่มีบทพูด ไม่มีเพลง ไม่มีตัวหนังสือบนจอ
- ห้ามภาพเลือด ความรุนแรง ซากศพ ให้น่ากลัวด้วยบรรยากาศ เงา เสียง และสิ่งที่ "ไม่เห็น"
- narration: เสียงเล่าเรื่องบุรุษที่หนึ่ง ภาษาพูดไทยธรรมชาติ น้ำเสียงกระซิบ ตึงเครียด ช็อตแรกต้องเปิดด้วยประโยคที่ดึงความสนใจใน 2 วินาทีแรก ช็อตสุดท้ายจบค้างไว้ ไม่เฉลย
- subtitles: 2-3 บรรทัดต่อช็อต แต่ละบรรทัดไม่เกิน 22 ตัวอักษรไทย เมื่อต่อกันต้องมีเนื้อหาตรงกับ narration ของช็อตนั้น
- veo_prompt ต้องระบุสไตล์กล้อง: handheld smartphone footage, slight shake, shallow depth of field, headlamp beam cutting through mist, film grain, low-light noise, no cinematic color grading, subject partly in shadow
- ในภาพ ห้ามมีข้อความ ตัวอักษร โลโก้ หรือลายน้ำ
- hashtags 5-8 อัน ไม่ต้องมีเครื่องหมาย #
"""


def make_story(slot_index: int = 0) -> dict:
    topic = TOPICS[(datetime.date.today().toordinal() * 2 + slot_index) % len(TOPICS)]
    client = genai.Client()
    last_err = None
    for _ in range(3):
        try:
            resp = client.models.generate_content(
                model=TEXT_MODEL,
                contents=PROMPT.format(topic=topic),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=1.0
                ),
            )
            data = json.loads(resp.text)
            assert len(data["shots"]) == 3, "ต้องมี 3 ช็อต"
            for s in data["shots"]:
                assert s["veo_prompt"] and s["subtitles"]
            data["topic"] = topic
            return data
        except Exception as e:  # noqa
            last_err = e
    raise RuntimeError(f"สร้างเรื่องไม่สำเร็จ: {last_err}")


def build_caption(story: dict) -> str:
    tags = " ".join("#" + t.lstrip("#") for t in story["hashtags"])
    return (
        f"{story['title']} | คนเดินป่า\n\n{story['caption']}\n\n"
        "เรื่องเล่านี้สร้างด้วย AI (ภาพและเสียงสังเคราะห์) เพื่อความบันเทิง\n\n"
        f"{tags} #AI"
    )
