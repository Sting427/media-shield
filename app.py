import streamlit as st
import trafilatura
from pypdf import PdfReader
import pandas as pd
import zipfile
import time
import plotly.graph_objects as go
from transformers import pipeline

# --- CONFIGURATION ---
st.set_page_config(page_title="Media Shield: Research Scanner", page_icon="🕵️", layout="wide")

# ==========================================
# 🧠 THE NEURAL ENGINE (BERT)
# ==========================================
@st.cache_resource
def load_brain():
    # Load Toxic-BERT. 
    # top_k=None ensures we get scores for ALL categories (toxic, threat, etc.)
    return pipeline("text-classification", model="unitary/toxic-bert", top_k=None)

class NeuralScanner:
    def __init__(self):
        self.classifier = load_brain()

    def analyze_batch(self, texts, progress_bar):
        """
        Analyzes a list of texts one by one and returns a list of results.
        Updates the progress bar as it goes.
        """
        results = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            try:
                # Analyze text (truncated to 512 chars for speed)
                prediction = self.classifier(text[:512])
                
                # Parse output
                # Output format: [[{'label': 'toxic', 'score': 0.9}, ...]]
                data = prediction[0] if isinstance(prediction, list) else prediction
                scores = {item['label']: item['score'] for item in data}
                
                # Calculate Composite Danger Score
                danger = (
                    scores.get('identity_hate', 0) * 100 + 
                    scores.get('threat', 0) * 80 + 
                    scores.get('severe_toxic', 0) * 60 +
                    scores.get('toxic', 0) * 30
                )
                
                results.append({
                    "text": text,
                    "danger_score": min(int(danger), 100),
                    "identity_hate": scores.get('identity_hate', 0),
                    "threat": scores.get('threat', 0),
                    "toxic": scores.get('toxic', 0)
                })
                
                # Update UI every step
                progress_bar.progress((i + 1) / total, text=f"Scanning record {i+1}/{total}...")
                
            except Exception as e:
                # If one fails, skip it, don't crash
                continue
                
        return pd.DataFrame(results)

# ==========================================
# 🛠️ DATA EXTRACTION
# ==========================================
def load_dataframe(file):
    """Smart loader that handles CSV or Zipped CSV"""
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        elif file.name.endswith('.zip'):
            with zipfile.ZipFile(file) as z:
                target = next((f for f in z.namelist() if f.endswith('.csv')), None)
                with z.open(target) as f:
                    return pd.read_csv(f)
    except: return None

def find_text_column(df):
    """Auto-detects the column containing the comments"""
    candidates = ['comment_text', 'text', 'content', 'tweet', 'message', 'review']
    for col in candidates:
        if col in df.columns: return col
    return df.columns[0] # Fallback

# ==========================================
# 🖥️ UI LAYOUT
# ==========================================
st.title("🕵️ Media Shield: Deep Scanner")
st.caption("Batch Analysis Tool • Upload Datasets to find Toxic Needles in the Haystack")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Scanner Settings")
    st.info("Higher depth = Longer wait time.")
    scan_limit = st.slider("Max Records to Scan:", min_value=10, max_value=200, value=20, step=10)
    st.markdown("---")
    st.caption("**Note on Speed:**\nThe AI takes about 0.5 seconds per record. Scanning 100 records takes ~50 seconds.")

col1, col2 = st.columns([1, 2])

# --- INPUT SECTION ---
with col1:
    st.subheader("1. Load Dataset")
    uploaded = st.file_uploader("Upload CSV or ZIP", type=["csv", "zip"])
    
    dataset = None
    text_col = None
    
    if uploaded:
        df = load_dataframe(uploaded)
        if df is not None:
            dataset = df
            text_col = find_text_column(df)
            st.success(f"Loaded {len(df)} rows.")
            st.info(f"Targeting Column: **'{text_col}'**")
            
            # Preview
            with st.expander("Preview Data"):
                st.dataframe(df.head(3))
        else:
            st.error("Could not read file.")

    start_btn = st.button("🚀 Start Deep Scan", type="primary", use_container_width=True, disabled=(dataset is None))

# --- REPORT SECTION ---
with col2:
    st.subheader("2. Audit Report")
    
    if start_btn and dataset is not None:
        scanner = NeuralScanner()
        
        # 1. Prepare the Batch
        # We take the top N rows based on the slider
        batch_data = dataset[text_col].astype(str).head(scan_limit).tolist()
        
        # 2. Run Analysis with Progress Bar
        progress = st.progress(0, text="Initializing Neural Engine...")
        results_df = scanner.analyze_batch(batch_data, progress)
        progress.empty() # Remove bar when done
        
        if not results_df.empty:
            # 3. CALCULATE STATS
            avg_danger = int(results_df['danger_score'].mean())
            toxic_count = len(results_df[results_df['danger_score'] > 50])
            hate_count = len(results_df[results_df['identity_hate'] > 0.5])
            
            # --- DASHBOARD METRICS ---
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Avg Toxicity", f"{avg_danger}/100", delta_color="inverse")
            with m2:
                st.metric("Toxic Records", f"{toxic_count} / {scan_limit}")
            with m3:
                st.metric("Hate Crimes", f"{hate_count}", help="Rows with confirmed Identity Hate")
                
            # --- PIE CHART ---
            # Categorize the results
            safe = len(results_df[results_df['danger_score'] < 30])
            sus = len(results_df[(results_df['danger_score'] >= 30) & (results_df['danger_score'] < 70)])
            danger = len(results_df[results_df['danger_score'] >= 70])
            
            fig = go.Figure(data=[go.Pie(
                labels=['Safe', 'Suspicious', 'Dangerous'],
                values=[safe, sus, danger],
                hole=.4,
                marker_colors=['#4CAF50', '#FFA500', '#FF0000']
            )])
            fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- THE "WORST OFFENDERS" TABLE ---
            st.subheader("🚩 The Worst Offenders")
            st.caption("These rows triggered the highest alarms:")
            
            # Sort by danger score descending
            worst_df = results_df.sort_values(by="danger_score", ascending=False).head(5)
            
            for index, row in worst_df.iterrows():
                # Dynamic Border Color
                b_color = "#FF0000" if row['danger_score'] > 80 else "#FFA500"
                
                st.markdown(f"""
                <div style="border-left: 5px solid {b_color}; background-color: #262730; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold; color: {b_color};">THREAT SCORE: {row['danger_score']}</span>
                        <span style="color: #aaa; font-size: 0.8em;">Identity Hate Confidence: {int(row['identity_hate']*100)}%</span>
                    </div>
                    <p style="margin-top: 5px; font-style: italic;">"{row['text'][:200]}..."</p>
                </div>
                """, unsafe_allow_html=True)
                
            # Download Full Report
            csv_data = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Full Forensic Report",
                data=csv_data,
                file_name="toxicity_audit_report.csv",
                mime="text/csv"
            )

    elif dataset is None:
        st.info("👈 Upload a dataset to begin the audit.")
