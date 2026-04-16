"""
AVL-DRIVE Heatmap Tool - Python Version
A Streamlit web application that replicates the Excel-based AVL-DRIVE Heatmap Tool.

Usage:
    streamlit run app.py
"""

import html as _html
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image as _PILImage
import streamlit as st

from config import (
    STATUS_COLORS,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_YELLOW_BRIGHT,
    COLOR_RED,
    COLOR_HEATMAP_HEADER,
    COLOR_HEATMAP_BORDER,
    COLOR_SHEET1_HEADER,
    COLOR_SHEET1_SECTION_BG,
    COLOR_SHEET1_DOT_BG,
    COLOR_BLACK,
    COLOR_WHITE,
    OPERATION_MODE_MAPPING,
    AVL_ODRIV_MAPPING,
    PARENT_OPERATION_CODES,
    SCORE_SCALE_MIN,
    SCORE_SCALE_MID,
    SCORE_SCALE_MAX,
    SCORE_COLOR_MIN,
    SCORE_COLOR_MID,
    SCORE_COLOR_MAX,
)
from heatmap_engine import (
    build_heatmap_template,
    parse_heatmap_data,
    refresh_heatmap,
    filter_heatmap_rows,
)
from evaluation_engine import (
    parse_sheet1_data,
    parse_sheet1_from_excel,
    parse_odriv_from_excel,
    parse_odriv_detail_sheets,
    evaluate_avl_status,
    build_overall_status,
    update_sub_operation_heatmap,
    calculate_group_status,
    generate_red_comments,
)

# ============================================================================
# Page Configuration
# ============================================================================
st.set_page_config(
    page_title="AVL-DRIVE Heatmap Tool",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    st.title("🚗 AVL-DRIVE Heatmap Tool")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        [
            "📋 AVL Data Input",
            "📊 Odriv Data Input",
            "🔥 HeatMap",
            "📈 Run Evaluation And Result",
            "📖 Help & Reference",
        ],
    )

    if page == "📋 AVL Data Input":
        heatmap_input_page()
    elif page == "📊 Odriv Data Input":
        sheet1_input_page()
    elif page == "🔥 HeatMap":
        heatmap_view_page()
    elif page == "📈 Run Evaluation And Result":
        evaluation_results_page()
    elif page == "📖 Help & Reference":
        help_page()


# ============================================================================
# Page: AVL Data Input
# ============================================================================
def heatmap_input_page():
    st.header("📋 AVL Data Input")
    st.markdown("""
    Paste your **Data Transfer Sheet** data here. This is the data with AVL-DRIVE
    ratings for each vehicle and operation mode.

    **Expected format** (tab-separated):
    ```
    Operation Modes    Vehicle1_Name    Vehicle2_Name
    Operation Modes    DR               DR
    10000000    AVL-DRIVE Rating    8.3    8.2
    10100000    Drive away          7.9    7.4
    10101300    Creep               7.2    6.9
    ...
    ```

    You can also upload an Excel file or CSV with this data.
    """)

    input_method = st.radio("Input method:", ["Paste Text", "Upload File"], key="hm_input_method")

    if input_method == "Paste Text":
        heatmap_text = st.text_area(
            "Paste HeatMap / Data Transfer Sheet data (tab-separated):",
            height=400,
            placeholder="Paste tab-separated data here...\n\n"
                        "Example:\n"
                        "\tOperation Modes\tBYD Atto 3 BEV_NORMAL\tBYD_Dolphin Surf_BEV_NORMAL\n"
                        "\tOperation Modes\tDR\tDR\n"
                        "10000000\tAVL-DRIVE Rating\t8.3\t8.2\n"
                        "10100000\tDrive away\t7.9\t7.4",
            key="heatmap_text_input",
        )

        if st.button("🔄 Process HeatMap Data", key="process_heatmap"):
            if heatmap_text.strip():
                parsed = parse_heatmap_data(heatmap_text)
                if parsed:
                    template = build_heatmap_template()
                    heatmap_df = refresh_heatmap(template, parsed)
                    st.session_state["heatmap_data"] = heatmap_df
                    st.session_state["vehicle_names"] = parsed["vehicle_names"]
                    st.success(f"✅ Loaded {len(parsed['vehicle_names'])} vehicle(s): "
                             f"{', '.join(parsed['vehicle_names'])}")
                else:
                    st.error("❌ Could not parse the data. Please check the format.")
            else:
                st.warning("⚠️ Please paste data first.")

    else:
        uploaded_file = st.file_uploader(
            "Upload Excel (.xlsx/.xlsm) or CSV file:",
            type=["xlsx", "xlsm", "csv"],
            key="heatmap_file",
        )

        if uploaded_file:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                # For Excel files, let user select sheet
                xls = pd.ExcelFile(uploaded_file)
                sheet_name = st.selectbox("Select sheet:", xls.sheet_names)
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

            st.dataframe(df, use_container_width=True)

            if st.button("🔄 Process Uploaded Data", key="process_uploaded_heatmap"):
                # Convert dataframe to tab-separated text and re-parse
                text = df.to_csv(sep="\t", index=False)
                parsed = parse_heatmap_data(text)
                if parsed:
                    template = build_heatmap_template()
                    heatmap_df = refresh_heatmap(template, parsed)
                    st.session_state["heatmap_data"] = heatmap_df
                    st.session_state["vehicle_names"] = parsed["vehicle_names"]
                    st.success(f"✅ Loaded {len(parsed['vehicle_names'])} vehicle(s)")
                else:
                    st.error("❌ Could not parse the uploaded data.")

    # Show current heatmap data if available
    if "heatmap_data" in st.session_state:
        st.subheader("Current HeatMap Data")
        st.dataframe(st.session_state["heatmap_data"], use_container_width=True)


