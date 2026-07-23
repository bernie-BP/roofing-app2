import base64
import json
import math
import os
import re
from io import BytesIO

import requests
import streamlit as st
import streamlit.components.v1 as components

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
    
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            res_json = response.json()
            text_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_response)
    except Exception as err:
        st.warning(f"Metadata extraction fallback triggered: {err}")
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
# 📋 UPLOADER HUB
# ==========================================
st.header("📋 Automated Document Upload Hub")
roofr_pages_bytes = None
contract_pages_bytes = None

if not PDF_ENGINES_AVAILABLE:
    st.info("💡 *PDF Processing Modules are active when deployed live with pypdf and pdf2image requirements.*")
else:
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        uploaded_roofr = st.file_uploader("1. Roofr Measurement (PDF)", type=["pdf"])
    with up_col2:
        uploaded_contract = st.file_uploader("2. Signed Contract (PDF)", type=["pdf"])
    
    if uploaded_roofr is not None:
        roofr_pages_bytes = uploaded_roofr.getvalue()
        current_roofr_hash = f"{uploaded_roofr.name}_{len(roofr_pages_bytes)}"
        if st.session_state.processed_roofr_hash != current_roofr_hash:
            try:
                reader = pypdf.PdfReader(BytesIO(roofr_pages_bytes))
                full_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
                
                def parse_metric(pattern, text):
                    match = re.search(pattern, text, re.IGNORECASE)
                    return match.group(1).strip() if match else "0"

                raw_pitched_ft = parse_metric(r"Pitched\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                raw_flat_ft = parse_metric(r"Flat\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                if raw_pitched_ft == "0": raw_pitched_ft = parse_metric(r"Pitched\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
                if raw_flat_ft == "0": raw_flat_ft = parse_metric(r"Flat\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
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
                st.success("✅ Roofr measurements scanned!")
            except Exception as e: st.error(f"Could not parse Roofr text. Error: {e}")

    if uploaded_contract is not None:
        contract_pages_bytes = uploaded_contract.getvalue()
        current_contract_hash = f"{uploaded_contract.name}_{len(contract_pages_bytes)}"
        if st.session_state.processed_contract_hash != current_contract_hash:
            try:
                contract_reader = pypdf.PdfReader(BytesIO(contract_pages_bytes))
                contract_text = "".join([page.extract_text() for page in contract_reader.pages if page.extract_text()])
                with st.spinner("AI is analyzing signed contract..."):
                    st.session_state.ai_metadata = ask_ai_to_extract_contract_metadata(contract_text)
                    st.session_state.processed_contract_hash = current_contract_hash
                    st.success("✅ Signed contract processed!")
            except Exception as e: st.error(f"Error reading contract: {e}")

st.markdown("---")

# ==========================================
# 🗺️ SPLIT DASHBOARD LAYOUT (LEFT/RIGHT)
# ==========================================
left_panel, right_panel = st.columns([1.0, 1.0], gap="large")

with left_panel:
    st.subheader("🛠️ Production Controls & Layout Settings")
    
    # MOVED: Top level layout selections using radio buttons
    material_type = st.radio("Material Type", options=["Tile", "Shingles", "Mod Bit"], horizontal=True)
    job_type = st.radio("Job Type", options=["New Tile", "Re-Roof"], index=1, horizontal=True) if material_type == "Tile" else None
    
    if material_type != "Mod Bit":
        underlayment_roll_size = st.radio("Underlayment Roll Size", options=[2, 5, 10], format_func=lambda x: f"{x} SQ roll", horizontal=True)
    
    st.markdown("### 📏 Dimensions")
    if material_type == "Mod Bit":
        mod_sq = get_num(st.text_input("Square Count (SQ)", value=st.session_state.scanned_vals["flat_sq"]))
        mod_eaves = get_num(st.text_input("Eaves (Linear Feet)", value=st.session_state.scanned_vals["eaves"]))
        mod_rakes = get_num(st.text_input("Rakes (Linear Feet)", value=st.session_state.scanned_vals["rakes"]))
        CAPSHEET_COLORS = ["Buff", "Grey Slate", "Black", "White", "Weatherwood"]
        cap_color = st.selectbox("Cap Sheet Color", CAPSHEET_COLORS)
        mod_bit_base_type = st.selectbox("Select Base Layer Material Type", options=["Base Sheet (2 SQ per roll)", "SAV 9\" Self-Adhered (66 LF per roll)"])
        
        drip_edge_length = 10
        mb_drip_pieces = (math.ceil(mod_eaves / drip_edge_length) if mod_eaves > 0 else 0) + 2
        cap_rolls = math.ceil(mod_sq) if mod_sq > 0 else 0
        
        if mod_bit_base_type == "Base Sheet (2 SQ per roll)":
            base_rolls = math.ceil(mod_sq / 2) if mod_sq > 0 else 0
            base_description, base_quantity_str = "Polyglass Base Sheet", f"{base_rolls}"
        else:
            base_rolls = math.ceil((mod_eaves + mod_rakes) / 66) if (mod_eaves + mod_rakes) > 0 else 0
            base_description, base_quantity_str = 'Polyglass SAV 9" Self-Adhered', f"{base_rolls}"
            
        descriptions = [f"Polyglass Cap Sheet — {cap_color}", base_description, "Drip Edge (10ft)"]
        quantities = [f"{cap_rolls}", f"{base_rolls}", f"{mb_drip_pieces}"]
    else:
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            sq_count = get_num(st.text_input("Square Count (SQ)", value=st.session_state.scanned_vals["pitched_sq"]))
            product = st.selectbox("Product Profile", ["Eagle (S-Profile)", "Eagle (W-Profile)", "Eagle (Flat)", "Westlake (S-Profile)", "Westlake (W-Profile)", "Westlake (Flat)"] if material_type == "Tile" else ["GAF Timberline HDZ", "GAF Royal Sovereign", "GAF Timberline UHDZ"])
            eaves = get_num(st.text_input("Eaves (Linear Feet)", value=st.session_state.scanned_vals["eaves"]))
            valleys = get_num(st.text_input("Valleys (Linear Feet)", value=st.session_state.scanned_vals["valleys"]))
        with sub_col2:
            hips = get_num(st.text_input("Hips (Linear Feet)", value=st.session_state.scanned_vals["hips"]))
            ridges = get_num(st.text_input("Ridges (Linear Feet)", value=st.session_state.scanned_vals["ridges"]))
            rakes = get_num(st.text_input("Rakes (Linear Feet)", value=st.session_state.scanned_vals["rakes"]))
            waste_pct = get_num(st.text_input("Waste Factor (%)", value="10"))

        drip_edge_length = 10
        WASTE_FACTOR = 1 + (waste_pct / 100)
        hip_ridge_lf = hips + ridges
        underlayment_rolls = math.ceil((sq_count * 1.15) / underlayment_roll_size)
        valley_pieces = math.ceil(valleys / 10) if valleys > 0 else 0
        
        if material_type == "Tile":
            total_squares_with_waste = sq_count * WASTE_FACTOR
            pallets_needed = (0.5 if sq_count < 20 else math.ceil((sq_count / 20) * 2) / 2) if job_type == "Re-Roof" else math.ceil(total_squares_with_waste / 2.97)
                
            tile_drip_pieces = (math.ceil(eaves / drip_edge_length) if eaves > 0 else 0) + 2
            birdstop_pieces = (math.ceil(eaves / 10) if eaves > 0 else 0) + 2
            is_flat_tile = "Flat" in product
            batten_bundles = math.ceil(sq_count)
            hip_bundles = 0 if is_flat_tile else math.ceil(hips / 25)
            ridge_bundles = math.ceil(hip_ridge_lf / 100) if is_flat_tile else math.ceil(ridges / 50)
            
            hip_ridge_desc = ["Hip Closures", "Ridge Closures"] if not is_flat_tile else ["Hip & Ridge Closures"]
            hip_ridge_qty = [f"{hip_bundles}", f"{ridge_bundles}"] if not is_flat_tile else [f"{ridge_bundles}"]
            descriptions = [f"Field Tile: {product}", f"Tile Underlayment ({underlayment_roll_size} SQ)", *hip_ridge_desc, "Roof Battens", "Birdstop Pieces", "Drip Edge"]
            quantities = [f"{pallets_needed:g}", f"{underlayment_rolls}", *hip_ridge_qty, f"{batten_bundles}", f"{birdstop_pieces}", f"{tile_drip_pieces}"]
        else:
            # --- SHINGLE CALCULATIONS ---
            total_squares_with_waste = sq_count * WASTE_FACTOR
            shingle_drip_pieces = (math.ceil((eaves + rakes) / drip_edge_length) if (eaves + rakes) > 0 else 0) + 2
            field_bundles = math.ceil(total_squares_with_waste * 3)
            hip_ridge_bundles = math.ceil(hip_ridge_lf / 33) if hip_ridge_lf > 0 else 0
            
            # 1. GAF Pro Start: Eaves + Rakes @ 120 LF per bundle (No waste)
            eaves_and_rakes_lf = eaves + rakes
            pro_start_bundles = math.ceil(eaves_and_rakes_lf / 120) if eaves_and_rakes_lf > 0 else 0
            
            # 2. GAF WeatherWatch: Valleys + Eaves @ 3ft roll width (2 SQ / 200 sq ft per roll) (No waste)
            valleys_and_eaves_lf = valleys + eaves
            weather_watch_sqft = valleys_and_eaves_lf * 3  # 3ft width coverage
            weather_watch_rolls = math.ceil(weather_watch_sqft / 200) if valleys_and_eaves_lf > 0 else 0
            
            field_nail_boxes = math.ceil(sq_count / 20) if sq_count > 0 else 0
            eave_nail_boxes  = math.ceil(sq_count / 20) if sq_count > 0 else 0
            cap_nail_boxes   = math.ceil(sq_count / 20) if sq_count > 0 else 0
            
            descriptions = [
                f"Field Shingles: {product}", 
                f"Underlayment ({underlayment_roll_size} SQ)", 
                "GAF WeatherWatch Leak Barrier (2 SQ Roll)",
                "GAF Pro Start Starter Strip", 
                "Hip & Ridge Cap", 
                "Drip Edge Pieces", 
                "Shingle Field Nails", 
                "Eave Coil Nails", 
                "Plastic Cap Nails"
            ]
            quantities = [
                f"{field_bundles}", 
                f"{underlayment_rolls}", 
                f"{weather_watch_rolls}",
                f"{pro_start_bundles}", 
                f"{hip_ridge_bundles}", 
                f"{shingle_drip_pieces}", 
                f"{field_nail_boxes}", 
                f"{eave_nail_boxes}", 
                f"{cap_nail_boxes}"
            ]

    # Valley Flashing (W-Valley) only applies to Tile installations
    if material_type == "Tile" and valleys > 0:
        descriptions.append("Valley Flashing (W-Valley)")
        quantities.append(f"{valley_pieces}")

    st.markdown("---")
    st.subheader("📝 Verify Contract Selections")
    ai_vals = st.session_state.ai_metadata
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        final_po = st.text_input("PO Number / Reference", value=ai_vals.get("po", ""))
        final_tile = st.text_input("Contracted Tile/Product Profile", value=ai_vals.get("tile_type", ""))
    with col_m2:
        final_birdstop = st.text_input("Birdstop Color Spec", value=ai_vals.get("birdstop", "Black"))
        final_drip = st.text_input("Drip Edge Color Spec", value=ai_vals.get("drip_edge", "White"))

# 🖼️ RIGHT PANEL: SCROLLABLE GRAPHICS VIEWPORT
with right_panel:
    st.subheader("🖼️ Document Reference Panel")
    view_toggle = st.radio("Display View Mode", options=["1. Roofr Measurement Blueprint", "2. Signed Homeowner Contract"], horizontal=True)
    st.markdown("---")
    
    target_bytes = roofr_pages_bytes if "Roofr" in view_toggle else contract_pages_bytes
    label_tag = "Roofr Takeoff Blueprint" if "Roofr" in view_toggle else "Signed Homeowner Contract"
    
    if target_bytes is not None:
        try:
            with st.spinner("Compiling continuous view layouts..."):
                html_rendered = cached_pdf_to_html_viewport(target_bytes, label_tag)
                components.html(html_rendered, height=770, scrolling=False)
        except Exception as err: st.caption("Rendering visual reference layout frame...")
    else: st.info("💡 Drop your PDF files into the uploader matrix above to unlock the scrollable window for this document.")

# 📋 BOTTOM ROW: DRAFT ORDER TABLE ENGINE
st.markdown("---")
st.header("2. Calculated Material Order Manifest")
manifest_ready = (material_type == "Mod Bit" and (mod_sq > 0 or (mod_eaves + mod_rakes) > 0)) or (material_type != "Mod Bit" and sq_count > 0)

if manifest_ready:
    st.table({"Material Item Description": descriptions, "Calculated Quantity": quantities})
else: 
    st.info("💡 Drop a takeoff report into the hub at the top of the page to populate the order manifests.")
