import streamlit as st
import math
import os
import re

# Handle backend PDF graphic engines natively
try:
    import pypdf
    from pdf2image import convert_from_bytes
    PDF_ENGINES_AVAILABLE = True
except ImportError:
    PDF_ENGINES_AVAILABLE = False

# Wide layout configuration to give ample space for the split panel view
st.set_page_config(page_title="Roofing Material Calculator", page_icon="🏠", layout="wide")

def get_num(val):
    if not val or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).strip().replace(',', ''))
    except ValueError:
        return 0.0

if os.path.exists("logo.png"):
    st.image("logo.png", width=200)

st.title("Roofing Material Ordering Dashboard")
st.write("Drop your job files below to view blueprints and pricing models on the right while managing parameters on the left.")

# ==========================================
# 📋 TWO-FILE UPLOADER HUB
# ==========================================
scanned_vals = {"pitched_sq": "", "flat_sq": "", "eaves": "", "valleys": "", "hips": "", "ridges": "", "rakes": ""}
roofr_pages_bytes = None
quote_pages_bytes = None
total_roofr_pages = 1
total_quote_pages = 1

st.header("📋 Automated Document Upload Hub")
if not PDF_ENGINES_AVAILABLE:
    st.info("💡 *PDF Processing Modules are active when deployed live with pypdf and pdf2image requirements.*")
else:
    # Twin File Upload Row
    up_col1, up_col2 = st.columns(2)
    
    with up_col1:
        uploaded_roofr = st.file_uploader("1. Upload Roofr Measurement Report (PDF)", type=["pdf"])
    with up_col2:
        uploaded_quote = st.file_uploader("2. Upload Estimate / Supplier Quote (PDF)", type=["pdf"])
    
    # Process File 1: Roofr Takeoff Text Parsing & Sizing Check
    if uploaded_roofr is not None:
        try:
            roofr_pages_bytes = uploaded_roofr.read()
            uploaded_roofr.seek(0)
            
            reader = pypdf.PdfReader(uploaded_roofr)
            total_roofr_pages = len(reader.pages)
            
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
            st.error(f"Could not parse Roofr blueprint text. Error: {e}")

    # Process File 2: Total Page Count Check on Supplier Quote
    if uploaded_quote is not None:
        try:
            quote_pages_bytes = uploaded_quote.read()
            uploaded_quote.seek(0)
            reader_quote = pypdf.PdfReader(uploaded_quote)
            total_quote_pages = len(reader_quote.pages)
            st.success("✅ Supplier material quote ready for visualization panels!")
        except Exception as e:
            st.error(f"Could not read estimate page indexing. Error: {e}")

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
            ridges = get_num(st.text_input("Ridges (Linear Feet)", value=scanned_vals["ridges"]))
            rakes = get_num(st.text_input("Rakes (Linear Feet)", value=scanned_vals["rakes"]))
            waste_pct = get_num(st.text_input("Waste Factor (%)", value="10"))

        underlayment_roll_size = st.selectbox("Underlayment Roll Size", options=[2, 5, 10], format_func=lambda x: f"{x} SQ roll")
        drip_edge_length = 10
        WASTE_FACTOR = 1 + (waste_pct / 100)
        hip_ridge_lf = hips + ridges
        underlayment_rolls = math.ceil((sq_count * 1.15) / underlayment_roll_size)
        valley_sections = math.ceil(valleys / 10) if valleys > 0 else 0
        
        if material_type == "Tile":
            total_squares_with_waste = sq_count * WASTE_FACTOR
            if job_type == "Re-Roof":
                pallets_needed = 0.5 if sq_count < 20 else math.ceil((sq_count / 20) * 2) / 2
            else:
                pallets_needed = math.ceil(total_squares_with_waste / 2.97)
            tile_drip_pieces = (math.ceil(eaves / drip_edge_length) if eaves > 0 else 0) + 2
            birdstop_pieces = (math.ceil(eaves / 10) if eaves > 0 else 0) + 2
            is_flat_tile = "Flat" in product
            batten_bundles = math.ceil(sq_count)
            hip_bundles = 0 if is_flat_tile else math.ceil(hips / 25)
            ridge_bundles = math.ceil(hip_ridge_lf / 100) if is_flat_tile else math.ceil(ridges / 50)
        else:
            total_squares_with_waste = sq_count * WASTE_FACTOR
            shingle_drip_pieces = (math.ceil((eaves + rakes) / drip_edge_length) if (eaves + rakes) > 0 else 0) + 2
            field_bundles = math.ceil(total_squares_with_waste * 3)
            hip_ridge_bundles = math.ceil(hip_ridge_lf / 33) if hip_ridge_lf > 0 else 0
            starter_bundles = math.ceil(eaves / 100) if eaves > 0 else 0
            field_nail_boxes = math.ceil(sq_count / 20) if sq_count > 0 else 0
            eave_nail_boxes  = math.ceil(sq_count / 20) if sq_count > 0 else 0
            cap_nail_boxes   = math.ceil(sq_count / 20) if sq_count > 0 else 0

