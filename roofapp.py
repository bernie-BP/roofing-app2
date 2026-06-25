import streamlit as st
import math
import os
import re
import base64

# Safely import pypdf for text parsing
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# Wide layout configuration to give ample space for the split panel view
st.set_page_config(page_title="Roofing Material Calculator", page_icon="🏠", layout="wide")

def get_num(val):
    if not val or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).strip().replace(',', ''))
    except ValueError:
        return 0.0

# Helper function to convert PDF bytes to an embedded base64 scrollable frame
def display_pdf_scrollable(file_bytes):
    base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf" style="border:1px solid #ccc; border-radius:5px;"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

if os.path.exists("logo.png"):
    st.image("logo.png", width=200)

st.title("Roofing Material Ordering Dashboard")
st.write("Drop your job files below to scroll through blueprints and pricing models on the right while managing parameters on the left.")

# ==========================================
# 📋 TWO-FILE UPLOADER HUB
# ==========================================
scanned_vals = {"pitched_sq": "", "flat_sq": "", "eaves": "", "valleys": "", "hips": "", "ridges": "", "rakes": ""}
roofr_file_bytes = None
quote_file_bytes = None

st.header("📋 Automated Document Upload Hub")

# Twin File Upload Row
up_col1, up_col2 = st.columns(2)

with up_col1:
    uploaded_roofr = st.file_uploader("1. Upload Roofr Measurement Report (PDF)", type=["pdf"])
with up_col2:
    uploaded_quote = st.file_uploader("2. Upload Estimate / Supplier Quote (PDF)", type=["pdf"])

# Process File 1: Roofr Takeoff Text Parsing
if uploaded_roofr is not None:
    try:
        roofr_file_bytes = uploaded_roofr.read()
        uploaded_roofr.seek(0)
        
        if PYPDF_AVAILABLE:
            reader = pypdf.PdfReader(uploaded_roofr)
            full_text = ""
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    full_text += text_content + "\n"
            
            def parse_metric(pattern, text):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                return ""

            raw_pitched_ft = parse_metric(r"Pitched\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
            raw_flat_ft = parse_metric(r"Flat\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
            
            if not raw_pitched_ft:
                raw_pitched_ft = parse_metric(r"Pitched\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
            if not raw_flat_ft:
                raw_flat_ft = parse_metric(r"Flat\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
            
            if not raw_pitched_ft and not raw_flat_ft:
                universal_ft = parse_metric(r"(?:Total Area|Squares)\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                raw_pitched_ft = universal_ft
                raw_flat_ft = universal_ft

            if raw_pitched_ft:
                scanned_vals["pitched_sq"] = f"{get_num(raw_pitched_ft) / 100:.1f}"
            if raw_flat_ft:
                scanned_vals["flat_sq"] = f"{get_num(raw_flat_ft) / 100:.1f}"

            scanned_vals["eaves"] = parse_metric(r"Eaves\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["valleys"] = parse_metric(r"Valleys\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["hips"] = parse_metric(r"Hips\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["ridges"] = parse_metric(r"Ridges?\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["rakes"] = parse_metric(r"Rakes\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            
            st.success("✅ Roofr measurements scanned into left-side configuration controls!")
    except Exception as e:
        st.error(f"Could not parse Roofr text rules. Error: {e}")

# Process File 2: Catch bytes for Quote display
if uploaded_quote is not None:
    quote_file_bytes = uploaded_quote.read()

st.markdown("---")

# ==========================================
# 🗺️ SPLIT DASHBOARD LAYOUT (LEFT/RIGHT)
# ==========================================
left_panel, right_panel = st.columns([1.0, 1.0], gap="large")

# 📥 LEFT PANEL: MATERIAL ENGINE CONFIGURATION
with left_panel:
    st.subheader("🛠️ Production Controls & Layout Settings")
    
    material_type = st.radio("Material Type", options=["Tile", "Shingles", "Mod Bit"], horizontal=True)
    job_type = st.radio("Job Type", options=["New Tile", "Re-Roof"], horizontal=True) if material_type == "Tile" else None
    
    st.markdown("### 📏 Dimensions")
    
    if material_type == "Mod Bit":
        mod_sq = get_num(st.text_input("Square Count (SQ)", value=scanned_vals["flat_sq"]))
        mod_eaves = get_num(st.text_input("Eaves (Linear Feet)", value=scanned_vals["eaves"]))
        mod_rakes = get_num(st.text_input("Rakes (Linear Feet)", value=scanned_vals["rakes"]))
        
        CAPSHEET_COLORS = ["Buff", "Grey Slate", "Black", "White", "Weatherwood"]
        cap_color = st.selectbox("Cap Sheet Color", CAPSHEET_COLORS)
        mod_bit_base_type = st.selectbox("Select Base Layer Material Type", options=["Base Sheet (2 SQ per roll)", "SAV 9\" Self-Adhered (66 LF per roll)"])
        
        drip_edge_length = 10
        mb_drip_pieces = (math.ceil(mod_eaves / drip_edge_length) if mod_eaves > 0 else 0) + 2
        cap_rolls = math.ceil(mod_sq) if mod_sq > 0 else 0
        
        if mod_bit_base_type == "Base Sheet (2 SQ per roll)":
            base_rolls = math.ceil(mod_sq / 2) if mod_sq > 0 else 0
            base_description, base_quantity_str = "Polyglass Base Sheet", f"{base_rolls} Rolls (covers {base_rolls * 2} SQ)"
        else:
            base_rolls = math.ceil((mod_eaves + mod_rakes) / 66) if (mod_eaves + mod_rakes) > 0 else 0
            base_description, base_quantity_str = 'Polyglass SAV 9" Self-Adhered (66 LF/roll)', f"{base_rolls} Rolls ({mod_eaves + mod_rakes:.0f} LF @ 66 LF/roll)"
            
    else:
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            sq_count = get_num(st.text_input("Square Count (SQ)", value=scanned_vals["pitched_sq"]))
            product = st.selectbox("Product Profile", ["Eagle (S-Profile)", "Eagle (W-Profile)", "Eagle (Flat)", "Westlake (S-Profile)", "Westlake (W-Profile)", "Westlake (Flat)"] if material_type == "Tile" else ["GAF Timberline HDZ (Architectural)", "GAF Royal Sovereign (3-Tab)", "GAF Timberline UHDZ"])
            eaves = get_num(st.text_input("Eaves (Linear Feet)", value=scanned_vals["eaves"]))
            valleys = get_num(st.text_input("Valleys (Linear Feet)", value=scanned_vals["valleys"]))
        with sub_col2:
            hips = get_num(st.text_input("Hips (Linear Feet)", value=scanned_vals["hips"]))
