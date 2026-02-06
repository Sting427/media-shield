import streamlit as st
import trafilatura
from pypdf import PdfReader
import re
import time
import plotly.graph_objects as go
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: Universal Core", page_icon="🛡️", layout="wide")

# ==========================================
# 🧠 UNIVERSAL INTELLIGENCE DATABASE
# ==========================================
# This dictionary detects PATTERNS, not just specific sentences.
INTELLIGENCE = {
    "DEHUMANIZATION": {
        "score": 30, # High Threat
        "color": "#000000",
        "patterns": [
            r"cancer", r"vermin", r"cockroach", r"insect", r"infest", r"plague", 
            r"filth", r"garbage", r"trash", r"animals?", r"beasts?", r"savages?", 
            r"subhuman", r"parasite", r"disease", r"virus", r"bacteria"
        ]
    },
    "VIOLENCE_INCITEMENT": {
        "score": 25,
        "color": "#FF0000",
        "patterns": [
            r"eliminate", r"eradicate", r"wipe out", r"cleansing", r"crush", 
            r"destroy them", r"kill", r"slaughter", r"burn", r"hang", r"shoot",
            r"no mercy", r"hunting"
        ]
    },
    "GROUP_ATTACK": {
        "score": 15,
        "color": "#FF4500",
        "patterns": [
            r"cult", r"invaders?", r"illegals?", r"aliens?", r"thugs", 
            r"criminals", r"terrorists?", r"rapists?", r"groomers?",
            r"loot", r"steal", r"rob", r"jihadis?"
        ]
    },
    "MANIPULATION_TACTICS": {
        "score": 10,
        "color": "#800080",
        "patterns": [
            r"barbaric", r"backward", r"primitive", r"uncivilized", 
            r"brainwashed", r"indoctrinated", r"radical", r"extremist",
            r"fundamentalist", r"threat to", r"danger to"
        ]
    }
}

class UniversalBrain:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def analyze(self, text):
        results = {
            "score": 0,
            "hits": {}, # Stores hits by category
            "verdict": "",
            "explanation": []
        }
        
        # 1. SCAN FOR PATTERNS
        total_hits = 0
        
        for category, data in INTELLIGENCE.items():
            results["hits"][category] = []
            for pattern in data["patterns"]:
                # Find all matches (case insensitive)
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Add unique hits to list
                    unique_matches = list(set(matches))
                    results["hits"][category].extend(unique_matches)
                    
                    # Calculate Score
                    results["score"] += len(matches) * data["score"]
                    total_hits += len(matches)

        # Cap score at 100
        results["score"] = min(results["score"], 100)
        
        # 2. GENERATE DYNAMIC REPORT
        # This part is now SMART. It reads what it found and writes a sentence about it.
        
        if results["hits"]["DEHUMANIZATION"]:
            words_found = ", ".join([f"'{w}'" for w in results["hits"]["DEHUMANIZATION"][:3]])
            results["explanation"].append(f"⚠️ **Dehumanization Detected:** The text refers to people as {words_found}. This is a dangerous tactic used to strip targets of human rights.")
            
        if results["hits"]["VIOLENCE_INCITEMENT"]:
            words_found = ", ".join([f"'{w}'" for w in results["hits"]["VIOLENCE_INCITEMENT"][:3]])
            results["explanation"].append(f"🚨 **Incitement to Violence:** Usage of terms like {words_found} implies a call for physical harm or elimination.")

        if results["hits"]["GROUP_ATTACK"]:
            words_found = ", ".join([f"'{w}'" for w in results["hits"]["GROUP_ATTACK"][:3]])
            results["explanation"].append(f"🛑 **Group Hostility:** The text generalizes a group as {words_found}, promoting collective guilt.")

        if results["score"] == 0:
            results["verdict"] = "✅ SAFE CONTENT"
            results["explanation"].append("No common hate speech patterns or manipulation triggers were detected.")
        elif results["score"] > 75:
            results["verdict"] = "🚨 EXTREME THREAT"
        elif results["score"] > 40:
            results["verdict"] = "⚠️ TOXIC CONTENT"
        else:
            results["verdict"] = "⚠️ SUSPICIOUS"

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
st.title("🛡️ Media Shield: Universal Core")
st.caption("Running in Offline Mode • Universal Pattern Matching")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Intercept Signal")
    input_type = st.radio("Source:", ["Paste Text / URL", "Upload PDF"], horizontal=True)
    
    target_text = ""
    
    if input_type == "Paste Text / URL":
        user_input = st.text_area("Content:", height=300, placeholder="Paste ANY controversial text here...")
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
        brain = UniversalBrain()
        
        with st.spinner("🔍 Scanning for universal hate patterns..."):
            time.sleep(0.5) 
            data = brain.analyze(target_text)
            
        # DYNAMIC COLOR
        color = "#4CAF50" # Green
        if data["score"] > 40: color = "#FFA500" # Orange
        if data["score"] > 75: color = "#FF0000" # Red
        
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
        if not data["explanation"]:
             st.markdown("- No threats detected.")
        for line in data["explanation"]:
            st.markdown(f"- {line}")
            
        # EVIDENCE GRID
        st.markdown("---")
        st.caption("EVIDENCE LOCKER")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Dehumanization", len(data["hits"]["DEHUMANIZATION"]))
        with c2:
            st.metric("Violence Calls", len(data["hits"]["VIOLENCE_INCITEMENT"]))
        with c3:
            st.metric("Group Attacks", len(data["hits"]["GROUP_ATTACK"]))
