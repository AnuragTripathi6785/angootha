import json
from pathlib import Path

import streamlit as st

import pipeline as p

st.set_page_config(page_title="Angootha", page_icon="🖐️", layout="wide")
st.title("🖐️ Angootha")
st.markdown("**अंगूठा लगाने से पहले, सुन लीजिए।** Photograph any paper before you put your thumbprint on it. "
            "Angootha reads it, marks the dangerous lines, explains them aloud in your language, "
            "and checks that you really understood before you sign.")

S = st.session_state
lang = st.selectbox("Your language", list(p.LANGS), format_func=lambda c: p.LANGS[c])
use_sample = st.checkbox("Use sample loan paper instead", value=True)


def run_live(img, name):
    blocks, t1 = p.read_document(img, name, "en-IN")
    report, t2 = p.analyze(blocks, lang)
    wav, t3 = p.speak(report["summary"], lang)
    return {"blocks": blocks, "report": report, "img": img, "flagged": p.draw_flags(img, blocks, report["flags"]),
            "wav": wav, "timings": {**t1, **t2, **t3}}


img, name = None, None
if use_sample:
    img, name = (p.SAMPLES / "loan.png").read_bytes(), "loan.png"
else:
    up = st.file_uploader("Photo or PDF of the paper", type=["png", "jpg", "jpeg"])
    cam = None if up else st.camera_input("…or take a photo")
    src = up or cam
    if src:
        img, name = src.getvalue(), getattr(src, "name", "photo.jpg")

if img and st.button("📖 Read this paper to me", type="primary"):
    S.pop("verdict", None)
    cached = p.SAMPLES / f"loan_result_{lang}.json"
    try:
        if use_sample and cached.exists():  # saved run of the sample: instant demo, works offline
            d = json.loads(cached.read_text())
            S.result = {"blocks": d["blocks"], "report": d["report"], "img": img,
                        "flagged": (p.SAMPLES / "loan_flagged.png").read_bytes(),
                        "wav": (p.SAMPLES / f"loan_summary_{lang}.wav").read_bytes(),
                        "timings": d["timings_ms"], "cached": True}
        else:
            with st.spinner("Sarvam Vision is reading the paper, then Sarvam-105B checks every line (about 1–2 min)…"):
                S.result = run_live(img, name)
    except p.AngoothaError as e:
        st.error(str(e))
    except Exception:
        st.error("Something went wrong. Please try again.")

R = S.get("result")
if R:
    rep = R["report"]
    left, right = st.columns([1, 1])
    with left:
        st.image(R["flagged"], caption="Red = could cost you land or a lot of money · Amber = unfair or unclear")
    with right:
        reds = sum(f["severity"] == "red" for f in rep["flags"])
        if reds:
            st.error(f"⚠️ {reds} dangerous line(s) found")
        st.subheader("🔊 What this paper says")
        st.audio(R["wav"], format="audio/wav")
        st.markdown(f"#### {rep['summary']}")
        for n, f in enumerate(rep["flags"], 1):
            icon = "🔴" if f["severity"] == "red" else "🟠"
            st.markdown(f"{icon} **{n}. {f['title']}** — {f['explain']}")
        if rep.get("questions"):
            st.markdown("**Ask before signing:**")
            for q in rep["questions"]:
                st.markdown(f"- {q}")
    t = R["timings"]
    cols = st.columns(4)
    cols[0].metric("Vision (OCR)", f"{t.get('vision', 0)/1000:.1f} s")
    cols[1].metric("105B analysis", f"{t.get('analyze', 0)/1000:.1f} s")
    cols[2].metric("Bulbul voice", f"{t.get('speak', 0)/1000:.1f} s")
    cols[3].metric("Total", f"{sum(t.values())/1000:.1f} s")
    if R.get("cached"):
        st.caption("Showing a saved run of the sample (live times shown). Untick the sample to try your own paper.")

    st.divider()
    st.subheader("🖐️ Before your thumbprint: tell us in your own words")
    st.write("What are you agreeing to? Speak for 10–20 seconds. We'll check you understood the dangers.")
    audio = st.audio_input("Record your explanation")
    if audio and st.button("✅ Check my understanding"):
        try:
            with st.spinner("Listening (Saaras) and checking (Sarvam-105B)…"):
                tr, v, tt = p.teach_back(audio.getvalue(), rep, lang)
                wav, ts = p.speak(v["feedback"], lang)
            S.verdict = {"transcript": tr, "v": v, "wav": wav, "t": {**tt, **ts}}
        except p.AngoothaError as e:
            st.error(str(e))
        except Exception:
            st.error("Something went wrong. Please try again.")
    V = S.get("verdict")
    if V:
        st.caption(f"You said: “{V['transcript']}”")
        if V["v"]["understood"]:
            st.success("✅ You understood the risks. The decision is yours.")
        else:
            st.warning("⚠️ Don't put your thumbprint yet. Listen again to what you missed.")
            for m in V["v"]["missed"]:
                st.markdown(f"- {m}")
        st.markdown(f"#### {V['v']['feedback']}")
        st.audio(V["wav"], format="audio/wav")
        c = st.columns(3)
        c[0].metric("Saaras (listen)", f"{V['t']['listen']/1000:.1f} s")
        c[1].metric("105B (check)", f"{V['t']['check']/1000:.1f} s")
        c[2].metric("Bulbul (reply)", f"{V['t']['speak']/1000:.1f} s")

st.caption("Built on Sarvam AI: Sarvam Vision · Sarvam-105B · Saaras v4 · Bulbul v4. Angootha explains; it does not give legal advice.")
