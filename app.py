import json

import streamlit as st

import pipeline as p

st.set_page_config(page_title="Angootha", layout="centered")

# Big, simple, touch-friendly: many users read little, so lean on size, colour, numbers and sound.
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html, body, p, li, label, h1, h2, h3, .stMarkdown, .stButton button p, [data-testid="stWidgetLabel"] p,
[data-testid="stExpander"] summary p { font-family: "Noto Sans", "Noto Sans Devanagari", system-ui, sans-serif !important; }
[data-testid="stIconMaterial"], .material-symbols-rounded, span[class*="material"] {
    font-family: "Material Symbols Rounded" !important; }
html, body { font-size: 18px; }
.block-container { padding-top: 2rem; max-width: 760px; }
header[data-testid="stHeader"] { background: transparent; }
.hero { background: linear-gradient(135deg, #1E3A8A 0%, #0F172A 100%); color: #fff; border-radius: 20px;
        padding: 1.6rem 1.6rem 1.4rem; margin-bottom: .6rem; }
.hero h1 { color: #fff !important; font-size: 2.4rem !important; font-weight: 800; margin: 0 !important; padding: 0 !important; letter-spacing: -.02em; }
.hero .tag { font-size: 1.35rem; font-weight: 600; margin: .35rem 0 .5rem; color: #FDE68A; }
.hero p { color: #CBD5E1; margin: 0; font-size: 1rem; line-height: 1.55; }
.hero .by { margin-top: .9rem; font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; color: #94A3B8; }
.stButton > button { min-height: 3.6rem; font-size: 1.2rem !important; font-weight: 700; border-radius: 14px;
                     box-shadow: 0 4px 14px rgba(30,58,138,.25); }
.step { display: flex; align-items: center; gap: .85rem; margin: 2rem 0 .7rem; }
.step b { background: #1E3A8A; color: #fff; border-radius: 50%; min-width: 2.5rem; height: 2.5rem;
          display: inline-flex; align-items: center; justify-content: center; font-size: 1.25rem; }
.step span { font-size: 1.35rem; font-weight: 700; line-height: 1.25; color: #0F172A; }
.step small { display: block; font-size: .9rem; font-weight: 400; color: #64748B; }
.card { border-radius: 14px; padding: .95rem 1.15rem; margin: .5rem 0; font-size: 1.08rem; line-height: 1.55;
        background: #fff; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(15,23,42,.06); }
.red { border-left: 8px solid #DC2626; }
.amber { border-left: 8px solid #D97706; }
.ok { background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 8px solid #16A34A; color: #14532D; font-size: 1.3rem; font-weight: 700; }
.stop { background: #FEF2F2; border: 1px solid #FECACA; border-left: 8px solid #DC2626; color: #7F1D1D; font-size: 1.3rem; font-weight: 700; }
.ok small, .stop small { font-size: .95rem; font-weight: 500; }
.num { display: inline-flex; align-items: center; justify-content: center; background: #DC2626; color: #fff;
       border-radius: 50%; width: 1.8rem; height: 1.8rem; font-weight: 700; margin-right: .55rem; font-size: .95rem; }
.amber .num { background: #D97706; }
.say { font-size: 1.22rem; line-height: 1.7; font-weight: 600; color: #0F172A; background: #fff; border-radius: 14px;
       padding: 1rem 1.2rem; border: 1px solid #E2E8F0; }
@media (max-width: 640px) {
  .block-container { padding: 1rem .9rem 3rem; }
  .hero { padding: 1.2rem; border-radius: 16px; } .hero h1 { font-size: 2rem !important; }
  .step span { font-size: 1.15rem; }
}
</style>
""", unsafe_allow_html=True)

NATIVE = {"hi-IN": "हिन्दी", "mr-IN": "मराठी", "bn-IN": "বাংলা", "gu-IN": "ગુજરાતી", "kn-IN": "ಕನ್ನಡ",
          "ml-IN": "മലയാളം", "od-IN": "ଓଡ଼ିଆ", "pa-IN": "ਪੰਜਾਬੀ", "ta-IN": "தமிழ்", "te-IN": "తెలుగు",
          "en-IN": "English"}
S = st.session_state


def step(n, hi, en):
    st.markdown(f'<div class="step"><b>{n}</b><span>{hi}<small>{en}</small></span></div>', unsafe_allow_html=True)


st.markdown("""<div class="hero"><h1>Angootha</h1>
<div class="tag">अंगूठा लगाने से पहले, सुन लीजिए।</div>
<p>Before you put your thumbprint on any paper, we read it to you in your language, mark the dangerous lines,
and check that you really understood.</p>
<div class="by">Powered by Sarvam AI</div></div>""", unsafe_allow_html=True)

step("अ", "अपनी भाषा चुनिए", "Choose your language")
lang = st.pills("Language", list(NATIVE), format_func=NATIVE.get, default="hi-IN",
                label_visibility="collapsed") or "hi-IN"

step(1, "कागज़ की फ़ोटो", "Photo of the paper")
use_sample = st.toggle("नमूना कागज़ इस्तेमाल करें · Use sample loan paper", value=True)
img, name = None, None
if use_sample:
    img, name = (p.SAMPLES / "loan.png").read_bytes(), "loan.png"
    with st.expander("नमूना कागज़ देखें · See sample paper"):
        st.image(img)
else:
    src = st.file_uploader("फ़ोटो डालें · Upload a photo (PNG / JPG)", type=["png", "jpg", "jpeg"])
    if not src:
        src = st.camera_input("या कैमरे से फ़ोटो लें · Or take a photo")
    if src:
        img, name = src.getvalue(), getattr(src, "name", "photo.jpg")

if img and st.button("कागज़ पढ़कर सुनाइए · Read this paper to me", type="primary",
                     icon=":material/volume_up:", use_container_width=True):
    S.pop("verdict", None)
    cached = p.SAMPLES / f"loan_result_{lang}.json"
    try:
        if use_sample and cached.exists():  # saved run of the sample: instant demo, works offline
            d = json.loads(cached.read_text())
            S.result = {"blocks": d["blocks"], "report": d["report"],
                        "flagged": (p.SAMPLES / "loan_flagged.png").read_bytes(),
                        "wav": (p.SAMPLES / f"loan_summary_{lang}.wav").read_bytes(),
                        "timings": d["timings_ms"], "cached": True}
        else:
            with st.spinner("पढ़ रहे हैं… 1-2 मिनट लगेंगे · Reading the paper, about 1-2 minutes…"):
                blocks, t1 = p.read_document(img, name, "en-IN")
                report, t2 = p.analyze(blocks, lang)
                wav, t3 = p.speak(report["summary"], lang)
            S.result = {"blocks": blocks, "report": report, "flagged": p.draw_flags(img, blocks, report["flags"]),
                        "wav": wav, "timings": {**t1, **t2, **t3}}
        S.autoplay = True
    except p.AngoothaError as e:
        st.error(str(e))
    except Exception:
        st.error("Something went wrong. Please try again.")

R = S.get("result")
if R:
    rep = R["report"]
    step(2, "सुनिए: इस कागज़ में क्या लिखा है", "Listen: what this paper says")
    st.audio(R["wav"], format="audio/wav", autoplay=S.pop("autoplay", False))
    reds = sum(f["severity"] == "red" for f in rep["flags"])
    if reds:
        st.markdown(f'<div class="card stop">{reds} ख़तरनाक बातें मिलीं · {reds} dangerous lines found</div>',
                    unsafe_allow_html=True)
    st.markdown(f'<p class="say">{rep["summary"]}</p>', unsafe_allow_html=True)
    st.image(R["flagged"], caption="लाल = ज़मीन या बहुत पैसा जा सकता है · नारंगी = अनुचित या अस्पष्ट  |  "
                                   "Red = could cost land or a lot of money · Orange = unfair or unclear")
    for n, f in enumerate(rep["flags"], 1):
        cls = "red" if f["severity"] == "red" else "amber"
        st.markdown(f'<div class="card {cls}"><span class="num">{n}</span><b>{f["title"]}</b><br>{f["explain"]}</div>',
                    unsafe_allow_html=True)
    if rep.get("questions"):
        st.markdown("**अंगूठा लगाने से पहले ये पूछिए · Ask before signing:**")
        for q in rep["questions"]:
            st.markdown(f'<div class="card amber">{q}</div>', unsafe_allow_html=True)

    step(3, "अब आप बताइए: आप किस बात के लिए मान रहे हैं?", "Now you tell us: what are you agreeing to?")
    st.write("माइक दबाइए और 10-20 सेकंड बोलिए · Tap the mic and speak for 10-20 seconds.")
    audio = st.audio_input("अपनी बात रिकॉर्ड करें · Record your explanation")
    if audio and st.button("मेरी समझ जाँचिए · Check my understanding", type="primary",
                           icon=":material/fact_check:", use_container_width=True):
        try:
            with st.spinner("सुन रहे हैं… · Listening and checking…"):
                tr, v, tt = p.teach_back(audio.getvalue(), rep, lang)
                wav, ts = p.speak(v["feedback"], lang)
            S.verdict = {"transcript": tr, "v": v, "wav": wav, "t": {**tt, **ts}, "autoplay": True}
        except p.AngoothaError as e:
            st.error(str(e))
        except Exception:
            st.error("Something went wrong. Please try again.")
    V = S.get("verdict")
    if V:
        st.audio(V["wav"], format="audio/wav", autoplay=V.pop("autoplay", False))
        if V["v"]["understood"]:
            st.markdown('<div class="card ok">आपने समझ लिया। फ़ैसला आपका है।<br>'
                        '<small>You understood the risks. The decision is yours.</small></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card stop">अभी अंगूठा मत लगाइए।<br>'
                        '<small>Don\'t put your thumbprint yet.</small></div>', unsafe_allow_html=True)
            for m in V["v"]["missed"]:
                st.markdown(f'<div class="card red">{m}</div>', unsafe_allow_html=True)
        st.markdown(f'<p class="say">{V["v"]["feedback"]}</p>', unsafe_allow_html=True)
        st.caption(f"आपने कहा · You said: “{V['transcript']}”")

    with st.expander("Timings (Sarvam APIs)"):
        t = R["timings"]
        c = st.columns(4)
        c[0].metric("Vision", f"{t.get('vision', 0)/1000:.1f} s")
        c[1].metric("105B", f"{t.get('analyze', 0)/1000:.1f} s")
        c[2].metric("Bulbul", f"{t.get('speak', 0)/1000:.1f} s")
        c[3].metric("Total", f"{sum(t.values())/1000:.1f} s")
        if V:
            c = st.columns(3)
            c[0].metric("Saaras", f"{V['t']['listen']/1000:.1f} s")
            c[1].metric("105B check", f"{V['t']['check']/1000:.1f} s")
            c[2].metric("Bulbul reply", f"{V['t']['speak']/1000:.1f} s")

st.caption("Built on Sarvam AI: Sarvam Vision · Sarvam-105B · Saaras v4 · Mayura · Bulbul v4. "
           "Angootha explains papers; it does not give legal advice.")