# 🖼️ RIGHT PANEL: BROWSER-SAFE IMAGE RENDER CORES
with right_panel:
    st.subheader("🖼️ Job File Document Matrix")
    
    doc_view_col1, doc_view_col2 = st.columns(2)
    
    with doc_view_col1:
        st.markdown("**1. Roofr Schematic Map**")
        if roofr_pages_bytes is not None:
            # Brave-safe page selector
            roofr_page_selection = st.selectbox(
                "Go to Page",
                options=list(range(1, total_roofr_pages + 1)),
                format_func=lambda x: f"Page {x} of {total_roofr_pages}",
                key="roofr_page_selector"
            )
            try:
                images_roofr = convert_from_bytes(roofr_pages_bytes, first_page=roofr_page_selection, last_page=roofr_page_selection)
                if images_roofr:
                    st.image(images_roofr[0], use_column_width=True)
            except Exception as img_err:
                st.caption("Rendering document view...")
        else:
            st.caption("Waiting for Roofr Takeoff Report...")
            
    with doc_view_col2:
        st.markdown("**2. Active Supplier Estimate**")
        if quote_pages_bytes is not None:
            # Brave-safe page selector
            quote_page_selection = st.selectbox(
                "Go to Page",
                options=list(range(1, total_quote_pages + 1)),
                format_func=lambda x: f"Page {x} of {total_quote_pages}",
                key="quote_page_selector"
            )
            try:
                images_quote = convert_from_bytes(quote_pages_bytes, first_page=quote_page_selection, last_page=quote_page_selection)
                if images_quote:
                    st.image(images_quote[0], use_column_width=True)
            except Exception as img_err:
                st.caption("Rendering document view...")
        else:
            st.caption("Waiting for Distributor Quote file...")

# 📋 BOTTOM ROW: SYSTEM OUTPUT MANIFESTS
st.markdown("---")
st.header("2. Calculated Material Order")

manifest_ready = False
if material_type == "Mod Bit" and (mod_sq > 0 or (mod_eaves + mod_rakes) > 0):
    manifest_ready = True
    c1, c2, c3 = st.columns(3)
    c1.metric("Cap Sheet Rolls", f"{cap_rolls} Rolls")
    c2.metric(f"{mod_bit_base_type.split(' (')[0]} Rolls", f"{base_rolls} Rolls")
    c3.metric("Drip Edge Pieces", f"{mb_drip_pieces} Pcs")
    
    descriptions = [f"Polyglass Cap Sheet — {cap_color}", base_description, "Drip Edge (10ft sections, eaves only)"]
    quantities = [f"{cap_rolls} Rolls (covers {cap_rolls} SQ)", base_quantity_str, f"{mb_drip_pieces} Pieces ({mb_drip_pieces * 10} LF)"]

elif material_type != "Mod Bit" and sq_count > 0:
    manifest_ready = True
    if material_type == "Tile":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Field SQ (+{waste_pct:.0f}% Waste)", f"{total_squares_with_waste:.1f} SQ")
        c2.metric("Pallets Needed", f"{pallets_needed:g} Pallets")
        c3.metric("Underlayment Rolls", f"{underlayment_rolls} Rolls")
        c4.metric("Hip/Ridge Closures", f"{ridge_bundles} Bundles" if is_flat_tile else f"{hip_bundles} / {ridge_bundles} Bundles")
        
        hip_ridge_desc = ["Hip & Ridge Closures (100 LF/bundle)"] if is_flat_tile else ["Hip Closures (25 LF/bundle)", "Ridge Closures (50 LF/bundle)"]
        hip_ridge_qty = [f"{ridge_bundles} Bundles"] if is_flat_tile else [f"{hip_bundles} Bundles", f"{ridge_bundles} Bundles"]
        descriptions = [f"Field Tile: {product}", f"Tile Underlayment ({underlayment_roll_size}-SQ Rolls)", *hip_ridge_desc, "Roof Battens", "Eave Closure / Birdstop", "Drip Edge (eaves only)"]
        quantities = [f"{pallets_needed:g} Pallets (Breakage)" if job_type == "Re-Roof" else f"{total_squares_with_waste:.1f} SQ ({pallets_needed:g} Pallets)", f"{underlayment_rolls} Rolls", *hip_ridge_qty, f"{batten_bundles} Bundles", f"{birdstop_pieces} Pcs", f"{tile_drip_pieces} Pcs"]
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Field SQ (+{waste_pct:.0f}% Waste)", f"{total_squares_with_waste:.1f} SQ")
        c2.metric("Field Bundles", f"{field_bundles} Bundles")
        c3.metric("Underlayment Rolls", f"{underlayment_rolls} Rolls")
        c4.metric("Hip/Ridge Cap Bundles", f"{hip_ridge_bundles} Bundles")
        
        descriptions = [f"Field Shingles: {product}", f"Underlayment ({underlayment_roll_size}-SQ Rolls)", "Hip & Ridge Cap", "Starter Strip", "Drip Edge", "Shingle Field Nails", "Eave Coil Nails", "Plastic Cap Nails"]
        quantities = [f"{field_bundles} Bundles", f"{underlayment_rolls} Rolls", f"{hip_ridge_bundles} Bundles", f"{starter_bundles} Bundles", f"{shingle_drip_pieces} Pcs", f"{field_nail_boxes} Box(es) (Net SQ)", f"{eave_nail_boxes} Box(es) (Net SQ)", f"{cap_nail_boxes} Box(es) (Net SQ)"]

if manifest_ready:
    if material_type != "Mod Bit" and valleys > 0:
        descriptions.append("Valley Flashing (W-Valley)")
        quantities.append(f"{valley_sections} Sections")
        
    st.table({"Material Description": descriptions, "Calculated Quantity": quantities})
    
    st.header("3. Actions")
    job_address = st.text_input("Job Address / Name", placeholder="e.g., Lot 42 - Whispering Pines")
    if st.button("Confirm & Ready to Order") and job_address:
        st.success(f"📦 Order Manifest generated for **{job_address}**!")
