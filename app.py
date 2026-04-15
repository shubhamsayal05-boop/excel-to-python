"""
AVL-DRIVE Heatmap Tool - Python Version
A Streamlit web application that replicates the Excel-based AVL-DRIVE Heatmap Tool.

Usage:
    streamlit run app.py
"""

import html as _html
import io

import pandas as pd
import streamlit as st

from config import (
    STATUS_COLORS,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BLUE_HEADER,
    OPERATION_MODE_MAPPING,
    AVL_ODRIV_MAPPING,
    PARENT_OPERATION_CODES,
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
    evaluate_avl_status,
    build_overall_status,
    update_sub_operation_heatmap,
    calculate_group_status,
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
    st.markdown("**Python version** — Independent of Excel, fully replicating the "
                "original AVL-DRIVE Heatmap Tool v5.1")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        [
            "📋 HeatMap Data Input",
            "📊 Sheet1 Data Input",
            "🔥 HeatMap View",
            "📈 Evaluation Results",
            "📖 Help & Reference",
        ],
    )

    if page == "📋 HeatMap Data Input":
        heatmap_input_page()
    elif page == "📊 Sheet1 Data Input":
        sheet1_input_page()
    elif page == "🔥 HeatMap View":
        heatmap_view_page()
    elif page == "📈 Evaluation Results":
        evaluation_results_page()
    elif page == "📖 Help & Reference":
        help_page()


