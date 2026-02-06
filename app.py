import streamlit as st
import nltk
import ssl
import plotly.graph_objects as go
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import time
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

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
st.set_page_config(page_title="Media Shield", page_icon="🛡️", layout="centered")

# ==========================================
# 🧠 INTELLIGENCE DATABASE
# ==========================================
INTELLIGENCE = {
    "ANGER": {"color": "#FF4B4B", "category": "EMOTION", "patterns": [r"scandal", r"eviscerated", r"misogynist", r"racist", r"censored", r"banned", r"cover-up", r"outrage", r"shameful", r"hypocrisy", r"lies", r"attack", r"destroy", r"victim", r"furious"]},
    "FEAR": {"color": "#800080", "category": "EMOTION", "patterns": [r"toxic", r"lethal", r"crisis", r"collapse", r"warning", r"danger", r"risk", r"poison", r"meltdown", r"apocalypse", r"deadly", r"threat", r"emergency", r"fatal"]},
    "SCARCITY": {"color": "#0068C9", "category": "PRESSURE", "patterns": [r"(?i)\bact\s+now\b", r"(?i)\bonly\s+\d+\s+(left|remaining)\b", r"(?i)\bwhile\s+supplies\s+last\b", r"(?i)\boffer\s+expires\b", r"(?i)\btime\s+is\s+running\s+out\b", r"(?i)\blast\s+chance\b", r"(?i)\btoday\s+only\b", r"(?i)\bdeadline\s+approaching\b", r"(?i)\bhurry\b"]},
    "AUTHORITY": {"color": "#00C9A7", "category": "PRESSURE", "patterns": [r"(?i)\b(doctors?|scientists?|experts?)\s+(recommend|say|agree|confirm)\b", r"(?i)\bstudies\s+(show|prove|indicate)\b", r"(?i)\b(leading|top)\s+(authority|expert)\b", r"(?i)\bsecret\s+formula\b", r"(?i)\bscientifically\s+proven\b"]},
    "SOCIAL_PROOF": {"color": "#29B5E8", "category": "PRESSURE", "patterns": [r"(?i)\bjoin\s+(over\s+)?[\d,.]+\s+(people|users)\b", r"(?i)\b(best|top)[- ]?selling\b", r"(?i)\beveryone\s+is\s+(buying|using)\b", r"(?i)\b(thousands|millions)\s+of\s+satisfied\b"]},
    "US_VS_THEM": {"color": "#FF8C00", "category": "LOGIC", "patterns": [r"those people", r"the radical", r"unlike us", r"they want to", r"they hate", r"the enemy", r"anti-American", r"foreigners", r"outsiders", r"destroy our values", r"threat to our way of life"]},
    "SUNK_COST": {"color": "#8D6E63", "category": "LOGIC", "patterns": [r"we have already invested", r"too late to turn back", r"invested too much", r"can't stop now", r"finish what we started", r"waste of time if we stop", r"already spent"]}
}

class GeneralAI:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def extract_from_pdf(self, uploaded_file):
        try:
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"Error reading PDF: {e}"

    def extract_from_url(self, url):
        try:
            # We pretend to be a real browser to avoid getting blocked
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return f"Error: Failed to retrieve website (Status Code: {response.status_code})"
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Kill javascript and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
                
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return clean_text
        except Exception as e:
            return f"Error scraping URL: {str(e)}"

    def scan(self, text):
        results = {"score": 0, "breakdown": {"EMOTION": 0, "PRESSURE": 0, "LOGIC": 0}, "triggers_found": [], "highlighted_text": text}
        matches = []
        
        # 1. FIND MATCHES
        for label, data in INTELLIGENCE.items():
            for pattern in data["patterns"]:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matches.append({"start": match.start(), "end": match.end(), "text": match.group(), "label": label, "category": data["category"], "color": data["color"]})

        # 2. RESOLVE OVERLAPS
        matches.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        final_matches = []
        last_end = 0
        for m in matches:
            if m["start"] >= last_end:
                final_matches.append(m)
                last_end = m["end"]
                results["breakdown"][m["category"]] += 1
                results["triggers_found"].append(m["label"])

        # 3. HIGHLIGHT TEXT
        final_matches.sort(key=lambda x: x["start"], reverse=True)
        for m in final_matches:
            badge = f'<span style="background-color: {m["color"]}33; border-bottom: 2px solid {m["color"]}; border-radius: 4px; padding: 0 2px; font-weight: bold;" title="{m["label"]}">{text[m["start"]:m["end"]]}</span>'
            results["highlighted_text"] = results["highlighted_text"][:m["start"]] + badge + results["highlighted_text"][m["end"]:]

        # 4. SCORE
        score = (results["breakdown"]["EMOTION"] * 10) + (results["breakdown"]["PRESSURE"] * 15) + (results["breakdown"]["LOGIC"] * 20)
        vader = self.vader.polarity_scores(text)
        if abs(vader['compound']) * 100 > 50: score += 15
        results["score"] = min(score, 100)
        return results

