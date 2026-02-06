import streamlit as st
import trafilatura
from pypdf import PdfReader
import re
import time
import plotly.graph_objects as go
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: Forensic Core", page_icon="🛡️", layout="wide")

# ==========================================
# 🧠 THE "OFFLINE" INTELLIGENCE DATABASE
# ==========================================
# This engine runs LOCALLY. No API Key required. No 404 errors.
INTELLIGENCE = {
    "HATE_SPEECH": {
        "color": "#000000", # Black
        "label": "DEHUMANIZATION",
        "patterns": [
            r"cancer for humanity", r"barbaric cult", r"given nothing to humanity", 
            r"elimination", r"conversion", r"enslaving", r"loot maal", r"laundia", 
            r"vermin", r"infest", r"plague", r"animals?", r"savages?", r"wipe out", 
            r"eradicate", r"cleansing", r"subhuman", r"invaders"
        ]
    },
    "RELIGIOUS_ATTACK": {
        "color": "#FF0000", # Red
        "label": "RELIGIOUS HOSTILITY",
        "patterns": [
            r"jihadis?", r"arab cult", r"7th century", r"ma?al e ganimat", 
            r"malkal zamin", r"radical", r"extremist", r"terrorist"
        ]
    },
    "EMOTIONAL_MANIPULATION": {
        "color": "#800080", # Purple
        "label": "FEAR & ANGER",
        "patterns": [
            r"violence", r"lawlessness", r"destruction", r"no peace", r"no progress",
            r"crisis", r"collapse", r"danger", r"threat", r"deadly", r"fatal",
            r"scandal", r"outrage", r"shameful", r"betrayal", r"cover-up"
        ]
    }
}

class LocalBrain:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def analyze(self, text):
        results = {
            "score": 0,
            "hits": [],
            "verdict": "",
            "explanation": []
        }
        
        # 1. SCAN FOR PATTERNS
        detected_categories = {}
        
        for category, data in INTELLIGENCE.items():
            count = 0
            for pattern in data["patterns"]:
                # Find all matches (case insensitive)
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    count += len(matches)
                    for m in matches:
                        results["hits"].append(f"**'{m}'** ({data['label']})")
            
            if count > 0:
                detected_categories[data['label']] = count

        # 2. CALCULATE THREAT SCORE
        # Hate speech is weighted heavily (30 points per hit)
        score = 0
        score += detected_categories.get("DEHUMANIZATION", 0) * 30
        score += detected_categories.get("RELIGIOUS HOSTILITY", 0) * 20
        score += detected_categories.get("FEAR & ANGER", 0) * 10
        
        # VADER Sentiment Check (Negative sentiment adds points)
        vs = self.vader.polarity_scores(text)
        if vs['compound'] < -0.5:
            score += 20
            
        results["score"] = min(score, 100)

        # 3. GENERATE HUMAN-READABLE REPORT
        if results["score"] > 80:
            results["verdict"] = "🚨 DANGEROUS HATE SPEECH"
            results["explanation"].append("This text uses **dehumanizing language** ('cancer', 'vermin') to strip a group of their human status.")
            results["explanation"].append("It promotes **hostility** by generalizing an entire community as 'barbaric' or a 'cult'.")
            results["explanation"].append("This is not a political critique; it is an **attack on identity** meant to justify harm.")
        elif results["score"] > 40:
            results["verdict"] = "⚠️ HIGHLY TOXIC CONTENT"
            results["explanation"].append("This text relies on **extreme emotional triggers** (Fear/Anger) to bypass logic.")
            results["explanation"].append("It uses **us-vs-them** rhetoric to paint a specific group as an enemy.")
        else:
            results["verdict"] = "✅ SAFE / NEUTRAL"
            results["explanation"].append("No significant manipulation patterns detected.")

        return results

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def extract_from_url(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded: return None
        return trafilatura.extract(downloaded)
    except: return None

def extract_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])
    except: return None

# ==========================================
# 🖥️ UI LAYOUT
# ==========================================
st.title("🛡️ Media Shield: Forensic Core")
st.caption("Running in Offline Mode • No API Limits • Privacy Focused")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Intercept Signal")
    input_type = st.radio("Source:", ["Paste Text / URL", "Upload PDF"], horizontal=True)
    
    target_text = ""
    
    if input_type == "Paste Text / URL":
        user_input = st.text_area("Content:", height=300, placeholder="Paste that hateful comment here...")
        if user_input:
            if user_input.startswith("http"):
                with st.spinner("🕷️ Deploying Scraper..."):
                    target_text = extract_from_url(user_input)
                    if target_text: st.success("Extracted Article Content.")
                    else: st.error("Could not scrape URL.")
            else:
                target_text = user_input
    else:
        uploaded = st.file_uploader("PDF Document", type="pdf")
        if uploaded:
            with st.spinner("📄 Reading Document..."):
                target_text = extract_from_pdf(uploaded)
                st.success("PDF Loaded.")

    analyze_btn = st.button("🚀 Run Forensic Scan", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Forensic Report")
    
    if analyze_btn and target_text:
        brain = LocalBrain()
        
        with st.spinner("🔍 Scanning for Hate Speech patterns..."):
            time.sleep(0.5) # Simulate processing for UX
            data = brain.analyze(target_text)
            
        # DYNAMIC COLOR
        color = "#4CAF50" # Green
        if data["score"] > 40: color = "#FFA500" # Orange
        if data["score"] > 80: color = "#FF0000" # Red
        
        # VERDICT BOX
        st.markdown(f"""
        <div style="background-color: #0e1117; border-left: 10px solid {color}; border-radius: 5px; padding: 20px; margin-bottom: 20px;">
            <h2 style="color: {color}; margin:0;">{data['verdict']}</h2>
            <h1 style="font-size: 3em; margin: 10px 0;">{data['score']}/100</h1>
            <p style="color: #aaa; text-transform: uppercase; letter-spacing: 1px;">Threat Intensity</p>
        </div>
        """, unsafe_allow_html=True)
        
        # EXPLANATION
        st.markdown("### 📝 Analysis")
        for line in data["explanation"]:
            st.markdown(f"- {line}")
            
        # SMOKING GUN (EVIDENCE)
        if data["hits"]:
            st.markdown("### 🔫 The Smoking Gun (Triggers Found)")
            st.warning(", ".join(data["hits"]))
            
        # RADAR CHART REPLACEMENT (BAR CHART)
        # Using a simple progress bar visual for simplicity and robustness
        st.markdown("---")
        st.caption("FORENSIC BREAKDOWN")
        st.progress(data["score"] / 100)
