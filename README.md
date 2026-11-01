# Angootha — read it to me before I sign

**Live demo (hackathon venue Wi-Fi):** http://10.51.13.82:8501 — open it on any phone or laptop connected to the same Wi-Fi.

Millions of Indians sign with a thumbprint (*angootha*) on papers they cannot read: moneylender loans, land and lease papers, job contracts, consent forms. Angootha reads the paper aloud in their language, marks the dangerous lines **on the photo itself**, and runs a **teach-back check** to confirm they understood before they sign.

## Pipeline (all Sarvam AI)
1. **Sarvam Vision** (`doc_ai.parse`) reads the photo → text blocks with bounding boxes
2. **Sarvam-105B** finds harmful clauses (interest, penalties, land loss, waived rights) → red/amber boxes drawn on the photo
3. **Bulbul v4** speaks the explanation in the user's language
4. **Teach-back:** the user explains the paper by voice → **Saaras v4** transcribes → **Sarvam-105B** checks understanding → Bulbul speaks feedback

## Run
```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo "SARVAM_API_KEY=your_key" > .env
.venv/bin/streamlit run app.py
```
`python pipeline.py hi-IN` runs the sample end to end and saves outputs to `samples/` (used as the instant/offline demo).

Angootha explains documents; it does not give legal advice.
