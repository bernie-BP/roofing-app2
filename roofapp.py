import streamlit as st
import math
import os
import re

# Safely import pypdf for local/production server use
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

st.set_page_config(page_title="Roofing Material Calculator", page_icon="🏠", layout="centered")

# Helper function to convert empty text strings safely to floats
def get_num(val):
    if not val or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).strip().replace(',', ''))
    except ValueError:
        return 0.0

# Safety Check: Only show the logo if the file actually exists
if os.path.exists("logo.png"):
    st.image("logo.png", width=200)

st.title("Roofing Material Ordering Dashboard")
st.write("Enter measurements manually or drop a Roofr report below to instantly generate distributor manifests.")

# ==========================================
# 📋 ROOFR PDF PARSER ENGINE
# ==========================================
scanned_vals = {"pitched_sq": "", "flat_sq": "", "eaves": "", "valleys": "", "hips": "", "ridges": "", "rakes": ""}

st.header("📋 Automated Roofr Report Import")
if not PYPDF_AVAILABLE:
    st.info("💡 *PDF Reader Mode is available when deployed live with a requirements file. Standard manual input is active below.*")
else:
    uploaded_file = st.file_uploader("Upload a Roofr PDF Measurement Report", type=["pdf"])
    
    if uploaded_file is not None:
        try:
            reader = pypdf.PdfReader(uploaded_file)
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

            # UPDATED: Target Roofr's specific split layout for Pitched vs Flat areas
            scanned_vals["pitched_sq"] = parse_metric(r"Pitched\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
            scanned_vals["flat_sq"] = parse_metric(r"Flat\s*Roof\s*Area\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
            
            # Fallback patterns if written as pure SQ units in report tables
            if not scanned_vals["pitched_sq"]:
                scanned_vals["pitched_sq"] = parse_metric(r"Pitched\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
            if not scanned_vals["flat_sq"]:
                scanned_vals["flat_sq"] = parse_metric(r"Flat\s*Area\s*[:\-]?\s*([\d\.,]+)\s*SQ", full_text)
            
            # Universal fallback if no breakdown is found
            if not scanned_vals["pitched_sq"] and not scanned_vals["flat_sq"]:
                universal_sq = parse_metric(r"(?:Total Area|Squares)\s*[:\-]?\s*([\d\.,]+)\s*sq", full_text)
                scanned_vals["pitched_sq"] = universal_sq
                scanned_vals["flat_sq"] = universal_sq

            # Standard perimeter lineals
            scanned_vals["eaves"] = parse_metric(r"Eaves\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["valleys"] = parse_metric(r"Valleys\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["hips"] = parse_metric(r"Hips\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["ridges"] = parse_metric(r"Ridges?\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            scanned_vals["rakes"] = parse_metric(r"Rakes\s*[:\-]?\s*([\d\.,]+)\s*f", full_text)
            
            st.success("✅ Roofr measurements scanned! Verify values in the tables below.")
        except Exception as e:
            st.error(f"Could not read PDF structure. Please check the file format. Error: {e}")

st.markdown("---")

# ── Material Type Selector ──────────────────────────────────────────────────
st.header("1. Job Measurements & Specifications")

material_type = st.radio(
    "Material Type",
    options=["Tile", "Shingles", "Mod Bit"],
    horizontal=True,
)

job_type = None
if material_type == "Tile":
    job_type = st.radio(
        "Job Type",
        options=["New Tile", "Re-Roof"],
        horizontal=True,
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MOD BIT SECTION
# ══════════════════════════════════════════════════════════════════════════════
if material_type == "Mod Bit":
    mb_col1, mb_col2 = st.columns(2)

    with mb_col1:
        # UPDATED: Uses Flat Roof Area
        mod_sq = get_num(st.text_input("Square Count (SQ)", value=scanned_vals["flat_sq"], help="Calculated using Flat Roof Area values from report"))
        mod_eaves = get_num(st.text_input("Eaves (Linear Feet)", value=scanned_vals["eaves"]))
        mod_rakes = get_num(st.text_input("Rakes (Linear Feet)", value=scanned_vals["rakes"]))

    with mb_col2:
        CAPSHEET_COLORS = [
            "Buff", "Grey Slate", "Black", "Heather Blend", 
            "Chestnut", "Oak", "White", "Red Blend", 
            "Pine Green", "Weatherwood"
        ]
        cap_color = st.selectbox("Cap Sheet Color", CAPSHEET_COLORS)
        
        mod_bit_base_type = st.selectbox(
            "Select Base Layer Material Type",
            options=["Base Sheet (2 SQ per roll)", "SAV 9\" Self-Adhered (66 LF per roll)"],
            help="Choose which product you are using for the base layer to calculate correct rolls."
        )

    st.markdown("---")

    # Mod Bit Math Calculations
    drip_edge_length = 10
    mb_drip_pieces  = (math.ceil(mod_eaves / drip_edge_length) if mod_eaves > 0 else 0) + 2
    cap_rolls       = math.ceil(mod_sq) if mod_sq > 0 else 0

    if mod_bit_base_type == "Base Sheet (2 SQ per roll)":
        base_rolls = math.ceil(mod_sq / 2) if mod_sq > 0 else 0
        base_description = "Polyglass Base Sheet"
        base_quantity_str = f"{base_rolls} Rolls  (covers {base_rolls * 2} SQ)"
    else:
        base_rolls = math.ceil((mod_eaves + mod_rakes) / 66) if (mod_eaves + mod_rakes) > 0 else 0
        base_description = 'Polyglass SAV 9" Self-Adhered (66 LF/roll)'
        base_quantity_str = f"{base_rolls} Rolls  ({mod_eaves + mod_rakes:.0f} LF @ 66 LF/roll)"

    st.header("2. Calculated Material Order")

    if mod_sq > 0 or (mod_eaves + mod_rakes) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Cap Sheet Rolls", f"{cap_rolls} Rolls", help="1 SQ per roll")
        c2.metric(f"{mod_bit_base_type.split(' (')[0]} Rolls", f"{base_rolls} Rolls")
        c3.metric("Drip Edge Pieces", f"{mb_drip_pieces} Pcs", help="10ft sections, eaves only")

        st.markdown("### 📋 Detailed Order Manifest")
        descriptions = [
            f"Polyglass Cap Sheet — {cap_color}",
            base_description,
            "Drip Edge (10ft sections, eaves only)",
        ]
        quantities = [
            f"{cap_rolls} Rolls  (covers {cap_rolls} SQ)",
            base_quantity_str,
            f"{mb_drip_pieces} Pieces  ({mb_drip_pieces * 10} LF)",
        ]
        st.table({"Material Description": descriptions, "Calculated Quantity": quantities})

        st.header("3. Actions")
        job_address = st.text_input("Job Address / Name", placeholder="e.g., Lot 42 - Whispering Pines")
        crew_notes = st.text_area("Crew / Field Notes", placeholder="e.g., flat deck, drain locations...", height=100)

        if st.button("Confirm & Ready to Order"):
            if job_address:
                st.success(f"📦 Order Manifest generated for **{job_address}**!")
            else:
                st.warning("Please enter a Job Address before confirming.")
    else:
        st.info("💡 Enter a Square Count or linear footage above to generate the material order manifest.")

# ══════════════════════════════════════════════════════════════════════════════
# TILE & SHINGLES SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
else:
    col1, col2 = st.columns(2)

    with col1:
        # UPDATED: Uses Pitched Roof Area
        sq_count = get_num(st.text_input("Square Count (SQ)", value=scanned_vals["pitched_sq"], help="Calculated using Pitched Roof Area values from report"))

        if material_type == "Tile":
            product = st.selectbox("Tile Type / Profile", [
                "Eagle (S-Profile)", "Eagle (W-Profile)", "Eagle (Flat)",
                "Westlake (S-Profile)", "Westlake (W-Profile)", "Westlake (Flat)"
            ])
        else:
            GAF_SHINGLES = {
                "GAF Timberline HDZ (Architectural)":                   3,
                "GAF Royal Sovereign (3-Tab)":                          3,
                "GAF Timberline UHDZ (Ultra High Definition)":          3,
                "GAF Timberline CS Cool Series (Architectural)":        3,
                "GAF Timberline American Harvest (Architectural)":      3,
                "GAF Timberline Natural Shadow (Architectural)":        3,
                "GAF Timberline AS II (Architectural)":                 3,
                "GAF Grand Canyon (Designer)":                          3,
                "GAF Slateline (Designer)":                             3,
                "GAF Woodland (Designer)":                              3,
                "GAF Grand Sequoia (Designer)":                         3,
                "GAF Camelot II (Designer)":                            4,
                "GAF Monaco (Designer)":                                4,
                "GAF Country Mansion (Designer)":                        4,
                "GAF Glenwood (Designer)":                              4,
            }
            product = st.selectbox("Shingle Type (GAF)", list(GAF_SHINGLES.keys()))
            bundles_per_sq = GAF_SHINGLES[product]
            st.caption(f"Coverage rate: **{bundles_per_sq} bundles per square**")

        eaves = get_num(st.text_input("Eaves (Linear Feet)", value=scanned_vals["eaves"]))
        valleys = get_num(st.text_input("Valleys (Linear Feet)", value=scanned_vals["valleys"]))

    with col2:
        hips = get_num(st.text_input("Hips (Linear Feet)", value=scanned_vals["hips"]))
        ridges = get_num(st.text_input("Ridges (Linear Feet)", value=scanned_vals["ridges"]))
        rakes = get_num(st.text_input("Rakes (Linear Feet)", value=scanned_vals["rakes"]))
        
        waste_pct = get_num(st.text_input("Waste Factor (%)", value="10"))

    st.markdown("---")
    st.subheader("Material Options")
    opt_col1, opt_col2 = st.columns(2)

    with opt_col1:
        underlayment_roll_size = st.selectbox(
            "Underlayment Roll Size",
            options=[2, 5, 10],
            index=0,
            format_func=lambda x: f"{x} SQ roll ({x * 100} sq ft)"
        )

    drip_edge_length = 10

    # Perimeter Formulas Logic
    WASTE_FACTOR = 1 + (waste_pct / 100)
    hip_ridge_lf = hips + ridges

    underlayment_rolls = math.ceil((sq_count * 1.15) / underlayment_roll_size)
    valley_sections = math.ceil(valleys / 10) if valleys > 0 else 0
    TILE_SQ_PER_PALLET = 2.97

    if material_type == "Tile":
        total_squares_with_waste = sq_count * WASTE_FACTOR
        if job_type == "Re-Roof":
            if sq_count < 20:
                pallets_needed = math.ceil(total_squares_with_waste / TILE_SQ_PER_PALLET) + 0.5
            else:
                pallets_needed = math.ceil(total_squares_with_waste / TILE_SQ_PER_PALLET) + 1
        else:
            pallets_needed = math.ceil(total_squares_with_waste / TILE_SQ_PER_PALLET)
        
        tile_drip_pieces = (math.ceil(eaves / drip_edge_length) if eaves > 0 else 0) + 2
        birdstop_pieces = (math.ceil(eaves / 10) if eaves > 0 else 0) + 2
        is_flat_tile = "Flat" in product
        batten_bundles = math.ceil(sq_count)
        
        if is_flat_tile:
            hip_bundles = 0
            ridge_bundles = math.ceil(hip_ridge_lf / 100) if hip_ridge_lf > 0 else 0
        else:
            hip_bundles = math.ceil(hips / 25) if hips > 0 else 0
            ridge_bundles = math.ceil(ridges / 50) if ridges > 0 else 0
    else:
        total_squares_with_waste = sq_count * WASTE_FACTOR
        shingle_drip_pieces = (math.ceil((eaves + rakes) / drip_edge_length) if (eaves + rakes) > 0 else 0) + 2
        field_bundles = math.ceil(total_squares_with_waste * bundles_per_sq)
        hip_ridge_bundles = math.ceil(hip_ridge_lf / 33) if hip_ridge_lf > 0 else 0
        starter_bundles = math.ceil(eaves / 100) if eaves > 0 else 0

    st.header("2. Calculated Material Order")

    if sq_count > 0:
        if material_type == "Tile":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(
