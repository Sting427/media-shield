import streamlit as st
import trafilatura
from pypdf import PdfReader
import pandas as pd
import zipfile
import time
import plotly.graph_objects as go
from transformers import pipeline

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: Research Core", page_icon="🧪", layout="wide")

# ==========================================
# 🧠 THE NEURAL ENGINE (BERT)
# ==========================================
@st.cache_resource
def load_brain():
    classifier = pipeline("text-classification", model="unitary/toxic-bert", top_k=None)
    return classifier

class NeuralBrain:
    def __init__(self):
        self.classifier = load_brain()

    def analyze(self, text):
        try:
            results = self.classifier(text[:2000])
            if isinstance(results, list) and len(results) > 0:
                data = results[0] if isinstance(results[0], list) else results
            else:
                return None
            scores = {item['label']: item['score'] for item in data}
            return scores
        except Exception as e:
            st.error(f"Neural Engine Error: {str(e)}")
            return None

# ==========================================
# 🛠️ EXTRACTION ENGINES
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

def process_dataframe(df):
    """Helper to grab random samples from any dataframe"""
    try:
        # Smart Column Detection
        possible_cols = ['comment_text', 'text', 'content', 'tweet', 'message']
        text_col = next((col for col in possible_cols if col in df.columns), None)
        
        if not text_col:
            text_col = df.columns[0] # Fallback to first column
            
        # Grab 3 random samples
        sample_count = min(3, len(df))
        samples = df[text_col].sample(sample_count).tolist()
        
        st.toast(f"✅ Loaded {sample_count} samples from column: '{text_col}'")
        return "\n\n--- [NEXT SAMPLE] ---\n\n".join(str(s) for s in samples)
    except Exception as e:
        return f"Error processing data: {str(e)}"

def extract_from_csv(file):
    try:
        df = pd.read_csv(file)
        return process_dataframe(df)
    except Exception as e:
        return f"Error reading CSV: {str(e)}"

def extract_from_zip(file):
    try:
        with zipfile.ZipFile(file) as z:
            # Find the first CSV file inside the zip
            target_file = next((f for f in z.namelist() if f.endswith('.csv')), None)
            
            if not target_file:
                return "Error: No CSV file found inside this ZIP archive."
            
            # Read specific file from zip
            with z.open(target_file) as f:
                df = pd.read_csv(f)
                return process_dataframe(df)
    except Exception as e:
        return f"Error reading ZIP: {str(e)}"

# ==========================================
# 🖥️ UI LAYOUT
# ==========================================
st.title("🧪 Media Shield: Research Core")
st.caption("Neural Analysis for Web, PDF, Datasets (CSV), and Archives (ZIP)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Input Data")
    input_type = st.radio("Source:", ["Paste Text / URL", "Upload File"], horizontal=True)
    
    target_text = ""
    
    if input_type == "Paste Text / URL":
        user_input = st.text_area("Content:", height=300, placeholder="Paste text or URL here...")
        if user_input:
            if user_input.strip().startswith("http"):
                with st.spinner("🕷️ Deploying Scraper..."):
                    target_text = extract_from_url(user_input)
                    if target_text: st.success("Extracted content successfully.")
                    else: st.error("Could not scrape URL.")
            else:
                target_text = user_input
    else:
        # UPDATED: Added "zip" to type list
        uploaded = st.file_uploader("Upload Document", type=["pdf", "csv", "txt", "zip"])
        if uploaded:
            with st.spinner("📂 Processing File..."):
                if uploaded.name.endswith(".csv"):
                    target_text = extract_from_csv(uploaded)
                elif uploaded.name.endswith(".zip"):
                    target_text = extract_from_zip(uploaded)
                elif uploaded.name.endswith(".pdf"):
                    target_text = extract_from_pdf(uploaded)
                elif uploaded.name.endswith(".txt"):
                    target_text = uploaded.read().decode("utf-8")
                
                if target_text and not target_text.startswith("Error"):
                    st.success(f"File loaded: {uploaded.name}")
                elif target_text:
                    st.error(target_text)

    analyze_btn = st.button("🚀 Run Neural Scan", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Forensic Analysis")
    
    if analyze_btn and target_text:
        with st.spinner("🧠 Neural Network is analyzing vectors..."):
            brain = NeuralBrain()
            scores = brain.analyze(target_text)
            
        if scores:
            danger_score = (
                scores.get('identity_hate', 0) * 100 + 
                scores.get('threat', 0) * 80 + 
                scores.get('severe_toxic', 0) * 60 +
                scores.get('toxic', 0) * 30
            )
            final_score = min(int(danger_score), 100)
            
            color = "#4CAF50" 
            if final_score > 40: color = "#FFA500"
            if final_score > 80: color = "#FF0000"

            st.markdown(f"""
            <div style="background-color: #0e1117; border-left: 10px solid {color}; border-radius: 5px; padding: 20px; margin-bottom: 20px;">
                <h1 style="font-size: 3em; margin: 0; color: {color};">{final_score}/100</h1>
                <p style="color: #aaa; text-transform: uppercase; letter-spacing: 1px;">Toxicity Index</p>
            </div>
            """, unsafe_allow_html=True)
            
            labels = list(scores.keys())
            values = [scores[k] * 100 for k in labels]
            colors = ['#ff4b4b' if v > 50 else '#333' for v in values]
            
            fig = go.Figure(go.Bar(
                x=values, y=labels, orientation='h', marker_color=colors,
                text=[f"{v:.1f}%" for v in values], textposition='auto'
            ))
            fig.update_layout(title="Detailed Vector Analysis", xaxis_title="Confidence (%)", yaxis_autorange="reversed", height=400, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📝 AI Verdict")
            if final_score < 20: st.success("✅ **Clean Content**")
            elif scores.get('identity_hate', 0) > 0.5: st.error(f"🚨 **HATE SPEECH:** Attack on identity detected ({int(scores['identity_hate']*100)}%).")
            elif scores.get('threat', 0) > 0.5: st.error(f"🛑 **THREAT DETECTED:** Credible physical threat detected.")
            elif scores.get('toxic', 0) > 0.8: st.warning("⚠️ **Highly Toxic:** Inflammatory language.")
            else: st.info("⚠️ **Suspicious:** Potential negativity detected.")
        
        with st.expander("Show Analyzed Text Sample"):
            st.text(target_text[:1000] + "...")
