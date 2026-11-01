"""Angootha: read a paper aloud and flag its dangers before someone puts a thumbprint on it.

Sarvam Vision (doc_ai parse) -> Sarvam-105B risk report -> Bulbul speech -> Saaras + 105B teach-back check.
"""
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

load_dotenv(Path(__file__).parent / ".env")
try:  # Streamlit Cloud keeps the key in st.secrets
    import streamlit as st
    os.environ.setdefault("SARVAM_API_KEY", st.secrets.get("SARVAM_API_KEY", ""))
except Exception:
    pass
client = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY", ""), timeout=240)

LANGS = {"hi-IN": "Hindi", "mr-IN": "Marathi", "bn-IN": "Bengali", "gu-IN": "Gujarati", "kn-IN": "Kannada",
         "ml-IN": "Malayalam", "od-IN": "Odia", "pa-IN": "Punjabi", "ta-IN": "Tamil", "te-IN": "Telugu",
         "en-IN": "English"}
SAMPLES = Path(__file__).parent / "samples"
TERMINAL = ("completed", "partially_completed", "failed", "rejected")


class AngoothaError(Exception):
    """Message is safe to show to users."""


def _call(fn, retries=3, **kwargs):
    for attempt in range(retries):
        try:
            return fn(**kwargs)
        except ApiError as e:
            code = e.status_code
            if code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt); continue
            if code == 402: raise AngoothaError("Sarvam credits are used up. Please top up and try again.")
            if code in (401, 403): raise AngoothaError("The Sarvam API key is missing or invalid.")
            if code in (400, 422): raise AngoothaError("Sarvam could not accept this input. Try a clearer photo or shorter audio.")
            raise AngoothaError(f"Sarvam API error ({code}). Please try again.")
        except httpx.TimeoutException:
            raise AngoothaError("Sarvam is taking too long right now. Please try again in a moment.")
        except httpx.TransportError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt); continue
            raise AngoothaError("Network problem reaching Sarvam. Check the internet connection.")


def read_document(image_bytes, filename="document.png", language="en-IN", timeout_s=90):
    """Sarvam Vision OCR. Returns (blocks, timings_ms); each block has text and bbox_norm [x0,y0,x1,y1]."""
    if not image_bytes:
        raise AngoothaError("Please add a photo of the document.")
    t0 = time.time()
    mime = "application/pdf" if filename.lower().endswith(".pdf") else \
        "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
    job = _call(client.doc_ai.parse, file=[(filename, image_bytes, mime)], language=language)
    while True:
        st_ = _call(client.doc_ai.get_status, job_id=job.job_id)
        if st_.status in TERMINAL: break
        if time.time() - t0 > timeout_s:
            raise AngoothaError("Reading the document is taking too long. Please try again.")
        time.sleep(1.5)
    if st_.status in ("failed", "rejected"):
        raise AngoothaError("Sarvam Vision could not read this document. Try a sharper, well-lit photo.")
    # SDK 0.1.41 rejects the 'digitise' result type, so fetch the JSON over the SDK's own HTTP client.
    w = client.doc_ai._raw_client._client_wrapper
    def _get():
        r = w.httpx_client.request(f"doc-ai/v1/job/{job.job_id}/results", base_url=w.get_environment().base,
                                   method="GET", params={"format": "json"})
        if r.status_code >= 300:
            raise ApiError(status_code=r.status_code, headers=dict(r.headers), body=r.text)
        return r.json()
    data = _call(_get)
    blocks = [{"id": b["block_id"], "text": b["text"].strip(), "bbox": b["bbox_norm"], "page": p["page_num"]}
              for d in data.get("documents", []) for p in d.get("pages", []) for b in p.get("blocks", [])
              if b.get("text", "").strip()]
    if not blocks:
        raise AngoothaError("No text found in this photo. Try again with the whole page in view.")
    return blocks, {"vision": int((time.time() - t0) * 1000)}


