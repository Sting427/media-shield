import streamlit as st
import nltk
import ssl
import plotly.graph_objects as go
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import time
import trafilatura # The New "Specialist" Scraper
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
        # --- THE TRAFILATURA UPGRADE ---
        # This replaces the messy BeautifulSoup logic with a specialized extractor
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                return "Error: Could not reach the website. It might be blocking bots."
            
            # This is the magic line that strips ads, menus, and noise
            text = trafilatura.extract(downloaded)
            
            if text is None:
                return "Error: Could not find the main article text."
            
            return text
        except Exception as e:
            return f"Error scraping URL: {str(e)}"

    def generate_verdict(self, breakdown, score):
        if score < 20:
            return "✅ **Safe to Read:** This text appears balanced, neutral, and objective. It relies on facts rather than emotional manipulation."
        
        highest_cat = max(breakdown, key=breakdown.get)
        verdict = ""
        
        if highest_cat == "EMOTION":
            verdict = "⚠️ **Emotional Manipulation Detected:** This text is trying to bypass your logic by triggering intense feelings like Anger or Fear. "
        elif highest_cat == "PRESSURE":
            verdict = "⚠️ **High Pressure Tactics:** The author is creating artificial urgency or relying on vague 'experts' to force you into a quick decision. "
        elif highest_cat == "LOGIC":
            verdict = "⚠️ **Logical Fallacies:** This argument is structurally flawed. It uses 'Us vs. Them' tribalism or 'Sunk Cost' traps instead of valid reasoning. "
            
        if score > 70:
            verdict += "**Proceed with extreme caution.** The manipulation density is critical."
        elif score > 40:
            verdict += "Be skeptical of the framing used here."
            
        return verdict

    def scan(self, text):
        results = {"score": 0, "breakdown": {"EMOTION": 0, "PRESSURE": 0, "LOGIC": 0}, "triggers_found": [], "highlighted_text": text}
        matches = []
        
        for label, data in INTELLIGENCE.items():
            for pattern in data["patterns"]:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matches.append({"start": match.start(), "end": match.end(), "text": match.group(), "label": label, "category": data["category"], "color": data["color"]})

        matches.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        final_matches = []
        last_end = 0
        for m in matches:
            if m["start"] >= last_end:
                final_matches.append(m)
                last_end = m["end"]
                results["breakdown"][m["category"]] += 1
                results["triggers_found"].append(m["label"])

        final_matches.sort(key=lambda x: x["start"], reverse=True)
        for m in final_matches:
            badge = f'<span style="background-color: {m["color"]}33; border-bottom: 2px solid {m["color"]}; border-radius: 4px; padding: 0 2px; font-weight: bold;" title="{m["label"]}">{text[m["start"]:m["end"]]}</span>'
            results["highlighted_text"] = results["highlighted_text"][:m["start"]] + badge + results["highlighted_text"][m["end"]:]

        score = (results["breakdown"]["EMOTION"] * 10) + (results["breakdown"]["PRESSURE"] * 15) + (results["breakdown"]["LOGIC"] * 20)
        vader = self.vader.polarity_scores(text)
        if abs(vader['compound']) * 100 > 50: score += 15
        results["score"] = min(score, 100)
        
        results["verdict"] = self.generate_verdict(results["breakdown"], results["score"])
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
            if user_input.strip().startswith("http") or user_input.strip().startswith("www"):
                with st.spinner("🕷️ Crawling main article (using Trafilatura Engine)..."):
                    target_url = user_input.strip()
                    if target_url.startswith("www"): target_url = "https://" + target_url
                    scraped_text = ai.extract_from_url(target_url)
                    if "Error" in scraped_text: st.error(scraped_text)
                    else:
                        final_text_to_scan = scraped_text
                        st.success(f"Focused Scan: Analyzed {len(final_text_to_scan)} characters.")
            else: final_text_to_scan = user_input
    else:
        uploaded_file = st.file_uploader("Choose PDF", type="pdf")
        if uploaded_file is not None:
            if st.button("🚀 Process PDF", type="primary", use_container_width=True):
                ai = GeneralAI()
                with st.spinner("Extracting text from PDF..."):
                    final_text_to_scan = ai.extract_from_pdf(uploaded_file)
                    st.success(f"Extracted {len(final_text_to_scan)} characters.")

    if final_text_to_scan and len(final_text_to_scan) > 10:
        st.session_state['scan_result'] = GeneralAI().scan(final_text_to_scan)
        st.session_state['has_run'] = True
        st.toast("Scan Complete! Check Analysis tab.", icon="✅")

with tab2:
    if st.session_state.get('has_run'):
        data = st.session_state['scan_result']
        
        st.markdown(f"""
        <div style="background-color: #262730; padding: 20px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 25px;">
            <h3 style="margin-top:0;">🔎 Forensic Verdict</h3>
            <p style="font-size: 1.1em; margin-bottom: 0;">{data['verdict']}</p>
        </div>
        """, unsafe_allow_html=True)

        score = data['score']
        color = "green"
        if score > 40: color = "orange"
        if score > 70: color = "red"
        
        c_score, c_chart = st.columns([1, 2])
        
        with c_score:
            st.markdown(f"""
                <div style="text-align: center; border: 2px solid {color}; padding: 10px; border-radius: 10px;">
                    <h1 style="color:{color}; margin:0; font-size: 3em;">{score}</h1>
                    <p style="margin:0;">THREAT INDEX</p>
                </div>
            """, unsafe_allow_html=True)
        
        with c_chart:
            categories = ["EMOTION", "PRESSURE", "LOGIC"]
            values = [data["breakdown"]["EMOTION"], data["breakdown"]["PRESSURE"], data["breakdown"]["LOGIC"]]
            values += [values[0]]
            categories += [categories[0]]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#FF4B4B'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(max(values)+1, 5)])), showlegend=False, height=200, margin=dict(l=30, r=30, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.caption("Waiting for data...")

with tab3:
    if st.session_state.get('has_run'):
        data = st.session_state['scan_result']
        st.markdown(f"""<div style="padding: 15px; background-color: #0e1117; border: 1px solid #444; border-radius: 5px; font-family: sans-serif; line-height: 1.6; font-size: 0.9em;">{data['highlighted_text']}</div>""", unsafe_allow_html=True)
        st.markdown("""<div style="margin-top: 20px; font-size: 0.8em; color: #888;"><span style="color:#FF4B4B">■ Anger</span> &nbsp; <span style="color:#800080">■ Fear</span> &nbsp; <span style="color:#0068C9">■ Urgency</span> &nbsp; <span style="color:#00C9A7">■ Authority</span> &nbsp; <span style="color:#29B5E8">■ Social Proof</span> &nbsp; <span style="color:#FF8C00">■ Tribalism</span> &nbsp; <span style="color:#8D6E63">■ Sunk Cost</span></div>""", unsafe_allow_html=True)
    else:
        st.caption("Evidence will appear here.")
