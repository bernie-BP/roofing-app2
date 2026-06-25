import streamlit as st
import streamlit.components.v1 as components
import math
import os
import re
import base64
from io import BytesIO

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
st.write("Drop your job files below to scroll through your blueprints and pricing models seamlessly on the right panel.")

# ==========================================
# 📋 TWO-FILE UPLOADER HUB
# ==========================================
scanned_vals = {"pitched_sq": "", "flat_sq": "", "eaves": "", "valleys": "", "hips": "", "ridges": "", "rakes": ""}
roofr_pages_bytes = None
quote_pages_bytes = None

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
    
    # Process File 1: Roofr Takeoff Text Parsing
    if uploaded_roofr is not None:
        try:
            roofr_pages_bytes = uploaded_roofr.read()
            uploaded_roofr.seek(0)
            
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
            st.error(f"Could not parse Roofr blueprint text. Error: {e}")

    if uploaded_quote is not None:
        quote_pages_bytes = uploaded_quote.read()
        st.success("✅ Supplier material quote parsed successfully!")

st.markdown("---")

# ==========================================
# 🗺️ SPLIT DASHBOARD LAYOUT (LEFT/RIGHT)
# ==========================================
left_panel, right_panel = st.columns([1.0, 1.0], gap="large")

# 📥 LEFT PANEL: MATERIAL ENGINE CONFIGURATION
with left_panel:
    st.subheader("🛠️ Production Controls & Layout Settings")
    
    material_type = st.radio("Material Type", options=["Tile", "Shingles", "Mod Bit"], horizontal=True)
    job_type = st.radio("Job Type", options=["New Tile", "Re-Roof"], index=1, horizontal=True) if material_type == "Tile" else None
    
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

# 🖼️ RIGHT PANEL: SCROLL BOX IN A FIXED LOCATION (SAFE FROM BRAVE SHIELDS)
with right_panel:
    st.subheader("🖼️ Document Reference Panel")
    
    view_toggle = st.radio(
        "Display View Mode",
        options=["1. Roofr Measurement Blueprint", "2. Active Supplier Estimate"],
        horizontal=True
    )
    
    st.markdown("---")
    
    target_bytes = roofr_pages_bytes if "Roofr" in view_toggle else quote_pages_bytes
    label_tag = "Roofr Takeoff Blueprint" if "Roofr" in view_toggle else "Supplier Material Quote"
    
    if target_bytes is not None:
        try:
            with st.spinner("Compiling scroll viewport layout..."):
                all_images = convert_from_bytes(target_bytes)
                html_content = '<div style="height: 750px; overflow-y: scroll; border: 2px solid #4A5568; border-radius: 8px; padding: 10px; background-color: #1A202C;">'
                
                for i, page_img in enumerate(all_images):
                    buffered = BytesIO()
                    page_img.save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    html_content += f'<div style="text-align: center; margin-bottom: 20px;">'
                    html_content += f'<p style="color: #A0AEC0; font-family: sans-serif; font-size: 14px;">📄 {label_tag} — Page {i+1}</p>'
                    html_content += f'<img src="data:image/jpeg;base64,{img_base64}" style="width: 100%; max-width: 800px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">'
                    html_content += f'</div>'
                    
                html_content += '</div>'
                components.html(html_content, height=770, scrolling=False)
        except Exception as err:
            st.caption("Rendering continuous visual frame profile...")
    else:
        st.info(f"💡 Drop your PDF files into the uploader matrix above to lock and load the scrollable window for this document.")

# 📋 BOTTOM ROW: SYSTEM OUTPUT MANIFESTS
st.markdown("---")
st.header("2. Calculated Material Order")

manifest_ready = False
descriptions = []
quantities = []

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
    
    st.header("3. Operations Actions")
    
    act_col1, act_col2 = st.columns(2)
    with act_col1:
        job_address = st.text_input("Job Address / Name", placeholder="e.g., Lot 42 - Whispering Pines")
    with act_col2:
        crew_notes = st.text_input("Crew / Field Logistics Notes", placeholder="e.g., Dumpster in driveway, protect bushes on north slope...")
    
    # NEW FEATURE: Delivery Ticket HTML Generator Blueprint
    table_rows_html = ""
    for desc, qty in zip(descriptions, quantities):
        table_rows_html += f"<tr><td style='padding:10px; border-bottom:1px solid #ddd;'>{desc}</td><td style='padding:10px; border-bottom:1px solid #ddd; text-align:right; font-weight:bold;'>{qty}</td></tr>"

    html_ticket_template = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 40px; color: #333;">
        <div style="border: 2px solid #333; padding: 20px; border-radius: 8px;">
            <h2 style="text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">Roofing Material Delivery Ticket</h2>
            <p style="text-align: center; color: #666; margin-top: 0; font-size: 13px;">Production manifest generated via Calculator Dashboard</p>
            <hr style="border: 1px solid #333; margin-bottom: 20px;">
            
            <table style="width: 100%; margin-bottom: 20px; font-size: 14px;">
                <tr><td><strong>Job Location:</strong> {job_address if job_address else 'Not Specified'}</td></tr>
                <tr><td><strong>Material Category:</strong> {material_type} {'('+job_type+')' if job_type else ''}</td></tr>
                <tr><td><strong>Logistics/Crew Notes:</strong> {crew_notes if crew_notes else 'None listed.'}</td></tr>
            </table>
            
            <h3 style="background: #f4f4f4; padding: 8px; margin-bottom: 10px; font-size: 15px;">📦 Loaded Material Checklist</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #e2e2e2;"><th style="padding:10px; text-align:left;">Material Description</th><th style="padding:10px; text-align:right;">Quantity Loaded</th></tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
            
            <div style="margin-top: 50px; font-size: 12px; display: flex; justify-content: space-between;">
                <div><p>_____________________________________<br>Driver Loading Verification Signature</p></div>
                <div style="text-align: right;"><p>_____________________________________<br>Field Superintendent Receiving Signature</p></div>
            </div>
        </div>
        <script>window.print();</script>
    </body>
    </html>
    """

    # Create a simple direct printing function using standard web frames
    st.markdown("### 🖨️ Document Export Center")
    if job_address:
        st.download_button(
            label="Download Delivery Ticket Printout File",
            data=html_ticket_template,
            file_name=f"Delivery_Ticket_{job_address.replace(' ', '_')}.html",
            mime="text/html",
            help="Downloads a print-ready document file. Opening this file will instantly open your computer's standard print menu to print or save as a clean PDF document."
        )
    else:
        st.caption("⚠️ *Type a Job Address / Name above to unlock the printable Delivery Ticket file generator.*")
        
else:
    st.info("💡 Upload data files or enter sizing values to populate the order manifests.")
