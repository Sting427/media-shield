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
st.set_page_config(page_title="Media Shield: Forensic Lab", page_icon="🛡️", layout="wide")

# INTELLIGENCE DICTIONARY (Expanded)
TRIGGERS = {
    "ANGER": {
        "color": "#FF4B4B", # Red
        "words": ["scandal", "eviscerated", "misogynist", "racist", "censored", "banned", "cover-up", "outrage", "shameful", "hypocrisy", "lies", "attack", "destroy", "victim", "furious"]
    },
    "FEAR": {
        "color": "#800080", # Purple
        "words": ["toxic", "lethal", "crisis", "collapse", "warning", "danger", "risk", "poison", "meltdown", "apocalypse", "deadly", "threat", "emergency", "fatal"]
    },
    "SHOCK": {
        "color": "#FFA500", # Orange
        "words": ["mind-blowing", "unprecedented", "secret", "genius", "insane", "bizarre", "perfection", "shocking", "magic", "stunning", "miracle", "baffling"]
    },
    "WEASEL": {
        "color": "#808080", # Grey
        "words": ["reportedly", "supposedly", "purportedly", "sources say", "rumors", "allegedly", "it appears", "some people"]
    }
}

class ForensicEngine:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def generate_highlighted_text(self, text):
        """
        Replaces trigger words with HTML badges.
        """
        highlighted = text
        # Sort words by length (descending) so we don't replace substrings incorrectly
        all_triggers = []
        for category, data in TRIGGERS.items():
            for word in data["words"]:
                all_triggers.append((word, category, data["color"]))
        
        all_triggers.sort(key=lambda x: len(x[0]), reverse=True)

        for word, category, color in all_triggers:
            # Regex to match whole words, case-insensitive
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            # The HTML replacement (Mark tag)
            replacement = f'<span style="background-color: {color}33; border-bottom: 2px solid {color}; padding: 0 4px; border-radius: 4px; font-weight: bold;" title="{category} Trigger">{word.upper()}</span>'
            highlighted = pattern.sub(replacement, highlighted)
            
        return highlighted

    def analyze(self, text):
        blob = TextBlob(text)
        results = {
            "intensity": 0,
            "subjectivity": blob.sentiment.subjectivity * 100,
            "counts": {"ANGER": 0, "FEAR": 0, "SHOCK": 0, "WEASEL": 0},
            "highlighted_html": self.generate_highlighted_text(text)
        }

        # VADER Intensity
        v_score = self.vader.polarity_scores(text)
        results["intensity"] = abs(v_score['compound']) * 100

        # Trigger Counting
        text_lower = text.lower()
        for cat, data in TRIGGERS.items():
            for word in data["words"]:
                if word in text_lower:
                    results["counts"][cat] += 1
        
        # Final Score Calc
        base_score = results["intensity"] * 0.5 + results["subjectivity"] * 0.3
        trigger_penalty = sum(results["counts"].values()) * 5
        results["final_score"] = min(base_score + trigger_penalty, 100)
        
        return results

# --- UI ---
st.title("🛡️ Media Shield: The Forensic Lab")
st.markdown("### Visualizing the Anatomy of Manipulation")

col_input, col_viz = st.columns([1, 1])

with col_input:
    st.subheader("1. Input Source")
    text_input = st.text_area("Paste Article Here:", height=400, placeholder="Paste text...")
    run_btn = st.button("🔬 Run Forensic Scan", type="primary")

if run_btn and text_input:
    engine = ForensicEngine()
    data = engine.analyze(text_input)
    
    with col_viz:
        st.subheader("2. The Bias Radar")
        
        # RADAR CHART (The "Fingerprint")
        categories = list(data["counts"].keys())
        values = list(data["counts"].values())
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Triggers'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(max(values)+1, 5)])),
            showlegend=False,
            height=300,
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        # METRICS
        m1, m2 = st.columns(2)
        m1.metric("Manipulation Score", f"{int(data['final_score'])}/100")
        m2.metric("Subjectivity", f"{int(data['subjectivity'])}%")
        
        if data['final_score'] > 70:
            st.error("🚨 CRITICAL MANIPULATION DETECTED")
        elif data['final_score'] > 40:
            st.warning("⚠️ SUSPICIOUS CONTENT")
        else:
            st.success("✅ CLEAN CONTENT")

    # --- THE HIGHLIGHTER (Full Width) ---
    st.divider()
    st.subheader("3. X-Ray View (Trigger Visualization)")
    st.caption("We have highlighted the specific words triggering the forensic filters.")
    
    # Render the HTML
    st.markdown(f"""
    <div style="padding: 20px; background-color: #0e1117; border: 1px solid #333; border-radius: 10px; line-height: 1.6; font-family: sans-serif;">
        {data['highlighted_html']}
    </div>
    """, unsafe_allow_html=True)

    # Legend
    st.markdown("""
    <br>
    <span style="color:#FF4B4B">■ Anger</span> &nbsp; 
    <span style="color:#800080">■ Fear</span> &nbsp; 
    <span style="color:#FFA500">■ Shock</span> &nbsp; 
    <span style="color:#808080">■ Weasel Words</span>
    """, unsafe_allow_html=True)
