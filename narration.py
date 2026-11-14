"""เสียงบรรยายไทยด้วย Gemini TTS -> ไฟล์ wav"""
import os, wave
from google.genai import types

TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-3.8-flash-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Charon")  # เสียงชายทุ้ม


def synth(client, text: str, out_wav: str):
    style = "พูดภาษาไทยเสียงกระซิบ ตึงเครียด จังหวะช้า เหมือนเล่าเรื่องผีกลางป่า: "
    resp = client.models.generate_content(
        model=TTS_MODEL,
        contents=style + text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
                )
            ),
        ),
    )
    data = resp.candidates[0].content.parts[0].inline_data.data
    if data[:4] == b"RIFF":  # ได้ WAV พร้อม header แล้ว
        with open(out_wav, "wb") as f:
            f.write(data)
        return
    with wave.open(out_wav, "wb") as w:  # PCM ดิบ 16-bit 24kHz mono
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(data)