# ============================================================================
# Page: HeatMap Data Input
# ============================================================================
def heatmap_input_page():
    st.header("📋 HeatMap Data Input")
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
# Page: Sheet1 Data Input
# ============================================================================
def sheet1_input_page():
    st.header("📊 Sheet1 Data Input (Drivability / Responsiveness)")
    st.markdown("""
    Load your **Sheet1** data containing the Drivability and Responsiveness
    evaluation data with colored dot statuses.

    **Recommended:** Upload the Excel file directly so dot colors (green / yellow / red)
    are read automatically. If pasting as text, encode dot colors as **G**, **Y**, **R**,
    or leave blank for N/A.
    """)

    input_method = st.radio(
        "Input method:",
        ["Upload Excel File (recommended)", "Paste Text"],
        key="sheet1_input_method",
    )

    if input_method == "Upload Excel File (recommended)":
        uploaded_file = st.file_uploader(
            "Upload the AVL-DRIVE Excel file (.xlsx / .xlsm):",
            type=["xlsx", "xlsm"],
            key="sheet1_file",
        )

        if uploaded_file and st.button("🔄 Process Sheet1 from Excel", key="process_sheet1_excel"):
            with st.spinner("Reading Sheet1 and extracting dot colors..."):
                parsed = parse_sheet1_from_excel(uploaded_file)
            if parsed:
                st.session_state["sheet1_data"] = parsed
                st.success(
                    f"✅ Loaded {len(parsed['operations'])} operations in "
                    f"{len(parsed['sections'])} sections.\n\n"
                    f"**Target:** {parsed['target_car']}  |  "
                    f"**Tested:** {parsed['tested_car']}"
                )
            else:
                st.error(
                    "❌ Could not parse Sheet1. Make sure the file contains a "
                    "sheet named **Sheet1** with the expected layout."
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
# Page: HeatMap View
# ============================================================================
def heatmap_view_page():
    st.header("🔥 HeatMap View")

    if "heatmap_data" not in st.session_state:
        st.info("ℹ️ No heatmap data loaded. Go to **HeatMap Data Input** to load data.")
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

    # Build the target vehicle label for the header
    target_label = target_vehicle or "Target Vehicle"

    # Render the Excel-style HTML heatmap
    html = _build_heatmap_html(display_df, vehicle_names, target_label)
    st.markdown(html, unsafe_allow_html=True)

    # Export
    st.subheader("Export")
    col1, col2 = st.columns(2)
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


# ============================================================================
# Page: Evaluation Results
# ============================================================================
def evaluation_results_page():
    st.header("📈 Evaluation Results")

    if "sheet1_data" not in st.session_state:
        st.info("ℹ️ No Sheet1 data loaded. Go to **Sheet1 Data Input** to load data.")
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

def _score_bg(val):
    """Return (background, text-color) CSS pair for an AVL score cell."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ("#FFFFFF", "#000000")
    try:
        v = float(val)
    except (ValueError, TypeError):
        return ("#FFFFFF", "#000000")
    if v >= 8.0:
        return (COLOR_GREEN, "#FFFFFF")
    if v >= 7.0:
        return (COLOR_YELLOW, "#000000")
    if v > 0:
        return (COLOR_RED, "#FFFFFF")
    return ("#FFFFFF", "#000000")


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
    vehicle_cols = [c for c in df.columns if c not in ("Op Code", "Operation Mode", "Status")]

    # --- CSS ---
    css = """
    <style>
    .hm-wrap { overflow-x: auto; }
    .hm-table {
        border-collapse: collapse;
        font-family: Arial, Calibri, sans-serif;
        font-size: 12px;
        width: 100%;
        min-width: 600px;
    }
    .hm-table th, .hm-table td {
        border: 1px solid #B4C6E7;
        padding: 4px 8px;
        white-space: nowrap;
    }
    /* Header rows */
    .hm-hdr {
        background-color: #4472C4;
        color: #FFFFFF;
        text-align: center;
        font-weight: bold;
    }
    .hm-hdr-op {
        background-color: #4472C4;
        color: #FFFFFF;
        text-align: left;
        font-weight: bold;
    }
    /* Sub-header (DR row) */
    .hm-sub {
        background-color: #D9E1F2;
        text-align: center;
        font-size: 11px;
    }
    .hm-sub-op {
        background-color: #D9E1F2;
        text-align: left;
        font-size: 11px;
    }
    /* Narrow separator column */
    .hm-sep { width: 6px; min-width: 6px; max-width: 6px; padding: 0; background: #FFFFFF; border-left: none; border-right: none; }
    /* Op Code column (narrow) */
    .hm-code { text-align: left; font-size: 10px; color: #808080; width: 70px; }
    /* Operation Mode column */
    .hm-opname { text-align: left; min-width: 220px; }
    /* Score cell */
    .hm-score { text-align: center; min-width: 100px; font-size: 12px; }
    /* Status cell */
    .hm-status { text-align: center; min-width: 80px; font-weight: bold; }
    /* Comments cell */
    .hm-comments { text-align: left; min-width: 120px; }
    /* Parent (bold group header) row */
    .hm-parent td { font-weight: bold; }
    .hm-parent .hm-opname { background-color: #D6DCE4; }
    .hm-parent .hm-code { background-color: #D6DCE4; }
    /* Target label row */
    .hm-target { background-color: #4472C4; color: #FFFFFF; text-align: center; font-weight: bold; font-size: 11px; }
    </style>
    """

    rows_html = []

    # --- Row 1: "Target Vehicle" label spanning vehicle columns ---
    # Only show if we know which is the target
    n_vehicle_cols = len(vehicle_cols)
    # Each vehicle takes 2 columns (separator + score) except the first which takes just 1 score col
    # Total vehicle-related columns = n_vehicle_cols * 2 - 1  (separators between)
    # But for simplicity: code col + op col + (sep + score) * n + status + comments

    # Build header row 1: Target Vehicle label above the first vehicle column
    r1 = '<tr>'
    r1 += '<td class="hm-hdr" style="border:none;background:transparent;"></td>'  # Op Code
    r1 += '<td class="hm-hdr" style="border:none;background:transparent;"></td>'  # Op Mode
    for i, vname in enumerate(vehicle_cols):
        r1 += '<td class="hm-sep"></td>'  # separator
        if i == 0:
            r1 += f'<td class="hm-target">Target Vehicle</td>'
        else:
            r1 += '<td style="border:none;background:transparent;"></td>'
    if has_status:
        r1 += '<td style="border:none;background:transparent;"></td>'
        r1 += '<td style="border:none;background:transparent;"></td>'
    r1 += '</tr>'
    rows_html.append(r1)

    # --- Row 2: Column headers with vehicle names ---
    r2 = '<tr>'
    r2 += '<td class="hm-hdr" style="width:70px;"></td>'
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
    r3 += '<td class="hm-sub"></td>'
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
            sbg, sfc = _status_bg(status_val)
            status_display = str(status_val) if status_val and not (isinstance(status_val, float) and pd.isna(status_val)) else ""
            r += (
                f'<td class="hm-status" style="background-color:{sbg};color:{sfc};">'
                f'{_html.escape(status_display)}</td>'
            )
            r += '<td class="hm-comments"></td>'

        r += '</tr>'
        rows_html.append(r)

    table = f'{css}<div class="hm-wrap"><table class="hm-table">{"".join(rows_html)}</table></div>'
    return table


def _dot_html(status):
    """Return an HTML colored dot (●) matching the Excel font color."""
    color_map = {
        "GREEN": "#008000",
        "YELLOW": "#FFFF00",
        "RED": "#FF0000",
    }
    color = color_map.get(str(status).upper(), "#D0D0D0")
    if str(status).upper() in ("N/A", ""):
        # White dot on dark background is hard to see — use a light gray
        return '<span style="color:#D0D0D0;font-size:16px;">●</span>'
    return f'<span style="color:{color};font-size:16px;">●</span>'


def _build_sheet1_html(operations, sections, tested_car, target_car):
    """
    Build an HTML table that displays Sheet1 data with actual colored dots,
    replicating the Excel look.
    """
    css = """
    <style>
    .s1-wrap { overflow-x: auto; }
    .s1-table {
        border-collapse: collapse;
        font-family: Arial, Calibri, sans-serif;
        font-size: 12px;
        width: 100%;
        min-width: 800px;
    }
    .s1-table th, .s1-table td {
        border: 1px solid #B4C6E7;
        padding: 4px 6px;
        white-space: nowrap;
    }
    .s1-hdr {
        background-color: #4472C4;
        color: #FFFFFF;
        text-align: center;
        font-weight: bold;
    }
    .s1-hdr-left {
        background-color: #4472C4;
        color: #FFFFFF;
        text-align: left;
        font-weight: bold;
    }
    .s1-sub {
        background-color: #D9E1F2;
        text-align: center;
        font-size: 11px;
    }
    .s1-section td {
        font-weight: bold;
        background-color: #D6DCE4;
    }
    .s1-code { text-align: left; font-size: 10px; color: #808080; width: 70px; }
    .s1-opname { text-align: left; min-width: 180px; }
    .s1-dot { text-align: center; width: 30px; background: #2B2B2B; }
    .s1-pct { text-align: center; min-width: 60px; }
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
