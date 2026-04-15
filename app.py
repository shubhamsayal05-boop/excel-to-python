"""
AVL-DRIVE Heatmap Tool - Python Version
A Streamlit web application that replicates the Excel-based AVL-DRIVE Heatmap Tool.

Usage:
    streamlit run app.py
"""

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
)
from heatmap_engine import (
    build_heatmap_template,
    parse_heatmap_data,
    refresh_heatmap,
    filter_heatmap_rows,
)
from evaluation_engine import (
    parse_sheet1_data,
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
    Paste your **Sheet1** data here. This contains the Drivability and Responsiveness
    evaluation data with colored dot statuses.

    **Since colors can't be pasted as text**, encode dot colors as:
    - **G** = Green ●
    - **Y** = Yellow ●
    - **R** = Red ●
    - Leave **blank** = White/No data (N/A)

    **Expected format** (tab-separated):
    ```
    				Drivability					Responsiveness
    			Current Status	Tested_Vehicle	Target_Vehicle	Driv Lowest	Current Status	Tested_Vehicle	Target_Vehicle	Resp Lowest
    USE CASE			P1	P2	P3			P1	P2	P3
    Drive away								78.8	84.4					99	98.2
    	10102400	DA Rolling Start	G	G	G	100	100		G	G	G	100	93
    	10101300	Drive Away Creep	R	G	G	11.2	34.3		G	G	G	100	100
    ...
    ```
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
                # Override car names if provided
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

    # Show parsed data if available
    if "sheet1_data" in st.session_state:
        data = st.session_state["sheet1_data"]
        st.subheader("Parsed Operations")

        ops_df = pd.DataFrame(data["operations"])
        if not ops_df.empty:
            st.dataframe(ops_df, use_container_width=True)

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

    # Style the dataframe
    st.subheader(f"HeatMap — Target: {target_vehicle or 'N/A'} | Tested: {tested_vehicle or 'N/A'}")

    styled_df = _style_heatmap(display_df)
    st.dataframe(styled_df, use_container_width=True, height=800)

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

        Since colored dots can't be pasted as text, encode colors:
        - **G** = Green, **Y** = Yellow, **R** = Red, blank = N/A

        Paste tab-separated with columns:
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
def _style_heatmap(df):
    """Apply color styling to heatmap DataFrame."""
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

    def _color_avl_score(val):
        if pd.isna(val) or val == "" or val is None:
            return ""
        try:
            v = float(val)
            if v >= 8.0:
                return f"background-color: {COLOR_GREEN}; color: white"
            elif v >= 7.0:
                return f"background-color: {COLOR_YELLOW}; color: black"
            elif v > 0:
                return f"background-color: {COLOR_RED}; color: white"
        except (ValueError, TypeError):
            pass
        return ""

    styled = df.style

    # Color the Status column
    if "Status" in df.columns:
        styled = styled.map(_color_status, subset=["Status"])

    # Color vehicle score columns
    vehicle_cols = [c for c in df.columns
                   if c not in ("Op Code", "Operation Mode", "Status")]
    if vehicle_cols:
        styled = styled.map(_color_avl_score, subset=vehicle_cols)

    return styled


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
