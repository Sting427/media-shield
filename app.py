import streamlit as st
import google.generativeai as genai
import trafilatura
from pypdf import PdfReader
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: AI Core", page_icon="🧠", layout="wide")

# ==========================================
# 🧠 THE GEMINI FORENSIC ENGINE
# ==========================================
class GeminiBrain:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def analyze(self, text):
        prompt = f"""
        Act as a Forensic Linguist and Counter-Disinformation Analyst. 
        Analyze the following text for:
        1. Emotional Manipulation (Fear, Anger, Pity)
        2. Logical Fallacies (Strawman, Ad Hominem, False Equivalence)
        3. Hate Speech & Dehumanization (Targeting identity, biological metaphors)
        4. Propaganda Tactics (Bandwagon, False Authority)

        TEXT TO ANALYZE:
        "{text[:3000]}"

        OUTPUT FORMAT:
        Return a clear, human-readable report. 
        - First, give a "Threat Score" from 0-100.
        - Second, provide a "Verdict" (Safe, Suspicious, or Dangerous).
        - Third, create a bulleted list called "The Smoking Gun". For each point, quote the specific sentence from the text and explain EXACTLY why it is manipulative.
        - Fourth, give a "Cognitive Defense" tip on how to mentally resist this specific message.
        
        Do not use Markdown for the whole thing, just use bolding for headers. Keep it punchy and professional.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error connecting to AI Core: {str(e)}"

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
st.title("🧠 Media Shield: Cognitive Defense")
st.caption("Powered by Gemini 1.5 Flash • Context-Aware Analysis")

# --- SECRETS MANAGEMENT (The Auto-Login) ---
# Try to get key from Cloud Secrets first
api_key = st.secrets.get("GEMINI_API_KEY")

# If no secret is found, fallback to manual entry
with st.sidebar:
    if not api_key:
        st.header("🔑 Activation")
        api_key = st.text_input("Enter Google Gemini API Key:", type="password", help="Get one for free at aistudio.google.com")
    else:
        st.success("🔐 Secure Link Active")
        st.caption("Key loaded from Cloud Secrets")

# MAIN INPUT
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Intercept Signal")
    input_type = st.radio("Source:", ["Paste Text / URL", "Upload PDF"], horizontal=True)
    
    target_text = ""
    
    if input_type == "Paste Text / URL":
        user_input = st.text_area("Content:", height=300, placeholder="Paste a link or text...")
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

# ANALYSIS OUTPUT
with col2:
    st.subheader("2. Forensic Report")
    
    if analyze_btn:
        if not api_key:
            st.error("⚠️ API Key Missing. Please check Settings > Secrets.")
        elif not target_text:
            st.warning("Please provide text to analyze.")
        else:
            brain = GeminiBrain(api_key)
            
            with st.spinner("🧠 Neural Network is analyzing meaning, context, and intent..."):
                start_time = time.time()
                report = brain.analyze(target_text)
                end_time = time.time()
                
            # DISPLAY REPORT
            st.markdown(f"""
            <div style="background-color: #0e1117; border: 1px solid #444; border-radius: 10px; padding: 20px; font-family: sans-serif; line-height: 1.6;">
                {report}
            </div>
            """, unsafe_allow_html=True)
            
            st.caption(f"Analysis completed in {round(end_time - start_time, 2)} seconds.")
