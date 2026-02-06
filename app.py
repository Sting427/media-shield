import streamlit as st
import nltk
import ssl
import plotly.graph_objects as go
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import time

# --- CLOUD FIX ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: General AI", page_icon="🛡️", layout="wide")

# ==========================================
# 🧠 THE "GENERAL AI" DATABASE
# ==========================================
# Combining Holiday (Emotion), Cialdini (Pressure), and Dobelli (Logic)

INTELLIGENCE = {
    # --- WING 1: EMOTION (Ryan Holiday) ---
    "ANGER": {
        "color": "#FF4B4B", # Red
        "category": "EMOTION",
        "patterns": [r"scandal", r"eviscerated", r"misogynist", r"racist", r"censored", r"banned", r"cover-up", r"outrage", r"shameful", r"hypocrisy", r"lies", r"attack", r"destroy", r"victim", r"furious"]
    },
    "FEAR": {
        "color": "#800080", # Purple
        "category": "EMOTION",
        "patterns": [r"toxic", r"lethal", r"crisis", r"collapse", r"warning", r"danger", r"risk", r"poison", r"meltdown", r"apocalypse", r"deadly", r"threat", r"emergency", r"fatal"]
    },
    
    # --- WING 2: PRESSURE (Robert Cialdini) ---
    "SCARCITY": {
        "color": "#0068C9", # Blue
        "category": "PRESSURE",
        "patterns": [
            r"(?i)\bact\s+now\b", r"(?i)\bonly\s+\d+\s+(left|remaining)\b", r"(?i)\bwhile\s+supplies\s+last\b", 
            r"(?i)\boffer\s+expires\b", r"(?i)\btime\s+is\s+running\s+out\b", r"(?i)\blast\s+chance\b", 
            r"(?i)\btoday\s+only\b", r"(?i)\bdeadline\s+approaching\b", r"(?i)\bhurry\b", r"(?i)\bflash\s+sale\b"
        ]
    },
    "AUTHORITY": {
        "color": "#00C9A7", # Teal
        "category": "PRESSURE",
        "patterns": [
            r"(?i)\b(doctors?|scientists?|experts?)\s+(recommend|say|agree|confirm)\b", r"(?i)\bstudies\s+(show|prove|indicate)\b", 
            r"(?i)\b(leading|top)\s+(authority|expert)\b", r"(?i)\bsecret\s+formula\b", r"(?i)\bscientifically\s+proven\b"
        ]
    },
    "SOCIAL_PROOF": {
        "color": "#29B5E8", # Light Blue
        "category": "PRESSURE",
        "patterns": [
            r"(?i)\bjoin\s+(over\s+)?[\d,.]+\s+(people|users)\b", r"(?i)\b(best|top)[- ]?selling\b", 
            r"(?i)\beveryone\s+is\s+(buying|using)\b", r"(?i)\b(thousands|millions)\s+of\s+satisfied\b", r"(?i)\b#1\s+rated\b"
        ]
    },

    # --- WING 3: LOGIC (Rolf Dobelli) ---
    "US_VS_THEM": {
        "color": "#FF8C00", # Dark Orange
        "category": "LOGIC",
        "patterns": [
            r"those people", r"the radical", r"unlike us", r"they want to", r"they hate", r"the enemy", 
            r"anti-American", r"foreigners", r"outsiders", r"destroy our values", r"threat to our way of life"
        ]
    },
    "SUNK_COST": {
        "color": "#8D6E63", # Brown
        "category": "LOGIC",
        "patterns": [
            r"we have already invested", r"too late to turn back", r"invested too much", r"can't stop now", 
            r"finish what we started", r"waste of time if we stop", r"already spent"
        ]
    }
}

