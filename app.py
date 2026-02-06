import streamlit as st
import trafilatura
from pypdf import PdfReader
import time
import plotly.graph_objects as go
from transformers import pipeline

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: Neural Core", page_icon="🧠", layout="wide")

# ==========================================
# 🧠 THE NEURAL ENGINE (BERT)
# ==========================================
# This downloads a real AI model trained on Wikipedia comments.
# It understands CONTEXT, not just keywords.
@st.cache_resource
def load_brain():
    # We use 'unitary/toxic-bert' - the Gold Standard for hate speech detection
    classifier = pipeline("text-classification", model="unitary/toxic-bert", return_all_scores=True)
    return classifier

class NeuralBrain:
    def __init__(self):
        self.classifier = load_brain()

    def analyze(self, text):
        # Truncate to 512 tokens (BERT limit) for speed
        results = self.classifier(text[:2000]) 
        
        # The model returns a list of dictionaries: [{'label': 'toxic', 'score': 0.9}, ...]
        scores = {item['label']: item['score'] for item in results[0]}
        
        return scores

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
st.title("🧠 Media Shield: Neural Core")
st.caption("Running 'toxic-bert' Transformer Model • Context-Aware Analysis")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Intercept Signal")
    input_type = st.radio("Source:", ["Paste Text / URL", "Upload PDF"], horizontal=True)
    
    target_text = ""
    
    if input_type == "Paste Text / URL":
        user_input = st.text_area("Content:", height=300, placeholder="Paste text to test the Neural Network...")
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

    analyze_btn = st.button("🚀 Run Neural Scan", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Forensic Report")
    
    if analyze_btn and target_text:
        # Load the brain (First time takes 10-20 seconds to download model)
        with st.spinner("🧠 Neural Network is processing vectors... (First run may be slow)"):
            brain = NeuralBrain()
            scores = brain.analyze(target_text)
            
        # --- VISUALIZING THE BRAIN'S OUTPUT ---
        
        # 1. THE BIG SCORE (Weighted Average)
        # We calculate a "Danger Score" based on the worst categories
        danger_score = (
            scores['identity_hate'] * 100 + 
            scores['threat'] * 80 + 
            scores['severe_toxic'] * 60 +
            scores['toxic'] * 40
        )
        final_score = min(int(danger_score), 100)
        
        # Color Logic
        color = "#4CAF50" # Green
        if final_score > 40: color = "#FFA500" # Orange
        if final_score > 80: color = "#FF0000" # Red

        # SCORE CARD
        st.markdown(f"""
        <div style="background-color: #0e1117; border-left: 10px solid {color}; border-radius: 5px; padding: 20px; margin-bottom: 20px;">
            <h1 style="font-size: 3em; margin: 0; color: {color};">{final_score}/100</h1>
            <p style="color: #aaa; text-transform: uppercase; letter-spacing: 1px;">Neural Threat Index</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. DETAILED BREAKDOWN (Bar Chart)
        # Formatting keys for display
        labels = list(scores.keys())
        values = [scores[k] * 100 for k in labels] # Convert 0.9 to 90%
        colors = ['#ff4b4b' if v > 50 else '#444' for v in values] # Red if high
        
        fig = go.Figure(go.Bar(
            x=values,
            y=labels,
            orientation='h',
            marker_color=colors,
            text=[f"{v:.1f}%" for v in values],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Toxicity Vector Analysis",
            xaxis_title="Confidence Level (%)",
            yaxis_autorange="reversed", # Top to bottom
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 3. THE VERDICT (Written by Logic)
        st.subheader("📝 Neural Verdict")
        
        top_trigger = max(scores, key=scores.get)
        
        if final_score < 20:
             st.success("✅ **Safe Content:** The model detects no hostile intent or toxicity.")
        elif scores['identity_hate'] > 0.5:
            st.error(f"🚨 **HATE SPEECH DETECTED:** The model is {int(scores['identity_hate']*100)}% confident this text attacks a specific group based on religion, race, or identity.")
        elif scores['threat'] > 0.5:
             st.error(f"🛑 **VIOLENCE DETECTED:** The model detected a physical threat with {int(scores['threat']*100)}% confidence.")
        elif scores['toxic'] > 0.8:
             st.warning("⚠️ **Toxic Behavior:** This text is highly rude, disrespectful, or inflammatory, but may not be hate speech.")
        else:
             st.info("⚠️ **Suspicious:** The text has negative undertones but does not cross the line into actionable threats.")