# ============================================================================
# Page: Odriv Data Input
# ============================================================================
def sheet1_input_page():
    st.header("📊 Odriv Data Input (Drivability / Responsiveness)")
    st.markdown("""
    Load your **Sheet1** data containing the Drivability and Responsiveness
    evaluation data with colored dot statuses.

    **Recommended:** Upload the Excel file directly so dot colors (green / yellow / red)
    are read automatically.  You can upload either:
    - The **AVL-DRIVE Heatmap Tool** Excel (reads from the *Sheet1* tab), or
    - An **AVL-ODRIV** Excel file (reads from the *RATING* tab).

    If pasting as text, encode dot colors as **G**, **Y**, **R**,
    or leave blank for N/A.
    """)

    input_method = st.radio(
        "Input method:",
        ["Upload Excel File (recommended)", "Paste Text"],
        key="sheet1_input_method",
    )

    if input_method == "Upload Excel File (recommended)":
        uploaded_file = st.file_uploader(
            "Upload an AVL-DRIVE Heatmap Tool or ODRIV Excel file (.xlsx / .xlsm):",
            type=["xlsx", "xlsm"],
            key="sheet1_file",
        )

        if uploaded_file and st.button("🔄 Process Excel File", key="process_sheet1_excel"):
            with st.spinner("Reading Excel file and extracting dot colors..."):
                # Try Sheet1 first, then fall back to ODRIV RATING sheet
                parsed = parse_sheet1_from_excel(uploaded_file)
                source_label = "Sheet1"
                if parsed is None:
                    uploaded_file.seek(0)
                    parsed = parse_odriv_from_excel(uploaded_file)
                    source_label = "RATING"

                # Also parse operation-detail sub-sheets for auto-comment generation.
                detail_msg = ""
                uploaded_file.seek(0)
                odriv_details = parse_odriv_detail_sheets(uploaded_file)
                if odriv_details:
                    st.session_state["odriv_details"] = odriv_details
                    detail_msg = (
                        f"  \n📝 Parsed **{len(odriv_details)}** detail sheet(s) "
                        f"for auto-comment generation."
                    )

            if parsed:
                st.session_state["sheet1_data"] = parsed
                st.success(
                    f"✅ Loaded {len(parsed['operations'])} operations in "
                    f"{len(parsed['sections'])} sections "
                    f"(from **{source_label}** sheet).\n\n"
                    f"**Target:** {parsed['target_car']}  |  "
                    f"**Tested:** {parsed['tested_car']}"
                    f"{detail_msg}"
                )
            else:
                st.error(
                    "❌ Could not parse the file. Make sure it contains either a "
                    "**Sheet1** tab (Heatmap Tool) or a **RATING** tab (ODRIV) "
                    "with the expected layout."
                )

    else:
        st.markdown("""
        **Since colors can't be pasted as text**, encode dot colors as:
        - **G** = Green ●  &nbsp; **Y** = Yellow ●  &nbsp; **R** = Red ●
        - Leave **blank** = White/No data (N/A)
        """)

        sheet1_text = st.text_area(
            "Paste Sheet1 data (tab-separated):",
            height=400,
            placeholder="Paste tab-separated data here...",
            key="sheet1_text_input",
        )

        col1, col2 = st.columns(2)
        with col1:
            target_car_override = st.text_input(
                "Target Vehicle Name (optional override):",
                key="target_car_name",
                help="If not auto-detected from pasted data, enter the target vehicle name here.",
            )
        with col2:
            tested_car_override = st.text_input(
                "Tested Vehicle Name (optional override):",
                key="tested_car_name",
                help="If not auto-detected from pasted data, enter the tested vehicle name here.",
            )

        if st.button("🔄 Process Sheet1 Data", key="process_sheet1"):
            if sheet1_text.strip():
                parsed = parse_sheet1_data(sheet1_text)
                if parsed:
                    if target_car_override:
                        parsed["target_car"] = target_car_override
                    if tested_car_override:
                        parsed["tested_car"] = tested_car_override

                    st.session_state["sheet1_data"] = parsed
                    st.success(
                        f"✅ Loaded {len(parsed['operations'])} operations in "
                        f"{len(parsed['sections'])} sections.\n\n"
                        f"**Target:** {parsed['target_car']}  |  "
                        f"**Tested:** {parsed['tested_car']}"
                    )
                else:
                    st.error("❌ Could not parse the data. Please check the format.")
            else:
                st.warning("⚠️ Please paste data first.")

    # Show parsed data with colored dots if available
    if "sheet1_data" in st.session_state:
        data = st.session_state["sheet1_data"]
        st.subheader("Parsed Operations")

        ops = data["operations"]
        if ops:
            html = _build_sheet1_html(ops, data.get("sections", []),
                                      data["tested_car"], data["target_car"])
            st.markdown(html, unsafe_allow_html=True)

        if data["sections"]:
            st.subheader("Sections")
            sections_df = pd.DataFrame(data["sections"])
            st.dataframe(sections_df, use_container_width=True)