class GeneralAI:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def scan(self, text):
        results = {
            "score": 0,
            "breakdown": {"EMOTION": 0, "PRESSURE": 0, "LOGIC": 0},
            "triggers_found": [],
            "highlighted_text": text
        }

        # 1. PREPARE PATTERNS
        # We process text to find matches for highlighting and counting
        matches = []
        for label, data in INTELLIGENCE.items():
            for pattern in data["patterns"]:
                # Find all matches for this pattern
                # We use regex to find the span (start, end) of the match
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matches.append({
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(),
                        "label": label,
                        "category": data["category"],
                        "color": data["color"]
                    })

        # 2. RESOLVE OVERLAPS (Longer matches take precedence)
        # e.g., "Act now" vs "Act" -> Keep "Act now"
        matches.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        final_matches = []
        last_end = 0
        
        for m in matches:
            if m["start"] >= last_end:
                final_matches.append(m)
                last_end = m["end"]
                
                # Add to Score & Breakdown
                results["breakdown"][m["category"]] += 1
                results["triggers_found"].append(m["label"])

        # 3. HIGHLIGHT TEXT (Rebuild string with HTML)
        # We work backwards so index positions don't shift
        final_matches.sort(key=lambda x: x["start"], reverse=True)
        for m in final_matches:
            badge = f'<span style="background-color: {m["color"]}33; border-bottom: 2px solid {m["color"]}; border-radius: 4px; padding: 0 2px; font-weight: bold;" title="{m["label"]} ({m["category"]})">{text[m["start"]:m["end"]]}</span>'
            results["highlighted_text"] = results["highlighted_text"][:m["start"]] + badge + results["highlighted_text"][m["end"]:]

        # 4. CALCULATE FINAL SCORE
        # Emotion = 10pts, Pressure = 15pts, Logic Fallacy = 20pts (Logic errors are heaviest)
        score = 0
        score += results["breakdown"]["EMOTION"] * 10
        score += results["breakdown"]["PRESSURE"] * 15
        score += results["breakdown"]["LOGIC"] * 20
        
        # Add VADER Intensity
        vader = self.vader.polarity_scores(text)
        intensity = abs(vader['compound']) * 100
        if intensity > 50: score += 15

        results["score"] = min(score, 100)
        return results

# ==========================================
# 🖥️ THE DASHBOARD
# ==========================================
st.title("🛡️ Media Shield: General AI Edition")
st.markdown("### The Unified Defense System (Emotion + Pressure + Logic)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Input Stream")
    text_input = st.text_area("Paste Article / Ad Copy / Manifesto:", height=350, placeholder="Paste text here...")
    btn = st.button("🧠 Run General AI Scan", type="primary")

if btn and text_input:
    ai = GeneralAI()
    data = ai.scan(text_input)
    
    with col2:
        st.subheader("2. Cognitive Attack Surface")
        
        # --- DETAILED LEGEND ---
    st.markdown("""
    <div style="margin-top: 20px; font-size: 0.9em; color: #ccc;">
        <strong>THE FORENSIC KEY:</strong> <br>
        <span style="color:#FF4B4B">■ Anger (Emotion)</span> &nbsp;&nbsp; 
        <span style="color:#800080">■ Fear (Emotion)</span> &nbsp;&nbsp;
        <span style="color:#0068C9">■ Urgency (Pressure)</span> &nbsp;&nbsp;
        <span style="color:#00C9A7">■ Authority (Pressure)</span> &nbsp;&nbsp;
        <span style="color:#29B5E8">■ Social Proof (Pressure)</span> &nbsp;&nbsp;
        <span style="color:#FF8C00">■ Tribalism (Logic)</span> &nbsp;&nbsp;
        <span style="color:#8D6E63">■ Sunk Cost (Logic)</span>
    </div>
    """, unsafe_allow_html=True)
    fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Attack Intensity',
            line_color='#FF4B4B'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(max(values)+1, 5)])
            ),
            showlegend=False,
            height=300,
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # METRICS
        c1, c2, c3 = st.columns(3)
        c1.metric("Emotion Hits", data["breakdown"]["EMOTION"])
        c2.metric("Pressure Hits", data["breakdown"]["PRESSURE"])
        c3.metric("Logic Fallacies", data["breakdown"]["LOGIC"])
        
        st.metric("TOTAL THREAT SCORE", f"{data['score']}/100")

    # --- FORENSIC VIEW ---
    st.divider()
    st.subheader("3. Forensic X-Ray (Visual Proof)")
    
    st.markdown(f"""
    <div style="padding: 20px; background-color: #0e1117; border: 1px solid #444; border-radius: 10px; font-family: sans-serif; line-height: 1.6;">
        {data['highlighted_text']}
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Legend: 🔴 Emotion (Anger/Fear) • 🔵 Pressure (Scarcity/Authority) • 🟠 Logic (Us vs Them/Fallacies)")


