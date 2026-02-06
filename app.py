import streamlit as st
import nltk
import ssl

# --- CLOUD FIX: AUTO-DOWNLOAD BRAINS ---
# This forces the cloud computer to download the necessary dictionaries
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download specific NLTK data required by TextBlob
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('averaged_perceptron_tagger_eng')

# --- NOW IMPORT THE REST ---
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Media Shield", page_icon="🛡️", layout="wide")

# ==========================================
# 🧠 INTELLIGENCE DICTIONARIES
# ==========================================
VIRAL_TRIGGERS = {
    "😡 ANGER": ["scandal", "eviscerated", "misogynist", "racist", "censored", "banned", "cover-up", "outrage", "shameful", "hypocrisy", "lies", "attack", "destroy", "victim"],
    "😱 FEAR": ["toxic", "lethal", "crisis", "collapse", "warning", "danger", "risk", "poison", "meltdown", "apocalypse", "deadly", "threat", "emergency", "fatal"],
    "😲 SHOCK": ["mind-blowing", "unprecedented", "secret", "genius", "insane", "bizarre", "perfection", "never-before-seen", "shocking", "magic", "stunning", "miracle"],
    "🔞 NSFW": ["uncensored", "naked", "leaked", "tape", "explicit", "nsfw", "raw", "exposed", "seductive", "forbidden", "nude"]
}

WEAK_SOURCES = ["reports are surfacing", "according to a tipster", "we are hearing", "sources tell us", "rumors", "people are saying", "allegedly", "reportedly", "supposedly"]

class MediaShieldScanner:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def analyze_sentence(self, sentence_obj):
        text = sentence_obj.string
        score = 0
        flags = []
        
        # 1. EMOTIONAL INTENSITY (VADER)
        vader_score = self.vader.polarity_scores(text)
        intensity = abs(vader_score['compound']) * 100
        if intensity > 60:
            score += 30
            flags.append(f"High Intensity ({int(intensity)}%)")

        # 2. SUBJECTIVITY (TextBlob)
        subj = sentence_obj.sentiment.subjectivity
        if subj > 0.7:
            score += 25
            flags.append(f"High Subjectivity ({int(subj*100)}%)")

        # 3. VIRAL TRIGGERS
        for category, keywords in VIRAL_TRIGGERS.items():
            found = [word for word in keywords if word in text.lower()]
            if found:
                score += (len(found) * 20)
                flags.append(f"{category} Trigger")

        # 4. WEAK SOURCING
        for phrase in WEAK_SOURCES:
            if phrase in text.lower():
                score += 25
                flags.append("Weak Sourcing")

        return min(score, 100), flags

    def scan_text(self, full_text):
        blob = TextBlob(full_text)
        sentences = blob.sentences
        
        total_sentences = len(sentences)
        toxic_sentences = []
        cumulative_score = 0
        
        for i, sent in enumerate(sentences):
            risk_score, flags = self.analyze_sentence(sent)
            if risk_score > 40:
                toxic_sentences.append({
                    "index": i + 1,
                    "text": sent.string,
                    "score": risk_score,
                    "flags": flags
                })
            cumulative_score += risk_score

        if total_sentences < 2:
            final_score = cumulative_score
        else:
            infection_rate = (len(toxic_sentences) / total_sentences) 
            final_score = min(infection_rate * 250, 100) 

        return {
            "score": int(final_score),
            "sentence_count": total_sentences,
            "toxic_count": len(toxic_sentences),
            "toxic_list": sorted(toxic_sentences, key=lambda x: x['score'], reverse=True)
        }

# ==========================================
# 🖥️ UI LAYOUT
# ==========================================
st.title("🛡️ Media Shield: Cloud Edition")
st.caption("Forensic Logic Online • Powered by VADER & TextBlob")

text_input = st.text_area("Paste Article or Headline:", height=200, placeholder="Paste text here to run forensic scan...")
btn = st.button("Run Forensic Scan", type="primary")

if btn and text_input:
    scanner = MediaShieldScanner()
    with st.spinner("Analyzing linguistic patterns..."):
        time.sleep(0.5)
        report = scanner.scan_text(text_input)
        
    score = report['score']
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        color = "green"
        if score > 40: color = "orange"
        if score > 70: color = "red"
        st.markdown(f"""
            <div style="text-align: center; border: 2px solid {color}; padding: 10px; border-radius: 10px;">
                <h1 style="color:{color}; margin:0;">{score}/100</h1>
                <p>Infection Score</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.metric("Sentences Scanned", report['sentence_count'])
        st.metric("Toxic Sentences", report['toxic_count'])

    with col3:
        if score > 70:
            st.error("🚨 CRITICAL: Heavily saturated with manipulative language.")
        elif score > 40:
            st.warning("⚠️ SUSPICIOUS: Contains high levels of subjectivity.")
        else:
            st.success("✅ CLEAN: Mostly objective reporting.")

    st.divider()

    if report['toxic_list']:
        st.subheader("🚩 The Evidence Locker")
        for item in report['toxic_list']:
            with st.expander(f"Risk {item['score']}%: \"{item['text'][:50]}...\"", expanded=True):
                st.markdown(f"**Full Text:** *{item['text']}*")
                for flag in item['flags']:
                    st.code(flag)
    else:
        st.info("No specifically toxic sentences found.")
        
