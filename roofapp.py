import streamlit as st
import math
import os

st.set_page_config(page_title="Roofing Material Calculator", page_icon="🏠", layout="centered")

# Helper function to convert empty text strings safely to floats
def get_num(val):
    if not val or val.strip() == "":
        return 0.0
    try:
        return float(val.strip())
    except ValueError:
        return 0.0

# Safety Check: Only show the logo if the file actually exists
if os.path.exists("logo.png"):
    st.image("logo.png", width=200)

st.title("Roofing Material Ordering Dashboard")
st.write("Enter the job measurements below to automatically calculate required materials.")

# ── Material Type ──────────────────────────────────────────────────────────────
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
# MOD BIT — separate input layout
# ══════════════════════════════════════════════════════════════════════════════
if material_type == "Mod Bit":
    mb_col1, mb_col2 = st.columns(2)

    with mb_col1:
        mod_sq = get_num(st.text_input("Square Count (SQ)", value="", help="1 SQ = 100 sq ft"))
        mod_eaves = get_num(st.text_input("Eaves (Linear Feet)", value=""))
        mod_rakes = get_num(st.text_input("Rakes (Linear Feet)", value=""))

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

    # ── Mod Bit Calculations ────────────────────────────────────────────────
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

    # ── Mod Bit Results ─────────────────────────────────────────────────────
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

        # ── Actions ────────────────────────────────────────────────────────
        st.header("3. Actions")
        job_address = st.text_input("Job Address / Name", placeholder="e.g., Lot 42 - Whispering Pines")
        crew_notes = st.text_area(
            "Crew / Field Notes",
            placeholder="e.g., flat deck, drain locations, existing cover count...",
            height=100,
        )

        if st.button("Confirm & Ready to Order"):
            if job_address:
                st.success(f"📦 Order Manifest generated for **{job_address}**! Copy the table above to send to your distributor.")
                if crew_notes.strip():
                    st.info(f"📝 **Field Notes:** {crew_notes.strip()}")
            else:
                st.warning("Please enter a Job Address before confirming.")
    else:
        st.info("💡 Enter a Square Count or linear footage above to generate the material order manifest.")