def _chat_json(system, user, schema, name):
    r = _call(client.chat.completions, model="sarvam-105b",
              messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
              response_format={"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}},
              temperature=0.2, reasoning_effort="low", max_tokens=12000)
    content = r.choices[0].message.content
    u = r.usage
    print(f"[105b] finish={r.choices[0].finish_reason} out={u.completion_tokens} "
          f"reasoning={getattr(u.completion_tokens_details, 'reasoning_tokens', None)}", file=sys.stderr)
    if not content:
        raise AngoothaError("The AI could not finish its answer. Please try again.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise AngoothaError("The AI gave an unreadable answer. Please try again.")


def _translate_all(texts, lang):
    """Mayura, in parallel. English passes through."""
    if lang == "en-IN" or not texts:
        return list(texts)
    from concurrent.futures import ThreadPoolExecutor
    def one(t):
        if not t.strip(): return t
        return _call(client.text.translate, input=t[:1000], source_language_code="en-IN",
                     target_language_code=lang, model="mayura:v1", mode="formal").translated_text
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, texts))


def analyze(blocks, lang="hi-IN"):
    """Sarvam-105B finds clauses that hurt the signer (in English), Mayura translates. Returns (report, timings_ms)."""
    t0 = time.time()
    ids = [b["id"] for b in blocks]
    say = {"type": "string"}
    schema = {"type": "object", "required": ["summary", "flags", "questions"], "properties": {
        "summary": say,
        "flags": {"type": "array", "items": {"type": "object", "required": ["block_id", "severity", "title", "explain"],
                  "properties": {"block_id": say, "severity": say, "title": say, "explain": say}}},
        "questions": {"type": "array", "items": say}}}
    system = ("You protect a person who cannot read, before they sign a document. Using ONLY the document blocks given, "
              "identify clauses that harm the signer (high interest, penalties, loss of property, waived rights, one-sided "
              "changes) and a blank signer name. Cite the exact block_id. severity is red or amber. Explain in very simple "
              "words with concrete rupee examples. summary: 3 short sentences. questions: 2 questions. Be brief.")
    report = _chat_json(system, "\n".join(f"[{b['id']}] {b['text']}" for b in blocks), schema, "riskreport")
    t1 = time.time()
    flags = []
    for f in report.get("flags", []):
        f["block_id"] = f.get("block_id", "").strip("[] ")
        f["severity"] = "red" if "red" in f.get("severity", "").lower() else "amber"
        if f["block_id"] in ids: flags.append(f)
    flags.sort(key=lambda f: f["severity"] != "red")
    flags = flags[:8]
    qs = report.get("questions", [])[:3]
    texts = [report.get("summary", "")] + [x for f in flags for x in (f["title"], f["explain"])] + qs
    out = _translate_all(texts, lang)
    report = {"summary": out[0], "flags": [], "questions": out[1 + 2 * len(flags):],
              "summary_en": texts[0]}
    for i, f in enumerate(flags):
        report["flags"].append({**f, "title": out[1 + 2 * i], "explain": out[2 + 2 * i],
                                "title_en": f["title"], "explain_en": f["explain"]})
    return report, {"analyze": int((t1 - t0) * 1000), "translate": int((time.time() - t1) * 1000)}


