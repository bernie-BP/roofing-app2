import streamlit as st
import streamlit.components.v1 as components
import math
import os
import re
import base64
import requests
import json
from io import BytesIO

# Handle backend PDF graphic engines safely
try:
    import pypdf
    from pdf2image import convert_from_bytes
    PDF_ENGINES_AVAILABLE = True
except ImportError:
    PDF_ENGINES_AVAILABLE = False

# Wide layout configuration to give ample space for the split panel view
st.set_page_config(page_title="RealRoofing MO Dashboard", page_icon="🏠", layout="wide")

# Fetch secure tokens from Streamlit configuration vault
JN_TOKEN = st.secrets.get("JOBNIMBUS_TOKEN", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

def get_num(val):
    if not val or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).strip().replace(',', ''))
    except ValueError:
        return 0.0

# --- 🚀 CACHING PERFORMANCE ENGINE ---
@st.cache_data(show_spinner=False)
def cached_pdf_to_html_viewport(target_bytes, label_tag):
    """Converts PDF pages to base64 images once and caches the result to prevent UI stutter."""
    if not target_bytes:
        return ""
    all_images = convert_from_bytes(target_bytes)
    html_content = '<div style="height: 750px; overflow-y: scroll; border: 2px solid #4A5568; border-radius: 8px; padding: 10px; background-color: #1A202C;">'
    for i, page_img in enumerate(all_images):
        buffered = BytesIO()
        page_img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        html_content += f'<div style="text-align: center; margin-bottom: 20px;"><p style="color: #A0AEC0; font-family: sans-serif; font-size: 14px;">📄 {label_tag} — Page {i+1}</p><img src="data:image/jpeg;base64,{img_base64}" style="width: 100%; max-width: 800px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);"></div>'
    html_content += '</div>'
    return html_content

def ask_ai_to_extract_contract_metadata(contract_text):
    """Sends raw homeowner contract text to Google Gemini API to extract customer selections."""
    if not GEMINI_KEY:
        return {"po": "", "tile_type": "", "birdstop": "Black", "drip_edge": "White"}
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    You are a professional roofing production assistant. Analyze the following text extracted from a signed homeowner contract and extract the construction selections accurately:
    1. Customer Name or Job Reference Name (To be used as the PO Number)
    2. Specific Tile Profile, Brand, or Shingle Style chosen (e.g., Eagle Flat, Westlake S-Profile, GAF HDZ)
    3. Birdstop Color specified (e.g., Black, Terracotta, Brown, Grey)
    4. Drip Edge Color selected by the customer (e.g., White, Bronze, Charcoal, Black)

    Return ONLY a valid JSON object with the exact keys: "po", "tile_type", "birdstop", "drip_edge". 
    Do not include any markdown wrappers like backticks or regular prose.
    
    Contract Text Document Content:
    {contract_text[:6000]}
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            res_json = response.json()
            text_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_response)
    except Exception:
        pass
    return {"po": "", "tile_type": "", "birdstop": "Black", "drip_edge": "White"}

# --- 🧠 STATE MANAGEMENT INITIALIZATION ---
if "scanned_vals" not in st.session_state:
    st.session_state.scanned_vals = {"pitched_sq": "0.0", "flat_sq": "0.0", "eaves": "0.0", "valleys": "0.0", "hips": "0.0", "ridges": "0.0", "rakes": "0.0"}

if "ai_metadata" not in st.session_state:
    st.session_state.ai_metadata = {"po": "", "tile_type": "", "birdstop": "Black", "drip_edge": "White"}

if "processed_roofr_hash" not in st.session_state:
    st.session_state.processed_roofr_hash = None

if "processed_contract_hash" not in st.session_state:
    st.session_state.processed_contract_hash = None

if os.path.exists("logo.png"):
    st.image("logo.png", width=200)

st.title("RealRoofing MO Production Dashboard")
st.write("Upload your structural reports and signed customer contracts to automatically cross-reference data and generate material orders.")

# ==========================================
# 📋 TWO-FILE UPLOADER HUB
# ==========================================
st.header("📋 Automated Document Upload Hub")
roofr_pages_bytes = None
contract_pages_bytes = None

if not PDF_ENGINES_AVAILABLE:
    st.info("💡 *PDF Processing Modules are active when deployed live with pypdf and pdf2image requirements.*")
else:
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        uploaded_roofr = st.file_uploader("1. Upload Roofr Measurement Report (PDF)", type=["pdf"])
    with up_col2:
        uploaded_contract = st.file_uploader("2. Upload Signed Homeowner Contract (PDF)", type=["pdf"])
    
    # 📐 ROOFR DATA PARSING GATEWAY
    if uploaded_roofr is not None:
        roofr_pages_bytes = uploaded_roofr.getvalue()
        current_roofr_hash = f"{uploaded_roofr.name}_{len(roofr_pages_bytes)}"
        
        if st.session_state.processed_roofr_hash != current_roofr_hash:
            try:
                reader = pypdf.PdfReader(BytesIO(roofr_pages_bytes))
                full_text = ""
                for page in reader.pages:
                    text_content = page.extract_text()
                    if text_content:
                        full_text += text_content + "\n"
                
                def parse_metric(pattern, text):
                    match = re.search(pattern, text, re.IGNORECASE)
                    return match.group(1).strip() if match else "0"

                raw_pitched_ft = parse_metric(r"Pitched\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                raw_flat_ft = parse_metric(r"Flat\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                
                if raw_pitched_ft == "0":
                    raw_pitched_ft = parse_metric(r"Pitched\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
                if raw_flat_ft == "0":
                    raw_flat_ft = parse_metric(r"Flat\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
                
                if raw_pitched_ft == "0" and raw_flat_ft == "0":
                    universal_ft = parse_metric(r"(?:Total Area|Squares)\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                    raw_pitched_ft = universal_ft
                    raw_flat_ft = universal_ft

                st.session_state.scanned_vals["pitched_sq"] = f"{get_num(raw_pitched_ft) / 100:.1f}"
                st.session_state.scanned_vals["flat_sq"] = f"{get_num(raw_flat_ft) / 100:.1f}"
                st.session_state.scanned_vals["eaves"] = parse_metric(r"Eaves\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
                st.session_state.scanned_vals["valleys"] = parse_metric(r"Valleys\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
                st.session_state.scanned_vals["hips"] = parse_metric(r"Hips\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
                st.session_state.scanned_vals["ridges"] = parse_metric(r"Ridges?\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
                st.session_state.scanned_vals["rakes"] = parse_metric(r"Rakes\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
                
                st.session_state.processed_roofr_hash = current_roofr_hash
                st.success