# ══════════════════════════════════════════════════════════════════════════════
# TILE & SHINGLES — Layout
# ══════════════════════════════════════════════════════════════════════════════
else:
    col1, col2 = st.columns(2)

    with col1:
        sq_count = get_num(st.text_input("Square Count (SQ)", value="", help="1 SQ = 100 sq ft"))

        if material_type == "Tile":
            product = st.selectbox("Tile Type / Profile", [
                "Eagle (S-Profile)",
                "Eagle (W-Profile)",
                "Eagle (Flat)",
                "Westlake (S-Profile)",
                "Westlake (W-Profile)",
                "Westlake (Flat)"
            ])
        else:
            GAF_SHINGLES = {
                "GAF Royal Sovereign (3-Tab)":                          3,
                "GAF Timberline HDZ (Architectural)":                   3,
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

        # 1. Eaves & 2. Valleys placed in Column 1
        eaves = get_num(st.text_input("Eaves (Linear Feet)", value=""))
        valleys = get_num(st.text_input("Valleys (Linear Feet)", value=""))

    with col2:
        # 3. Hips, 4. Ridges, & 5. Rakes placed in Column 2
        hips = get_num(st.text_input("Hips (Linear Feet)", value=""))
        ridges = get_num(st.text_input("Ridges (Linear Feet)", value=""))
        rakes = get_num(st.text_input("Rakes (Linear Feet)", value=""))
        
        waste_pct = get_num(st.text_input("Waste Factor (%)", value="10"))

    st.markdown("---")
    st.subheader("Material Options")

    opt_col1, opt_col2 = st.columns(2)

    with opt_col1:
        underlayment_roll_size = st.selectbox(
            "Underlayment Roll Size",
            options=[2, 5, 10],
            index=0,
            format_func=lambda x: f"{x} SQ roll ({x * 100} sq ft)",
            help="Select the roll size your supplier carries"
        )

    drip_edge_length = 10

    # ── Calculations ─────────────────────────────────────────────────────────
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

    # ── Results ───────────────────────────────────────────────────────────────
    st.header("2. Calculated Material Order")

    if sq_count > 0:
        if material_type == "Tile":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"Field SQ (+{waste_pct:.0f}% Waste)", f"{total_squares_with_waste:.1f} SQ")
            pallet_label = "Pallets Needed" + (" (Re-Roof)" if job_type == "Re-Roof" else "")
            c2.metric(pallet_label, f"{pallets_needed:g} Pallets")
            c3.metric("Underlayment Rolls", f"{underlayment_rolls} Rolls")
            if is_flat_tile:
                c4.metric("Hip/Ridge Closures", f"{ridge_bundles} Bundles")
            else:
                c4.metric("Hip / Ridge Closures", f"{hip_bundles} / {ridge_bundles} Bundles")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"Field SQ (+{waste_pct:.0f}% Waste)", f"{total_squares_with_waste:.1f} SQ")
            c2.metric("Field Bundles", f"{field_bundles} Bundles")
            c3.metric("Underlayment Rolls", f"{underlayment_rolls} Rolls")
            c4.metric("Hip/Ridge Cap Bundles", f"{hip_ridge_bundles} Bundles")

        st.markdown("### 📋 Detailed Order Manifest")

        if material_type == "Tile":
            if is_flat_tile:
                hip_ridge_desc = ["Hip & Ridge Closures (100 LF/bundle)"]
                hip_ridge_qty  = [f"{ridge_bundles} Bundles  ({hip_ridge_lf:.0f} LF @ 100 LF/bundle)"]
            else:
                hip_ridge_desc = ["Hip Closures (25 LF/bundle)", "Ridge Closures (50 LF/bundle)"]
                hip_ridge_qty = [
                    f"{hip_bundles} Bundles  ({hips:.0f} LF @ 25 LF/bundle)",
                    f"{ridge_bundles} Bundles  ({ridges:.0f} LF @ 50 LF/bundle)",
                ]

            # MODIFIED: Removed item #7 (Rake Trim / Gabled Edge Flashings)
            descriptions = [
                f"Field Tile: {product}",
                f"Tile Underlayment ({underlayment_roll_size}-SQ Rolls)",
                *hip_ridge_desc,
                "Roof Battens (1 bundle/SQ)",
                "Eave Closure / Birdstop (10ft pieces)",
                "Drip Edge (10ft sections, eaves only)",
            ]
            quantities = [
                f"{total_squares_with_waste:.1f} SQ  ({pallets_needed:g} pallets @ 2.97 SQ/pallet)",
                f"{underlayment_rolls} Rolls  (covers {underlayment_rolls * underlayment_roll_size} SQ)",
                *hip_ridge_qty,
                f"{batten_bundles} Bundles  ({sq_count:.0f} SQ)",
                f"{birdstop_pieces} Pieces  ({birdstop_pieces * 10} LF)",
                f"{tile_drip_pieces} Pieces  ({tile_drip_pieces * 10} LF)",
            ]
        else:
            descriptions = [
                f"Field Shingles: {product}",
                f"Underlayment ({underlayment_roll_size}-SQ Rolls)",
                "Hip & Ridge Cap Shingles",
                "Starter Strip Shingles",
                "Drip Edge (10ft sections)",
            ]
            quantities = [
                f"{total_squares_with_waste:.1f} SQ  ({field_bundles} bundles @ {bundles_per_sq}/SQ)",
                f"{underlayment_rolls} Rolls  (covers {underlayment_rolls * underlayment_roll_size} SQ)",
                f"{hip_ridge_bundles} Bundles  ({hip_ridge_bundles * 33} LF)",
                f"{starter_bundles} Bundles  ({starter_bundles * 100} LF)",
                f"{shingle_drip_pieces} Pieces  ({shingle_drip_pieces * 10} LF)",
            ]

        if valleys > 0:
            descriptions.append("Valley Flashing (W-Valley, 10ft sections)")
            quantities.append(f"{valley_sections} Sections  ({valley_sections * 10} LF)")

        st.table({"Material Description": descriptions, "Calculated Quantity": quantities})

        # ── Actions ──────────────────────────────────────────────────────────
        st.header("3. Actions")
        job_address = st.text_input("Job Address / Name", placeholder="e.g., Lot 42 - Whispering Pines")
        crew_notes = st.text_area(
            "Crew / Field Notes",
            placeholder="e.g., steep pitch on north slope, no dumpster access on weekends, match existing color...",
            height=100,
        )

        if st.button("Confirm & Ready to Order"):
            if job_address:
                st.success(f"📦 Order Manifest generated for **{job_address}**! Copy the table above to send to your distributor.")
                if crew_notes.strip():
                    st.info(f"📝 **Field Notes:** {crew_notes.strip()}")
            else:
                st.warning("Please enter a Job Address before confirming.")
    else:
        st.info("💡 Enter a Square Count above to generate the material order manifest.")
    