def draw_flags(image_bytes, blocks, flags):
    """Draw red/amber boxes on the photo over flagged clauses. Returns PNG bytes (page 1 only)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    by_id = {b["id"]: b for b in blocks}
    colors = {"red": (220, 38, 38), "amber": (217, 119, 6)}
    for n, f in enumerate(flags, 1):
        b = by_id.get(f["block_id"])
        if not b or b["page"] != 1: continue
        x0, y0, x1, y1 = b["bbox"]
        c = colors.get(f["severity"], colors["amber"])
        pad = max(4, W // 150)
        box = (x0 * W - pad, y0 * H - pad, x1 * W + pad, y1 * H + pad)
        d.rectangle(box, fill=c + (45,), outline=c + (255,), width=max(3, W // 300))
        r = max(14, W // 60)
        cx, cy = box[0] - r - 4 if box[0] > 2 * r + 8 else box[0] + r, box[1] + r
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c + (255,))
        d.text((cx, cy), str(n), fill="white", anchor="mm", font_size=int(r * 1.2))
    out = io.BytesIO()
    Image.alpha_composite(img, overlay).convert("RGB").save(out, "PNG")
    return out.getvalue()


def speak(text, lang="hi-IN"):
    """Bulbul v4 Flash. Returns (wav_bytes, timings_ms)."""
    if not text.strip():
        raise AngoothaError("Nothing to read aloud.")
    t0 = time.time()
    r = _call(client.text_to_speech.convert, text=text[:2000], language_code=lang, model="bulbul:v4-flash")
    if not r.audios:
        raise AngoothaError("Could not create the audio. Please try again.")
    return base64.b64decode("".join(r.audios)), {"speak": int((time.time() - t0) * 1000)}


def teach_back(audio_bytes, report, lang="hi-IN"):
    """User explains the paper in their own words; Saaras transcribes, 105B checks understanding.
    Returns (transcript, verdict, timings_ms)."""
    if not audio_bytes:
        raise AngoothaError("Please record your explanation first.")
    t0 = time.time()
    r = _call(client.speech_to_text.transcribe, file=("input.wav", audio_bytes, "audio/wav"),
              model="saaras:v4", mode="transcribe", language_code=lang)
    transcript = (r.transcript or "").strip()
    t1 = time.time()
    if not transcript:
        raise AngoothaError("I could not hear anything. Please speak a little louder and try again.")
    say = {"type": "string"}
    schema = {"type": "object", "required": ["understood", "missed", "feedback"], "properties": {
        "understood": {"type": "boolean"}, "missed": {"type": "array", "items": say}, "feedback": say}}
    system = ("A person who cannot read explained in their own words what a document they will sign means. "
              "Check if they understood the RED risks listed. understood = true only if they mention the key red risks. "
              "missed: risks they did not mention (short phrases). feedback: 2 short warm sentences, praising what they "
              "got right and repeating what they missed. Be brief.")
    risks = "\n".join(f"- ({f['severity']}) {f.get('title_en', f['title'])}: {f.get('explain_en', f['explain'])}"
                      for f in report["flags"])
    verdict = _chat_json(system, f"Risks:\n{risks}\n\nThey said:\n{transcript}", schema, "teach_back")
    out = _translate_all([verdict.get("feedback", "")] + list(verdict.get("missed", [])), lang)
    verdict = {"understood": bool(verdict.get("understood")), "feedback": out[0], "missed": out[1:]}
    return transcript, verdict, {"listen": int((t1 - t0) * 1000), "check": int((time.time() - t1) * 1000)}


if __name__ == "__main__":
    # Runs the sample end to end and saves outputs (these double as the offline demo fallback).
    lang = sys.argv[1] if len(sys.argv) > 1 else "hi-IN"
    img = (SAMPLES / "loan.png").read_bytes()
    blocks, t1 = read_document(img, "loan.png", "en-IN")
    print(f"vision: {len(blocks)} blocks", t1)
    report, t2 = analyze(blocks, lang)
    print("analyze:", t2); print(json.dumps(report, ensure_ascii=False, indent=1))
    (SAMPLES / "loan_flagged.png").write_bytes(draw_flags(img, blocks, report["flags"]))
    wav, t3 = speak(report["summary"], lang)
    (SAMPLES / f"loan_summary_{lang}.wav").write_bytes(wav)
    print("speak:", t3, f"{len(wav)} bytes")
    json.dump({"lang": lang, "blocks": blocks, "report": report, "timings_ms": {**t1, **t2, **t3}},
              open(SAMPLES / f"loan_result_{lang}.json", "w"), ensure_ascii=False, indent=1)
    # Teach-back on a synthetic spoken answer (macOS `say`), only if a test clip exists
    clip = SAMPLES / "teachback_test.wav"
    if clip.exists():
        tr, v, t4 = teach_back(clip.read_bytes(), report, lang)
        print("teach-back:", t4, "|", tr); print(json.dumps(v, ensure_ascii=False, indent=1))
    print("saved to", SAMPLES)