# ==========================================
# 📱 MOBILE-FIRST UI
# ==========================================
st.title("🛡️ Media Shield")
st.markdown("**Forensic Intelligence System**")

tab1, tab2, tab3 = st.tabs(["📂 Input", "📊 Analysis", "🚩 Evidence"])

with tab1:
    st.info("Upload PDF, Paste Text, or Enter URL.")
    
    input_method = st.radio("Source:", ["Paste Text / URL", "Upload PDF"], horizontal=True)
    
    final_text_to_scan = ""
    
    if input_method == "Paste Text / URL":
        user_input = st.text_area("Content:", height=200, placeholder="Paste text OR a website link (https://...)")
        
        if st.button("🚀 Process & Scan", type="primary", use_container_width=True):
            ai = GeneralAI()
            
            # URL DETECTION LOGIC
            if user_input.strip().startswith("http") or user_input.strip().startswith("www"):
                with st.spinner("🕷️ Crawling website content..."):
                    # Add https if missing
                    target_url = user_input.strip()
                    if target_url.startswith("www"): target_url = "https://" + target_url
                    
                    scraped_text = ai.extract_from_url(target_url)
                    
                    if "Error" in scraped_text:
                        st.error(scraped_text)
                    else:
                        final_text_to_scan = scraped_text
                        st.success(f"Webpage scraped! Analyzing {len(final_text_to_scan)} characters...")
            else:
                final_text_to_scan = user_input

    else:
        uploaded_file = st.file_uploader("Choose PDF", type="pdf")
        if uploaded_file is not None:
            if st.button("🚀 Process PDF", type="primary", use_container_width=True):
                ai = GeneralAI()
                with st.spinner("Extracting text from PDF..."):
                    final_text_to_scan = ai.extract_from_pdf(uploaded_file)
                    st.success(f"Extracted {len(final_text_to_scan)} characters.")

    # EXECUTE SCAN IF WE HAVE TEXT
    if final_text_to_scan and len(final_text_to_scan) > 10:
        st.session_state['scan_result'] = GeneralAI().scan(final_text_to_scan)
        st.session_state['has_run'] = True
        st.toast("Scan Complete! Check Analysis tab.", icon="✅")

with tab2:
    if st.session_state.get('has_run'):
        data = st.session_state['scan_result']
        
        # SCORE CARD
        score = data['score']
        color = "green"
        if score > 40: color = "orange"
        if score > 70: color = "red"
        
        st.markdown(f"""
            <div style="text-align: center; border: 2px solid {color}; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <h1 style="color:{color}; margin:0; font-size: 3em;">{score}</h1>
                <p style="margin:0; text-transform: uppercase; letter-spacing: 2px;">Threat Index</p>
            </div>
        """, unsafe_allow_html=True)

        # RADAR CHART
        categories = ["EMOTION", "PRESSURE", "LOGIC"]
        values = [data["breakdown"]["EMOTION"], data["breakdown"]["PRESSURE"], data["breakdown"]["LOGIC"]]
        values += [values[0]]
        categories += [categories[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#FF4B4B'))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(max(values)+1, 5)])),
            showlegend=False,
            height=250,
            margin=dict(l=30, r=30, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

        # BREAKDOWN
        c1, c2, c3 = st.columns(3)
        c1.metric("Emotion", data["breakdown"]["EMOTION"])
        c2.metric("Pressure", data["breakdown"]["PRESSURE"])
        c3.metric("Logic", data["breakdown"]["LOGIC"])
    else:
        st.caption("Waiting for data...")

with tab3:
    if st.session_state.get('has_run'):
        data = st.session_state['scan_result']
        
        st.markdown(f"""
        <div style="padding: 15px; background-color: #0e1117; border: 1px solid #444; border-radius: 5px; font-family: sans-serif; line-height: 1.6; font-size: 0.9em;">
            {data['highlighted_text']}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="margin-top: 20px; font-size: 0.8em; color: #888;">
            <span style="color:#FF4B4B">■ Anger</span> &nbsp; 
            <span style="color:#800080">■ Fear</span> &nbsp;
            <span style="color:#0068C9">■ Urgency</span> &nbsp;
            <span style="color:#00C9A7">■ Authority</span> &nbsp;
            <span style="color:#29B5E8">■ Social Proof</span> &nbsp;
            <span style="color:#FF8C00">■ Tribalism</span> &nbsp;
            <span style="color:#8D6E63">■ Sunk Cost</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Evidence will appear here.")