# ============================================================================
# Page: HeatMap
# ============================================================================
def heatmap_view_page():
    st.header("🔥 HeatMap")

    if "heatmap_data" not in st.session_state:
        st.info("ℹ️ No heatmap data loaded. Go to **AVL Data Input** to load data.")
        return

    heatmap_df = st.session_state["heatmap_data"]
    vehicle_names = st.session_state.get("vehicle_names", [])

    # Options
    col1, col2, col3 = st.columns(3)
    with col1:
        if vehicle_names:
            target_vehicle = st.selectbox("Target Vehicle:", vehicle_names, index=0)
        else:
            target_vehicle = None
    with col2:
        if len(vehicle_names) > 1:
            tested_vehicle = st.selectbox(
                "Tested Vehicle:",
                vehicle_names,
                index=len(vehicle_names) - 1,
            )
        elif vehicle_names:
            tested_vehicle = vehicle_names[0]
        else:
            tested_vehicle = None
    with col3:
        hide_empty = st.checkbox("Hide rows without tested vehicle data", value=True)

    # Apply filtering
    display_df = heatmap_df.copy()
    if hide_empty and tested_vehicle:
        display_df = filter_heatmap_rows(display_df, tested_vehicle)

    # Add status column if evaluation results exist
    if "eval_results" in st.session_state and not st.session_state["eval_results"].empty:
        display_df = update_sub_operation_heatmap(display_df, st.session_state["eval_results"])

    # Auto-generate comments for RED status sub-operations.
    if (
        "odriv_details" in st.session_state
        and "sheet1_data" in st.session_state
        and "Status" in display_df.columns
    ):
        red_comments = generate_red_comments(
            st.session_state["sheet1_data"],
            display_df,
            st.session_state["odriv_details"],
        )
        if red_comments:
            display_df["Comments"] = display_df["Op Code"].map(
                lambda x: red_comments.get(x, "")
            )

    # Build the target vehicle label for the header
    target_label = target_vehicle or "Target Vehicle"

    # Render the Excel-style HTML heatmap
    html = _build_heatmap_html(display_df, vehicle_names, target_label)
    st.markdown(html, unsafe_allow_html=True)

    # Export
    st.subheader("Export")
    col1, col2, col3 = st.columns(3)
    with col1:
        csv = display_df.to_csv(index=False)
        st.download_button(
            "📥 Download HeatMap as CSV",
            csv,
            "heatmap_results.csv",
            "text/csv",
        )
    with col2:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            display_df.to_excel(writer, sheet_name="HeatMap", index=False)
        st.download_button(
            "📥 Download HeatMap as Excel",
            excel_buffer.getvalue(),
            "heatmap_results.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col3:
        # Let the user choose where to split the table for JPG export.
        # Build a list of Operation Mode names so the user can pick the
        # first row of Part 2 (the header is repeated automatically).
        op_mode_names = display_df["Operation Mode"].astype(str).tolist()
        split_options = ["No split (single image)"] + [
            f"After row {i + 1}: {name}" for i, name in enumerate(op_mode_names)
            if i < len(op_mode_names) - 1  # splitting after the last row is pointless
        ]
        split_choice = st.selectbox(
            "Split JPG at:", split_options, index=0,
            help="For large tables, choose a row to split the image into two parts. "
                 "The header will be repeated in the second part.",
        )

    # Generate the JPG image(s) server-side with matplotlib (instant, no
    # html2canvas).  Render once and offer download buttons.
    jpg_buf = _render_heatmap_image(display_df, vehicle_names, target_label)

    if split_choice == "No split (single image)":
        st.download_button(
            "📸 Download HeatMap as JPG",
            jpg_buf.getvalue(),
            "heatmap.jpg",
            "image/jpeg",
        )
    else:
        # Split: crop the full image into two parts using Pillow
        split_at = int(split_choice.split(":")[0].replace("After row ", ""))
        full_img = _PILImage.open(jpg_buf)
        w, h = full_img.size

        # 3 header rows + split_at data rows  →  pixel boundary
        n_total_rows = 3 + len(display_df)
        header_pixel_h = int(h * 3 / n_total_rows)
        split_pixel_y = int(h * (3 + split_at) / n_total_rows)

        # Part 1: top → split row
        part1 = full_img.crop((0, 0, w, split_pixel_y))
        buf1 = io.BytesIO()
        part1.save(buf1, format="JPEG", quality=95)
        buf1.seek(0)

        # Part 2: header (repeated) + remaining rows
        header_strip = full_img.crop((0, 0, w, header_pixel_h))
        remaining = full_img.crop((0, split_pixel_y, w, h))
        part2 = _PILImage.new("RGB", (w, header_pixel_h + remaining.size[1]), (255, 255, 255))
        part2.paste(header_strip, (0, 0))
        part2.paste(remaining, (0, header_pixel_h))
        buf2 = io.BytesIO()
        part2.save(buf2, format="JPEG", quality=95)
        buf2.seek(0)

        p1col, p2col = st.columns(2)
        with p1col:
            st.download_button(
                "📸 Download Part 1",
                buf1.getvalue(),
                "heatmap_part1.jpg",
                "image/jpeg",
            )
        with p2col:
            st.download_button(
                "📸 Download Part 2",
                buf2.getvalue(),
                "heatmap_part2.jpg",
                "image/jpeg",
            )


# ============================================================================
# Page: Run Evaluation And Result
# ============================================================================
def evaluation_results_page():
    st.header("📈 Run Evaluation And Result")

    if "sheet1_data" not in st.session_state:
        st.info("ℹ️ No Odriv data loaded. Go to **Odriv Data Input** to load data.")
        return

    sheet1_data = st.session_state["sheet1_data"]
    heatmap_df = st.session_state.get("heatmap_data", pd.DataFrame())

    # Car selection
    st.subheader("Vehicle Selection")
    col1, col2 = st.columns(2)
    with col1:
        target_car = st.text_input(
            "Target Vehicle:",
            value=sheet1_data.get("target_car", "Target Vehicle"),
            key="eval_target_car",
        )
    with col2:
        tested_car = st.text_input(
            "Tested Vehicle:",
            value=sheet1_data.get("tested_car", "Tested Vehicle"),
            key="eval_tested_car",
        )

    if st.button("🔄 Run Evaluation", type="primary", key="run_eval"):
        with st.spinner("Running evaluation..."):
            eval_results = evaluate_avl_status(sheet1_data, heatmap_df, target_car, tested_car)
            st.session_state["eval_results"] = eval_results
            st.session_state["eval_target_car_name"] = target_car
            st.session_state["eval_tested_car_name"] = tested_car
            st.success(f"✅ Evaluation complete! {len(eval_results)} operations evaluated.")

    # Display results
    if "eval_results" in st.session_state and not st.session_state["eval_results"].empty:
        eval_results = st.session_state["eval_results"]
        target_car = st.session_state.get("eval_target_car_name", "Target")
        tested_car = st.session_state.get("eval_tested_car_name", "Tested")

        # Detailed Results
        st.subheader("Detailed Results")
        styled_eval = _style_evaluation_results(eval_results)
        st.dataframe(styled_eval, use_container_width=True, height=500)

        # Overall Status Summary
        st.subheader("Overall Status by Op Code")
        overall_df = build_overall_status(eval_results)
        if not overall_df.empty:
            styled_overall = _style_overall_status(overall_df)
            st.dataframe(styled_overall, use_container_width=True)

        # Status Distribution
        st.subheader("Status Distribution")
        _show_status_distribution(eval_results)

        # Group Status
        if "sheet1_data" in st.session_state:
            st.subheader("Operation Mode Group Status")
            _show_group_status(st.session_state["sheet1_data"])

        # Export
        st.subheader("Export")
        col1, col2 = st.columns(2)
        with col1:
            csv = eval_results.to_csv(index=False)
            st.download_button(
                "📥 Download Results as CSV",
                csv,
                "evaluation_results.csv",
                "text/csv",
            )
        with col2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                eval_results.to_excel(writer, sheet_name="Evaluation Results", index=False)
                if not overall_df.empty:
                    overall_df.to_excel(writer, sheet_name="Overall Status", index=False)
            st.download_button(
                "📥 Download Results as Excel",
                excel_buffer.getvalue(),
                "evaluation_results.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ============================================================================
# Page: Help & Reference
# ============================================================================
def help_page():
    st.header("📖 Help & Reference")

    with st.expander("🔢 Operation Mode Codes", expanded=False):
        st.markdown("Reference table of all operation mode codes and their names:")
        ref_data = [{"Code": k, "Operation Mode": v} for k, v in OPERATION_MODE_MAPPING.items()]
        st.dataframe(pd.DataFrame(ref_data), use_container_width=True)

    with st.expander("🔗 AVL-ODRIV Name Mapping", expanded=False):
        st.markdown("Maps detailed operation names to standard operation codes:")
        map_data = [{"Name": k, "Op Code": v} for k, v in AVL_ODRIV_MAPPING.items()]
        st.dataframe(pd.DataFrame(map_data), use_container_width=True)

    with st.expander("📊 Evaluation Rules", expanded=True):
        st.markdown("""
        ### Status Evaluation Rules

        For each operation, the tool evaluates **Drivability** and **Responsiveness**
        independently, then combines them into a **Final Status**.

        #### Individual Status (Drivability or Responsiveness):
        | Condition | Status |
        |-----------|--------|
        | P1 = N/A (white dot or no dot) | **N/A** |
        | AVL Score < 7.0 OR P1 = RED | **RED** 🔴 |
        | AVL Score ≥ 7.0 AND P1 = YELLOW | **YELLOW** 🟡 |
        | AVL Score ≥ 7.0 AND P1 = GREEN AND no benchmark | **GREEN** 🟢 |
        | AVL Score ≥ 7.0 AND P1 = GREEN AND tested ≥ target | **GREEN** 🟢 |
        | AVL Score ≥ 7.0 AND P1 = GREEN AND (target - tested) ≤ 2 | **GREEN** 🟢 |
        | AVL Score ≥ 7.0 AND P1 = GREEN AND (target - tested) > 2 | **YELLOW** 🟡 |

        #### Final Status (Combined):
        | Condition | Final Status |
        |-----------|-------------|
        | Either RED | **RED** 🔴 |
        | Either YELLOW | **YELLOW** 🟡 |
        | Both GREEN | **GREEN** 🟢 |
        | One GREEN + one N/A | **GREEN** 🟢 |
        | Both N/A | **N/A** |

        #### Group Status:
        | Condition | Group Status |
        |-----------|-------------|
        | Any RED in group | **NOK** 🔴 |
        | >35% YELLOW in group | **Acceptable** 🟡 |
        | Otherwise | **OK** 🟢 |
        """)

    with st.expander("📝 Data Input Format", expanded=True):
        st.markdown("""
        ### HeatMap Data (Data Transfer Sheet)

        Paste tab-separated data with:
        - **Row 1**: Header with vehicle names
        - **Row 2** (optional): DR markers
        - **Data rows**: `OpCode  OperationMode  Score1  Score2  ...`

        Example:
        ```
        \tOperation Modes\tBYD Atto 3\tDolphin Surf
        \tOperation Modes\tDR\tDR
        10000000\tAVL-DRIVE Rating\t8.3\t8.2
        10100000\tDrive away\t7.9\t7.4
        ```

        ### Sheet1 Data (Drivability / Responsiveness)

        **Recommended:** Upload the Excel (.xlsx / .xlsm) file directly.
        The tool reads the actual font colors of the dot (●) characters
        from the cells so you don't need to manually encode G/Y/R.

        **Alternative (text paste):** Encode dot colors as
        **G** = Green, **Y** = Yellow, **R** = Red, blank = N/A.

        Tab-separated columns:
        ```
        SectionOrBlank  OpCode  OpName  (empty)  DrivP1  DrivP2  DrivP3  DrivTested  DrivTarget  (empty)  RespP1  RespP2  RespP3  RespTested  RespTarget
        ```

        Section headers have text in column A with no op code.
        Data rows have op code in column B.
        """)

    with st.expander("🎨 Color Legend", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div style="background-color:{COLOR_GREEN};color:white;'
                       f'padding:10px;border-radius:5px;text-align:center;">'
                       f'🟢 GREEN</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div style="background-color:{COLOR_YELLOW};color:black;'
                       f'padding:10px;border-radius:5px;text-align:center;">'
                       f'🟡 YELLOW</div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div style="background-color:{COLOR_RED};color:white;'
                       f'padding:10px;border-radius:5px;text-align:center;">'
                       f'🔴 RED</div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div style="background-color:#F0F0F0;color:gray;'
                       'padding:10px;border-radius:5px;text-align:center;">'
                       '⚪ N/A</div>', unsafe_allow_html=True)


# ============================================================================
# Styling Helpers
# ============================================================================

def _score_gradient(v):
    """
    Compute the 3-point color-scale gradient matching the Excel conditional
    formatting on HeatMap score columns.

    Endpoints:
        score 1  → #FF0000 (red)
        score 7  → #FFFF00 (yellow)
        score 10 → #00B050 (green)

    Between endpoints the color is linearly interpolated in RGB space.
    Returns a ``#RRGGBB`` hex string.
    """
    if v <= SCORE_SCALE_MIN:
        r, g, b = SCORE_COLOR_MIN
    elif v >= SCORE_SCALE_MAX:
        r, g, b = SCORE_COLOR_MAX
    elif v <= SCORE_SCALE_MID:
        t = (v - SCORE_SCALE_MIN) / (SCORE_SCALE_MID - SCORE_SCALE_MIN)
        r = int(SCORE_COLOR_MIN[0] + t * (SCORE_COLOR_MID[0] - SCORE_COLOR_MIN[0]))
        g = int(SCORE_COLOR_MIN[1] + t * (SCORE_COLOR_MID[1] - SCORE_COLOR_MIN[1]))
        b = int(SCORE_COLOR_MIN[2] + t * (SCORE_COLOR_MID[2] - SCORE_COLOR_MIN[2]))
    else:
        t = (v - SCORE_SCALE_MID) / (SCORE_SCALE_MAX - SCORE_SCALE_MID)
        r = int(SCORE_COLOR_MID[0] + t * (SCORE_COLOR_MAX[0] - SCORE_COLOR_MID[0]))
        g = int(SCORE_COLOR_MID[1] + t * (SCORE_COLOR_MAX[1] - SCORE_COLOR_MID[1]))
        b = int(SCORE_COLOR_MID[2] + t * (SCORE_COLOR_MAX[2] - SCORE_COLOR_MID[2]))
    return f"#{r:02X}{g:02X}{b:02X}"


def _text_color_for_bg(hex_bg):
    """Return white or black text depending on background luminance."""
    hex_bg = hex_bg.lstrip("#")
    r, g, b = int(hex_bg[0:2], 16), int(hex_bg[2:4], 16), int(hex_bg[4:6], 16)
    # Relative luminance (ITU-R BT.709)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if lum > 140 else "#FFFFFF"


def _score_bg(val):
    """Return (background, text-color) CSS pair for an AVL score cell.

    Uses the same 3-point color gradient as the Excel HeatMap Sheet.
    Font is always black to match Excel (the color-scale conditional formatting
    only sets the background; the cell font stays as the base format = black).
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return (COLOR_WHITE, COLOR_BLACK)
    try:
        v = float(val)
    except (ValueError, TypeError):
        return (COLOR_WHITE, COLOR_BLACK)
    if v <= 0:
        return (COLOR_WHITE, COLOR_BLACK)
    bg = _score_gradient(v)
    return (bg, COLOR_BLACK)


def _status_bg(val):
    """Return (background, text-color) CSS pair for a status cell."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ("#FFFFFF", "#000000")
    v = str(val).upper().strip()
    if v == "GREEN":
        return (COLOR_GREEN, "#FFFFFF")
    if v == "YELLOW":
        return (COLOR_YELLOW, "#000000")
    if v == "RED":
        return (COLOR_RED, "#FFFFFF")
    return ("#FFFFFF", "#000000")


def _fmt_score(val):
    """Format a score value for display."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    try:
        v = float(val)
        # Display as integer if whole number, else one decimal
        return str(int(v)) if v == int(v) else f"{v:.1f}"
    except (ValueError, TypeError):
        return str(val)


def _comments_td(row, has_comments):
    """Return the ``<td>`` for the Comments column of a heatmap HTML row."""
    if has_comments:
        comment_val = row.get("Comments", "")
        comment_str = (
            str(comment_val).strip()
            if comment_val and not (isinstance(comment_val, float) and pd.isna(comment_val))
            else ""
        )
        return f'<td class="hm-comments">{_html.escape(comment_str)}</td>'
    return '<td class="hm-comments"></td>'


def _build_heatmap_html(df, vehicle_names, target_label):
    """
    Build an HTML table that replicates the exact look of the Excel HeatMap
    Sheet.

    Layout (matching the Excel):
    ┌──────────┬──────────────────────────┬───┬─────────────┬───┬─────────────┬──────────┬──────────┐
    │          │                          │   │Target Vehic.│   │             │          │          │
    │          │ Operation Modes          │   │ Vehicle 1   │   │ Vehicle 2   │  Status  │ Comments │
    │          │                          │   │ DR          │   │ DR          │          │          │
    ├──────────┼──────────────────────────┼───┼─────────────┼───┼─────────────┼──────────┼──────────┤
    │10000000  │ AVL-DRIVE Rating         │   │    8.3      │   │    8.2      │          │          │
    │10100000  │ Drive away  (bold/shade) │   │    7.9      │   │    7.4      │          │          │
    │10101300  │   Creep                  │   │    7.2      │   │    6.9      │          │          │
    └──────────┴──────────────────────────┴───┴─────────────┴───┴─────────────┴──────────┴──────────┘
    """
    # Column A is very narrow (hidden) in Excel, but we show it small for reference
    has_status = "Status" in df.columns

    # Derive vehicle column names from the DataFrame
    vehicle_cols = [c for c in df.columns if c not in ("Op Code", "Operation Mode", "Status", "Comments")]
    has_comments = "Comments" in df.columns

    # --- CSS --- (colors resolved from Excel HeatMap Sheet theme)
    css = f"""
    <style>
    .hm-wrap {{ overflow-x: auto; }}
    .hm-table {{
        border-collapse: collapse;
        font-family: Arial, Calibri, sans-serif;
        font-size: 12px;
        width: 100%;
        min-width: 600px;
    }}
    .hm-table th, .hm-table td {{
        border: 1px solid {COLOR_HEATMAP_BORDER};
        padding: 4px 8px;
        white-space: nowrap;
    }}
    /* Header rows – gray background, black text (Excel theme=0, tint=-0.15) */
    .hm-hdr {{
        background-color: {COLOR_HEATMAP_HEADER};
        color: {COLOR_BLACK};
        text-align: center;
        font-weight: bold;
    }}
    .hm-hdr-op {{
        background-color: {COLOR_HEATMAP_HEADER};
        color: {COLOR_BLACK};
        text-align: left;
        font-weight: bold;
    }}
    /* Sub-header (DR row) – same gray as header */
    .hm-sub {{
        background-color: {COLOR_HEATMAP_HEADER};
        color: {COLOR_BLACK};
        text-align: center;
        font-size: 11px;
    }}
    .hm-sub-op {{
        background-color: {COLOR_HEATMAP_HEADER};
        color: {COLOR_BLACK};
        text-align: left;
        font-size: 11px;
    }}
    /* Narrow separator column */
    .hm-sep {{ width: 6px; min-width: 6px; max-width: 6px; padding: 0; background: {COLOR_WHITE}; border-left: none; border-right: none; }}
    /* Op Code column – hidden but kept in DOM */
    .hm-code {{ display: none; }}
    /* Operation Mode column */
    .hm-opname {{ text-align: left; min-width: 220px; }}
    /* Score cell */
    .hm-score {{ text-align: center; min-width: 100px; font-size: 12px; }}
    /* Status cell */
    .hm-status {{ text-align: center; min-width: 80px; font-weight: bold; }}
    /* Comments cell */
    .hm-comments {{ text-align: left; min-width: 120px; }}
    /* Parent (bold group header) row – same gray background */
    .hm-parent td {{ font-weight: bold; }}
    .hm-parent .hm-opname {{ background-color: {COLOR_HEATMAP_HEADER}; }}
    .hm-parent .hm-code {{ background-color: {COLOR_HEATMAP_HEADER}; }}
    /* Target label row – white background, black text (Excel theme=0, tint=0) */
    .hm-target {{ background-color: {COLOR_WHITE}; color: {COLOR_BLACK}; text-align: center; font-weight: bold; font-size: 11px; }}
    </style>
    """

    rows_html = []

    # --- Row 1: "Target Vehicle" / "Tested Vehicle" labels above vehicle columns ---
    r1 = '<tr>'
    r1 += '<td class="hm-code"></td>'  # Op Code (hidden)
    r1 += '<td class="hm-hdr" style="border:none;background:transparent;"></td>'  # Op Mode
    for i, vname in enumerate(vehicle_cols):
        r1 += '<td class="hm-sep"></td>'  # separator
        if i == 0:
            r1 += '<td class="hm-target">Target Vehicle</td>'
        elif i == 1:
            r1 += '<td class="hm-target">Tested Vehicle</td>'
        else:
            r1 += '<td style="border:none;background:transparent;"></td>'
    if has_status:
        r1 += '<td style="border:none;background:transparent;"></td>'
        r1 += '<td style="border:none;background:transparent;"></td>'
    r1 += '</tr>'
    rows_html.append(r1)

    # --- Row 2: Column headers with vehicle names ---
    r2 = '<tr>'
    r2 += '<td class="hm-code"></td>'
    r2 += '<td class="hm-hdr-op">Operation Modes</td>'
    for vname in vehicle_cols:
        r2 += '<td class="hm-sep"></td>'
        r2 += f'<td class="hm-hdr">{_html.escape(str(vname))}</td>'
    if has_status:
        r2 += f'<td class="hm-hdr">Status</td>'
        r2 += f'<td class="hm-hdr">Comments</td>'
    r2 += '</tr>'
    rows_html.append(r2)

    # --- Row 3: DR markers ---
    r3 = '<tr>'
    r3 += '<td class="hm-code"></td>'
    r3 += '<td class="hm-sub-op"></td>'
    for _vname in vehicle_cols:
        r3 += '<td class="hm-sep"></td>'
        r3 += '<td class="hm-sub">DR</td>'
    if has_status:
        r3 += '<td class="hm-sub"></td>'
        r3 += '<td class="hm-sub"></td>'
    r3 += '</tr>'
    rows_html.append(r3)

    # --- Data rows ---
    for _, row in df.iterrows():
        op_code = row.get("Op Code", "")
        op_name = row.get("Operation Mode", "")
        is_parent = op_code in PARENT_OPERATION_CODES

        tr_class = ' class="hm-parent"' if is_parent else ''
        r = f'<tr{tr_class}>'
        r += f'<td class="hm-code">{op_code}</td>'
        r += f'<td class="hm-opname">{_html.escape(str(op_name))}</td>'

        for vname in vehicle_cols:
            val = row.get(vname)
            bg, fc = _score_bg(val)
            display = _fmt_score(val)
            r += '<td class="hm-sep"></td>'
            r += (
                f'<td class="hm-score" style="background-color:{bg};color:{fc};">'
                f'{display}</td>'
            )

        if has_status:
            status_val = row.get("Status", "")
            status_str = str(status_val).strip() if status_val and not (isinstance(status_val, float) and pd.isna(status_val)) else ""
            status_upper = status_str.upper()

            if is_parent:
                # Parent rows show text: OK / Acceptable / NOK with color
                # Colors match the HeatMap Sheet conditional formatting exactly
                if status_upper == "NOK":
                    sbg, sfc = (COLOR_RED, "#FFFFFF")
                elif status_upper == "ACCEPTABLE":
                    sbg, sfc = (COLOR_YELLOW_BRIGHT, "#000000")
                elif status_upper == "OK":
                    sbg, sfc = (COLOR_GREEN, "#FFFFFF")
                else:
                    sbg, sfc = ("#FFFFFF", "#000000")
                r += (
                    f'<td class="hm-status" style="background-color:{sbg};color:{sfc};">'
                    f'{_html.escape(status_str)}</td>'
                )
            else:
                # Sub-operation rows show a colored dot (●)
                if status_upper in ("GREEN", "YELLOW", "RED"):
                    dot_color = {
                        "GREEN": COLOR_GREEN,
                        "YELLOW": COLOR_YELLOW,
                        "RED": COLOR_RED,
                    }[status_upper]
                    r += (
                        f'<td class="hm-status" style="background-color:#FFFFFF;">'
                        f'<span style="color:{dot_color};font-size:18px;">●</span></td>'
                    )
                else:
                    r += '<td class="hm-status"></td>'
            r += _comments_td(row, has_comments)

        r += '</tr>'
        rows_html.append(r)

    table = f'{css}<div class="hm-wrap"><table class="hm-table">{"".join(rows_html)}</table></div>'
    return table


def _hex_to_rgb(hex_color):
    """Convert ``#RRGGBB`` to a matplotlib-compatible ``(r, g, b)`` tuple (0–1)."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def _render_heatmap_image(df, vehicle_names, target_label):
    """Render the heatmap DataFrame as a JPG byte buffer using matplotlib.

    This replaces the previous html2canvas approach which hung indefinitely
    on large tables inside the Streamlit iframe.

    Returns
    -------
    io.BytesIO
        A JPEG image of the full heatmap table.
    """
    has_status = "Status" in df.columns
    has_comments = "Comments" in df.columns
    vehicle_cols = [c for c in df.columns if c not in ("Op Code", "Operation Mode", "Status", "Comments")]

    # ----- Build cell data, colors, and widths -----
    # Column structure:  OpMode | sep | vehicle1 | sep | vehicle2 | ... | Status | Comments
    # We skip Op Code (hidden) and separators (drawn as thin gaps).

    # Column widths (inches) – proportional to content
    OP_W = 2.8
    SEP_W = 0.06
    STATUS_W = 1.0
    COMMENTS_W_MIN = 1.4
    ROW_H = 0.28
    HDR_H = 0.28
    FONT_SIZE = 8
    VEH_HDR_FONT = 7  # font size used for vehicle name headers
    COMMENT_FONT = 6  # smaller font for comment text

    # Dynamically size vehicle columns based on name length so names are
    # never clipped.  Approximate width: ~0.075 inches per character at 7pt,
    # with a minimum of 1.2 inches (enough for score values).
    VEH_W_MIN = 1.2
    CHAR_WIDTH_INCHES = 0.075
    veh_col_widths = []
    for vname in vehicle_cols:
        needed = len(str(vname)) * CHAR_WIDTH_INCHES + 0.2  # 0.2 padding
        veh_col_widths.append(max(VEH_W_MIN, needed))

    # Dynamically size the Comments column based on the longest comment.
    COMMENTS_W = COMMENTS_W_MIN
    if has_comments:
        max_comment_len = max(
            (len(str(v)) for v in df["Comments"] if v and not (isinstance(v, float) and pd.isna(v))),
            default=0,
        )
        # ~0.055 inches per char at 6pt + padding
        needed_cw = max_comment_len * 0.055 + 0.3
        COMMENTS_W = max(COMMENTS_W_MIN, needed_cw)

    n_veh = len(vehicle_cols)
    col_widths = [OP_W]
    for vw in veh_col_widths:
        col_widths.append(SEP_W)
        col_widths.append(vw)
    if has_status:
        col_widths.append(STATUS_W)
        col_widths.append(COMMENTS_W)

    n_cols = len(col_widths)
    total_w = sum(col_widths)

    # Build rows: 3 header rows + data rows
    n_data_rows = len(df)
    n_total_rows = 3 + n_data_rows
    total_h = n_total_rows * ROW_H + 0.1  # small margin

    hdr_bg = _hex_to_rgb(COLOR_HEATMAP_HEADER)
    white_bg = (1, 1, 1)
    black_fc = (0, 0, 0)
    white_fc = (1, 1, 1)

    fig, ax = plt.subplots(figsize=(total_w, total_h))
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    def draw_cell(x, y, w, h, bg, text, fc=black_fc, bold=False, align="center", fontsize=FONT_SIZE):
        """Draw a single table cell."""
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=bg, edgecolor=(0, 0, 0), linewidth=0.5, clip_on=False))
        if text:
            ha = "center" if align == "center" else "left"
            tx = x + w / 2 if align == "center" else x + 0.05
            ax.text(
                tx, y + h / 2, text,
                fontsize=fontsize, color=fc,
                fontweight="bold" if bold else "normal",
                ha=ha, va="center", clip_on=True,
            )

    def draw_sep(x, y, h):
        """Draw a thin separator column (no border)."""
        ax.add_patch(plt.Rectangle((x, y), SEP_W, h, facecolor=white_bg, edgecolor="none", linewidth=0))

    def row_y(row_idx):
        """Y coordinate for row *row_idx* (0 = top)."""
        return total_h - (row_idx + 1) * ROW_H - 0.05

    # ---- Row 0: Target / Tested labels ----
    y0 = row_y(0)
    # Op Mode cell – empty, no border
    ax.add_patch(plt.Rectangle((0, y0), OP_W, ROW_H, facecolor=white_bg, edgecolor="none"))
    cx = OP_W
    for i in range(n_veh):
        vw = veh_col_widths[i]
        draw_sep(cx, y0, ROW_H)
        cx += SEP_W
        label = "Target Vehicle" if i == 0 else ("Tested Vehicle" if i == 1 else "")
        draw_cell(cx, y0, vw, ROW_H, white_bg, label, bold=True, fontsize=VEH_HDR_FONT)
        cx += vw
    if has_status:
        ax.add_patch(plt.Rectangle((cx, y0), STATUS_W, ROW_H, facecolor=white_bg, edgecolor="none"))
        cx += STATUS_W
        ax.add_patch(plt.Rectangle((cx, y0), COMMENTS_W, ROW_H, facecolor=white_bg, edgecolor="none"))

    # ---- Row 1: Column headers ----
    y1 = row_y(1)
    draw_cell(0, y1, OP_W, ROW_H, hdr_bg, "Operation Modes", bold=True, align="left")
    cx = OP_W
    for i, vname in enumerate(vehicle_cols):
        vw = veh_col_widths[i]
        draw_sep(cx, y1, ROW_H)
        cx += SEP_W
        draw_cell(cx, y1, vw, ROW_H, hdr_bg, str(vname), bold=True, fontsize=VEH_HDR_FONT)
        cx += vw
    if has_status:
        draw_cell(cx, y1, STATUS_W, ROW_H, hdr_bg, "Status", bold=True)
        cx += STATUS_W
        draw_cell(cx, y1, COMMENTS_W, ROW_H, hdr_bg, "Comments", bold=True)

    # ---- Row 2: DR markers ----
    y2 = row_y(2)
    draw_cell(0, y2, OP_W, ROW_H, hdr_bg, "", align="left")
    cx = OP_W
    for i in range(n_veh):
        vw = veh_col_widths[i]
        draw_sep(cx, y2, ROW_H)
        cx += SEP_W
        draw_cell(cx, y2, vw, ROW_H, hdr_bg, "DR", fontsize=VEH_HDR_FONT)
        cx += vw
    if has_status:
        draw_cell(cx, y2, STATUS_W, ROW_H, hdr_bg, "")
        cx += STATUS_W
        draw_cell(cx, y2, COMMENTS_W, ROW_H, hdr_bg, "")

    # ---- Data rows ----
    for row_idx, (_, row) in enumerate(df.iterrows()):
        yd = row_y(3 + row_idx)
        op_code = row.get("Op Code", "")
        op_name = str(row.get("Operation Mode", ""))
        is_parent = op_code in PARENT_OPERATION_CODES

        op_bg = hdr_bg if is_parent else white_bg
        draw_cell(0, yd, OP_W, ROW_H, op_bg, op_name, bold=is_parent, align="left")

        cx = OP_W
        for i, vname in enumerate(vehicle_cols):
            vw = veh_col_widths[i]
            draw_sep(cx, yd, ROW_H)
            cx += SEP_W
            val = row.get(vname)
            bg_hex, fc_hex = _score_bg(val)
            display = _fmt_score(val)
            draw_cell(cx, yd, vw, ROW_H, _hex_to_rgb(bg_hex), display, fc=_hex_to_rgb(fc_hex))
            cx += vw

        if has_status:
            status_val = row.get("Status", "")
            status_str = str(status_val).strip() if status_val and not (isinstance(status_val, float) and pd.isna(status_val)) else ""
            status_upper = status_str.upper()

            if is_parent:
                if status_upper == "NOK":
                    sbg, sfc = _hex_to_rgb(COLOR_RED), white_fc
                elif status_upper == "ACCEPTABLE":
                    sbg, sfc = _hex_to_rgb(COLOR_YELLOW_BRIGHT), black_fc
                elif status_upper == "OK":
                    sbg, sfc = _hex_to_rgb(COLOR_GREEN), white_fc
                else:
                    sbg, sfc = white_bg, black_fc
                draw_cell(cx, yd, STATUS_W, ROW_H, sbg, status_str, fc=sfc, bold=True)
            else:
                draw_cell(cx, yd, STATUS_W, ROW_H, white_bg, "")
                if status_upper in ("GREEN", "YELLOW", "RED"):
                    dot_color = _hex_to_rgb({
                        "GREEN": COLOR_GREEN,
                        "YELLOW": COLOR_YELLOW,
                        "RED": COLOR_RED,
                    }[status_upper])
                    dot_x = cx + STATUS_W / 2
                    dot_y = yd + ROW_H / 2
                    ax.plot(dot_x, dot_y, "o", color=dot_color, markersize=6, clip_on=False)
            cx += STATUS_W
            comment_text = ""
            if has_comments:
                cv = row.get("Comments", "")
                comment_text = str(cv).strip() if cv and not (isinstance(cv, float) and pd.isna(cv)) else ""
            draw_cell(cx, yd, COMMENTS_W, ROW_H, white_bg, comment_text, align="left", fontsize=COMMENT_FONT)

    buf = io.BytesIO()
    fig.savefig(buf, format="jpeg", dpi=200, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    return buf


def _dot_html(status):
    """Return an HTML colored dot (●) matching the Excel font color."""
    color_map = {
        "GREEN": "#008000",
        "YELLOW": "#FFFF00",
        "RED": "#FF0000",
    }
    color = color_map.get(str(status).upper(), "#D0D0D0")
    if str(status).upper() in ("N/A", ""):
        # White/no-data dot — show faint on the gray background
        return '<span style="color:#FFFFFF;font-size:16px;">●</span>'
    return f'<span style="color:{color};font-size:16px;">●</span>'


def _build_sheet1_html(operations, sections, tested_car, target_car):
    """
    Build an HTML table that displays Sheet1 data with actual colored dots,
    replicating the Excel look.  Colors match the Excel Sheet1 / ODRIV RATING
    tab exactly.
    """
    css = f"""
    <style>
    .s1-wrap {{ overflow-x: auto; }}
    .s1-table {{
        border-collapse: collapse;
        font-family: Arial, Calibri, sans-serif;
        font-size: 12px;
        width: 100%;
        min-width: 800px;
    }}
    .s1-table th, .s1-table td {{
        border: 1px solid #B4C6E7;
        padding: 4px 6px;
        white-space: nowrap;
    }}
    .s1-hdr {{
        background-color: {COLOR_SHEET1_HEADER};
        color: #FFFFFF;
        text-align: center;
        font-weight: bold;
    }}
    .s1-hdr-left {{
        background-color: {COLOR_SHEET1_HEADER};
        color: #FFFFFF;
        text-align: left;
        font-weight: bold;
    }}
    .s1-sub {{
        background-color: {COLOR_SHEET1_HEADER};
        color: #FFFFFF;
        text-align: center;
        font-size: 11px;
    }}
    .s1-section td {{
        font-weight: bold;
        background-color: {COLOR_SHEET1_SECTION_BG};
    }}
    .s1-code {{ text-align: left; font-size: 10px; color: #808080; width: 70px; }}
    .s1-opname {{ text-align: left; min-width: 180px; }}
    .s1-dot {{ text-align: center; width: 30px; background: {COLOR_SHEET1_DOT_BG}; }}
    .s1-pct {{ text-align: center; min-width: 60px; }}
    </style>
    """

    rows_html = []

    # --- Header row 1: Drivability / Responsiveness spans ---
    r = '<tr>'
    r += '<td class="s1-hdr" rowspan="2" style="width:70px;"></td>'
    r += '<td class="s1-hdr-left" rowspan="2" style="min-width:180px;">USE CASE</td>'
    r += f'<td class="s1-hdr" colspan="5">Drivability</td>'
    r += f'<td class="s1-hdr" colspan="5">Responsiveness</td>'
    r += '</tr>'
    rows_html.append(r)

    # --- Header row 2: P1 P2 P3 Tested Target ---
    r = '<tr>'
    r += '<td class="s1-sub">P1</td>'
    r += '<td class="s1-sub">P2</td>'
    r += '<td class="s1-sub">P3</td>'
    r += f'<td class="s1-sub">{_html.escape(tested_car)}</td>'
    r += f'<td class="s1-sub">{_html.escape(target_car)}</td>'
    r += '<td class="s1-sub">P1</td>'
    r += '<td class="s1-sub">P2</td>'
    r += '<td class="s1-sub">P3</td>'
    r += f'<td class="s1-sub">{_html.escape(tested_car)}</td>'
    r += f'<td class="s1-sub">{_html.escape(target_car)}</td>'
    r += '</tr>'
    rows_html.append(r)

    # Build a section lookup for section header rows
    section_set = {s["name"] for s in sections}
    # Track which sections have already been rendered
    rendered_sections = set()

    for op in operations:
        section_name = op.get("section", "")

        # Emit section header row if not yet rendered
        if section_name and section_name not in rendered_sections:
            rendered_sections.add(section_name)
            sec_info = next((s for s in sections if s["name"] == section_name), None)
            r = '<tr class="s1-section">'
            r += '<td></td>'
            r += f'<td>{_html.escape(section_name)}</td>'
            r += '<td></td><td></td><td></td>'  # P1 P2 P3
            # driv tested / target averages
            dtv = sec_info["driv_tested_avg"] if sec_info else 0
            dta = sec_info["driv_target_avg"] if sec_info else 0
            r += f'<td class="s1-pct">{_fmt_score(dtv) if dtv else ""}</td>'
            r += f'<td class="s1-pct">{_fmt_score(dta) if dta else ""}</td>'
            r += '<td></td><td></td><td></td>'  # P1 P2 P3
            rtv = sec_info["resp_tested_avg"] if sec_info else 0
            rta = sec_info["resp_target_avg"] if sec_info else 0
            r += f'<td class="s1-pct">{_fmt_score(rtv) if rtv else ""}</td>'
            r += f'<td class="s1-pct">{_fmt_score(rta) if rta else ""}</td>'
            r += '</tr>'
            rows_html.append(r)

        # Data row
        r = '<tr>'
        r += f'<td class="s1-code">{op["op_code"]}</td>'
        r += f'<td class="s1-opname">{_html.escape(op["operation"])}</td>'

        # Drivability dots + percentages
        r += f'<td class="s1-dot">{_dot_html(op["driv_p1"])}</td>'
        r += f'<td class="s1-dot">{_dot_html(op["driv_p2"])}</td>'
        r += f'<td class="s1-dot">{_dot_html(op["driv_p3"])}</td>'
        r += f'<td class="s1-pct">{_fmt_score(op["driv_tested"])}</td>'
        r += f'<td class="s1-pct">{_fmt_score(op["driv_target"])}</td>'

        # Responsiveness dots + percentages
        r += f'<td class="s1-dot">{_dot_html(op["resp_p1"])}</td>'
        r += f'<td class="s1-dot">{_dot_html(op["resp_p2"])}</td>'
        r += f'<td class="s1-dot">{_dot_html(op["resp_p3"])}</td>'
        r += f'<td class="s1-pct">{_fmt_score(op["resp_tested"])}</td>'
        r += f'<td class="s1-pct">{_fmt_score(op["resp_target"])}</td>'

        r += '</tr>'
        rows_html.append(r)

    table = f'{css}<div class="s1-wrap"><table class="s1-table">{"".join(rows_html)}</table></div>'
    return table


def _style_evaluation_results(df):
    """Apply color styling to evaluation results."""
    def _color_status(val):
        if pd.isna(val) or val == "":
            return ""
        val_upper = str(val).upper()
        if val_upper == "GREEN":
            return f"background-color: {COLOR_GREEN}; color: white"
        elif val_upper == "YELLOW":
            return f"background-color: {COLOR_YELLOW}; color: black"
        elif val_upper == "RED":
            return f"background-color: {COLOR_RED}; color: white"
        return ""

    status_cols = [c for c in df.columns if "Status" in c or "P1" in c]
    return df.style.map(_color_status, subset=status_cols)


def _style_overall_status(df):
    """Apply color styling to overall status summary."""
    def _color_status(val):
        if pd.isna(val) or val == "":
            return ""
        val_upper = str(val).upper()
        if val_upper == "GREEN":
            return f"background-color: {COLOR_GREEN}; color: white"
        elif val_upper == "YELLOW":
            return f"background-color: {COLOR_YELLOW}; color: black"
        elif val_upper == "RED":
            return f"background-color: {COLOR_RED}; color: white"
        return ""

    return df.style.map(_color_status, subset=["Overall Status"])


def _show_status_distribution(eval_results):
    """Show status distribution charts."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Drivability Status**")
        driv_counts = eval_results["Driv Status"].value_counts()
        _show_status_metrics(driv_counts)

    with col2:
        st.markdown("**Responsiveness Status**")
        resp_counts = eval_results["Resp Status"].value_counts()
        _show_status_metrics(resp_counts)

    with col3:
        st.markdown("**Final Status**")
        final_counts = eval_results["Final Status"].value_counts()
        _show_status_metrics(final_counts)


def _show_status_metrics(counts):
    """Display status counts as colored metrics."""
    for status in ["GREEN", "YELLOW", "RED", "N/A"]:
        count = counts.get(status, 0)
        color = STATUS_COLORS.get(status, "#CCCCCC")
        emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "N/A": "⚪"}.get(status, "")
        st.markdown(f"{emoji} **{status}**: {count}")


def _show_group_status(sheet1_data):
    """Display group-level status evaluation."""
    sections = sheet1_data.get("sections", [])
    operations = sheet1_data.get("operations", [])

    if not sections:
        st.info("No section grouping detected.")
        return

    for section in sections:
        section_name = section["name"]
        section_ops = [op for op in operations if op.get("section") == section_name]

        if not section_ops:
            continue

        driv_group = calculate_group_status(section_ops, "driv_p1")
        resp_group = calculate_group_status(section_ops, "resp_p1")

        driv_emoji = {"NOK": "🔴", "Acceptable": "🟡", "OK": "🟢"}.get(driv_group, "⚪")
        resp_emoji = {"NOK": "🔴", "Acceptable": "🟡", "OK": "🟢"}.get(resp_group, "⚪")

        st.markdown(
            f"**{section_name}** — "
            f"Drivability: {driv_emoji} {driv_group or 'N/A'}  |  "
            f"Responsiveness: {resp_emoji} {resp_group or 'N/A'}"
        )


if __name__ == "__main__":
    main()
