"""
Evaluation Engine - Handles the evaluation logic.
Corresponds to the VBA EvaluateAVLStatus macro, CombineStatus, BuildUniqueOverallStatus,
Update_All_Operation_Mode_Status, and UpdateSubOperationHeatMap.
"""

import pandas as pd
from config import (
    AVL_THRESHOLD,
    BENCH_TOLERANCE,
    BENCH_SENTINEL,
    YELLOW_GROUP_THRESHOLD,
    AVL_ODRIV_MAPPING,
)

# Font-color RGB codes used for dot (●) cells in the Excel Sheet1.
# Format is "FFRRGGBB" (openpyxl includes the alpha prefix).
_DOT_COLOR_MAP = {
    "FF008000": "GREEN",   # dark green
    "FFFFFF00": "YELLOW",  # bright yellow
    "FFFF0000": "RED",     # bright red
    "FFFFFFFF": "N/A",     # white = no status
    "FF000000": "N/A",     # black text (sometimes in headers)
}


def parse_sheet1_data(text_input):
    """
    Parse tab-separated Sheet1 data pasted by the user.

    Expected format:
    Row 1: <empty> ... Drivability ... Responsiveness
    Row 2: <empty> ... Current Status ... VehicleA ... VehicleB ... Driv Lowest ... Current Status ... VehicleA ... VehicleB ... Resp Lowest
    Row 3: USE CASE ... P1 P2 P3 ... P1 P2 P3
    Row 4+: Section headers (bold) or data rows with:
      Col A: Section name (e.g., "Drive away") - for section headers
      Col B: Op Code (numeric) - for data rows
      Col C: Operation name
      Col E: Driv P1 dot color
      Col F: Driv P2 dot color
      Col G: Driv P3 dot color
      Col H: Driv Tested vehicle %
      Col I: Driv Target vehicle %
      Col J: Driv Lowest Events text
      Col K: Resp P1 dot color
      Col L: Resp P2 dot color
      Col M: Resp P3 dot color
      Col N: Resp Tested vehicle %
      Col O: Resp Target vehicle %
      Col P: Resp Lowest Events text

    Since we can't detect font colors from pasted text, we ask users to encode
    dot colors as G (green), Y (yellow), R (red), or leave blank for white/N/A.

    Args:
        text_input: Tab-separated text data

    Returns:
        dict with keys:
            'target_car': str
            'tested_car': str
            'sections': list of dicts with section info
            'operations': list of dicts with operation data
            'raw_df': pd.DataFrame
    """
    lines = [l for l in text_input.split("\n") if l.strip()]
    if len(lines) < 4:
        return None

    # Parse header rows
    row2_parts = lines[1].split("\t")

    # Find car names from row 2 (skip empty, "Current Status", "Lowest Events" etc.)
    car_names = []
    for part in row2_parts:
        part = part.strip()
        if part and "status" not in part.lower() and "lowest" not in part.lower() \
                and "p1" not in part.lower() and "p2" not in part.lower() \
                and "p3" not in part.lower() and "use case" not in part.lower():
            if part not in car_names:
                car_names.append(part)

    # Determine target and tested cars
    tested_car = car_names[0] if len(car_names) > 0 else "Tested Vehicle"
    target_car = car_names[1] if len(car_names) > 1 else "Target Vehicle"

    # Parse data rows (from row 4 onwards)
    sections = []
    operations = []
    current_section = None

    for line in lines[3:]:
        parts = line.split("\t")
        if not parts:
            continue

        # Pad parts to have at least 17 columns
        while len(parts) < 17:
            parts.append("")

        col_a = parts[0].strip()
        col_b = parts[1].strip()
        col_c = parts[2].strip()

        # Check if this is a section header (col_a has text, col_b is empty or non-numeric)
        is_section = False
        if col_a and not col_b:
            is_section = True
        elif col_a and col_b:
            try:
                int(col_b)
                is_section = False
            except ValueError:
                is_section = True

        if is_section:
            # Section header row
            section_data = {
                "name": col_a,
                "driv_tested_avg": _to_float(parts[7]),    # H
                "driv_target_avg": _to_float(parts[8]),     # I
                "resp_tested_avg": _to_float(parts[13]),    # N
                "resp_target_avg": _to_float(parts[14]),    # O
            }
            sections.append(section_data)
            current_section = col_a
        else:
            # Data row with operation
            try:
                op_code = int(col_b)
            except (ValueError, TypeError):
                continue

            op_name = col_c if col_c else ""

            op_data = {
                "section": current_section,
                "op_code": op_code,
                "operation": op_name,
                "driv_p1": _parse_dot_status(parts[4]),   # E
                "driv_p2": _parse_dot_status(parts[5]),   # F
                "driv_p3": _parse_dot_status(parts[6]),   # G
                "driv_tested": _to_float(parts[7]),        # H
                "driv_target": _to_float(parts[8]),        # I
                "resp_p1": _parse_dot_status(parts[10]),   # K
                "resp_p2": _parse_dot_status(parts[11]),   # L
                "resp_p3": _parse_dot_status(parts[12]),   # M
                "resp_tested": _to_float(parts[13]),       # N
                "resp_target": _to_float(parts[14]),       # O
            }
            operations.append(op_data)

    return {
        "target_car": target_car,
        "tested_car": tested_car,
        "sections": sections,
        "operations": operations,
    }


def parse_sheet1_from_excel(file_obj):
    """
    Parse Sheet1 directly from an uploaded Excel (.xlsx/.xlsm) file,
    extracting the actual font colors of the dot (●) characters so that
    users do not need to manually encode G/Y/R.

    The function reads the openpyxl workbook in read-only + data-only mode,
    walks the same row/column layout expected by ``parse_sheet1_data``, and
    translates each ``●`` cell's font-color RGB string into a status string
    via ``_DOT_COLOR_MAP``.

    Args:
        file_obj: A file-like object (e.g. ``st.file_uploader`` result) for
                  an .xlsx or .xlsm workbook that contains a sheet named
                  "Sheet1".

    Returns:
        Same dict as ``parse_sheet1_data`` on success, or ``None`` if the
        sheet cannot be found or parsed.
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_obj, data_only=True)
    if "Sheet1" not in wb.sheetnames:
        wb.close()
        return None

    ws = wb["Sheet1"]

    # --- Read header row 2 to find car names ---
    car_names = []
    skip_labels = {"current status", "lowest events", "drivability lowest events",
                   "responsiveness lowest events", "p1", "p2", "p3", "use case",
                   "drivability", "responsiveness", ""}
    for col_idx in range(1, ws.max_column + 1):
        val = ws.cell(row=2, column=col_idx).value
        if val is not None:
            val_str = str(val).strip()
            if val_str.lower() not in skip_labels and val_str not in car_names:
                car_names.append(val_str)

    tested_car = car_names[0] if len(car_names) > 0 else "Tested Vehicle"
    target_car = car_names[1] if len(car_names) > 1 else "Target Vehicle"

    # --- Helper: read dot color from a cell ---
    def _dot_status(cell):
        """Return GREEN / YELLOW / RED / N/A from a cell's font color."""
        val = cell.value
        if val is None:
            return "N/A"
        val_str = str(val).strip()
        # If the user typed G/Y/R instead of using dots, honour that too
        if val_str.upper() in ("G", "GREEN"):
            return "GREEN"
        if val_str.upper() in ("Y", "YELLOW"):
            return "YELLOW"
        if val_str.upper() in ("R", "RED"):
            return "RED"
        # Now try font-color on the ● character
        if val_str != "●":
            return "N/A"
        try:
            rgb = str(cell.font.color.rgb)
            return _DOT_COLOR_MAP.get(rgb, "N/A")
        except (AttributeError, TypeError):
            return "N/A"

    # --- Walk data rows (from row 4 onward, matching parse_sheet1_data) ---
    sections = []
    operations = []
    current_section = None

    for row_idx in range(4, ws.max_row + 1):
        col_a = ws.cell(row=row_idx, column=1).value  # section / empty
        col_b = ws.cell(row=row_idx, column=2).value  # op code
        col_c = ws.cell(row=row_idx, column=3).value  # op name

        col_a_str = str(col_a).strip() if col_a is not None else ""
        col_b_str = str(col_b).strip() if col_b is not None else ""

        # Detect section header vs data row
        is_section = False
        if col_a_str and not col_b_str:
            is_section = True
        elif col_a_str and col_b_str:
            try:
                int(col_b_str)
            except ValueError:
                is_section = True

        if is_section:
            h_val = ws.cell(row=row_idx, column=8).value   # H
            i_val = ws.cell(row=row_idx, column=9).value    # I
            n_val = ws.cell(row=row_idx, column=14).value   # N
            o_val = ws.cell(row=row_idx, column=15).value   # O
            section_data = {
                "name": col_a_str,
                "driv_tested_avg": _to_float(h_val),
                "driv_target_avg": _to_float(i_val),
                "resp_tested_avg": _to_float(n_val),
                "resp_target_avg": _to_float(o_val),
            }
            sections.append(section_data)
            current_section = col_a_str
            continue

        # Data row — op code must be numeric
        try:
            op_code = int(col_b_str)
        except (ValueError, TypeError):
            continue

        op_name = str(col_c).strip() if col_c else ""

        op_data = {
            "section": current_section,
            "op_code": op_code,
            "operation": op_name,
            "driv_p1": _dot_status(ws.cell(row=row_idx, column=5)),
            "driv_p2": _dot_status(ws.cell(row=row_idx, column=6)),
            "driv_p3": _dot_status(ws.cell(row=row_idx, column=7)),
            "driv_tested": _to_float(ws.cell(row=row_idx, column=8).value),
            "driv_target": _to_float(ws.cell(row=row_idx, column=9).value),
            "resp_p1": _dot_status(ws.cell(row=row_idx, column=11)),
            "resp_p2": _dot_status(ws.cell(row=row_idx, column=12)),
            "resp_p3": _dot_status(ws.cell(row=row_idx, column=13)),
            "resp_tested": _to_float(ws.cell(row=row_idx, column=14).value),
            "resp_target": _to_float(ws.cell(row=row_idx, column=15).value),
        }
        operations.append(op_data)

    wb.close()

    if not operations:
        return None

    return {
        "target_car": target_car,
        "tested_car": tested_car,
        "sections": sections,
        "operations": operations,
    }


def evaluate_avl_status(sheet1_data, heatmap_df, target_car, tested_car):
    """
    Main evaluation function.
    Corresponds to VBA EvaluateAVLStatus macro.

    Args:
        sheet1_data: dict from parse_sheet1_data()
        heatmap_df: DataFrame with heatmap data (must have tested vehicle column)
        target_car: name of target vehicle
        tested_car: name of tested vehicle

    Returns:
        pd.DataFrame with evaluation results
    """
    if sheet1_data is None:
        return pd.DataFrame()

    operations = sheet1_data["operations"]
    results = []

    for op in operations:
        op_code = op["op_code"]
        op_name = op["operation"]

        # Get tested AVL score from heatmap
        tested_avl = _get_tested_avl(heatmap_df, op_code, tested_car)

        # Get P1 statuses
        driv_p1 = op["driv_p1"]
        resp_p1 = op["resp_p1"]

        # Get benchmark values
        driv_target = op.get("driv_target", 0.0) or 0.0
        driv_tested = op.get("driv_tested", 0.0) or 0.0
        resp_target = op.get("resp_target", 0.0) or 0.0
        resp_tested = op.get("resp_tested", 0.0) or 0.0

        # Calculate benchmark differences
        driv_bench_diff = _bench_diff(driv_target, driv_tested)
        resp_bench_diff = _bench_diff(resp_target, resp_tested)

        # Evaluate statuses
        driv_status = _evaluate_status(tested_avl, driv_p1, driv_bench_diff,
                                        driv_target, driv_tested)
        resp_status = _evaluate_status(tested_avl, resp_p1, resp_bench_diff,
                                        resp_target, resp_tested)
        final_status = _combine_status(driv_status, resp_status)

        results.append({
            "Op Code": op_code,
            "Operation": op_name,
            "Tested AVL": tested_avl,
            "Driv P1": driv_p1,
            f"Driv Target ({target_car})": driv_target,
            f"Driv Tested ({tested_car})": driv_tested,
            "Driv Status": driv_status,
            "Resp P1": resp_p1,
            f"Resp Target ({target_car})": resp_target,
            f"Resp Tested ({tested_car})": resp_tested,
            "Resp Status": resp_status,
            "Final Status": final_status,
        })

    return pd.DataFrame(results)


def build_overall_status(eval_results_df):
    """
    Build "Overall Status by Op Code" summary.
    Corresponds to VBA BuildUniqueOverallStatus.

    Groups results by Op Code and determines overall status:
    - Any RED -> RED
    - All GREEN -> GREEN
    - Otherwise -> YELLOW
    - All N/A -> N/A

    Args:
        eval_results_df: DataFrame from evaluate_avl_status()

    Returns:
        pd.DataFrame with columns: Op Code, Operation, Overall Status
    """
    if eval_results_df.empty:
        return pd.DataFrame()

    summary = {}
    for _, row in eval_results_df.iterrows():
        code = str(row["Op Code"])
        status = str(row["Final Status"]).strip().upper()
        op_name = row["Operation"]

        if code not in summary:
            summary[code] = {"Operation": op_name, "statuses": []}
        summary[code]["statuses"].append(status)

    rows = []
    for code, info in summary.items():
        statuses = info["statuses"]
        valid = [s for s in statuses if s and s != "N/A"]

        if not valid:
            overall = "N/A"
        elif any(s == "RED" for s in valid):
            overall = "RED"
        elif all(s == "GREEN" for s in valid):
            overall = "GREEN"
        else:
            overall = "YELLOW"

        rows.append({
            "Op Code": code,
            "Operation": info["Operation"],
            "Overall Status": overall,
        })

    return pd.DataFrame(rows)


def calculate_group_status(operations, status_key="driv_p1"):
    """
    Calculate group-level status from sub-operation statuses.
    Corresponds to VBA Evaluate_Group_Status / Update_All_Operation_Mode_Status.

    Rules:
    - Any RED -> NOK (red)
    - >35% YELLOW -> Acceptable (yellow)
    - Otherwise -> OK (green)

    Args:
        operations: list of operation dicts
        status_key: which status field to use

    Returns:
        str: "NOK", "Acceptable", or "OK"
    """
    total = 0
    red_count = 0
    yellow_count = 0

    for op in operations:
        status = op.get(status_key, "").upper()
        if status in ("GREEN", "YELLOW", "RED"):
            total += 1
            if status == "RED":
                red_count += 1
            elif status == "YELLOW":
                yellow_count += 1

    if total == 0:
        return ""

    if red_count > 0:
        return "NOK"
    elif yellow_count / total > YELLOW_GROUP_THRESHOLD:
        return "Acceptable"
    else:
        return "OK"


def update_sub_operation_heatmap(heatmap_df, eval_results_df):
    """
    Update heatmap status column based on evaluation results.
    Corresponds to VBA UpdateSubOperationHeatMap.

    Args:
        heatmap_df: DataFrame with heatmap data
        eval_results_df: DataFrame from evaluate_avl_status()

    Returns:
        pd.DataFrame - heatmap with added 'Status' column
    """
    result = heatmap_df.copy()
    result["Status"] = ""

    if eval_results_df.empty:
        return result

    # Build dict of op_code -> overall status from eval results
    # Use the "Overall Status by Op Code" logic
    overall_df = build_overall_status(eval_results_df)
    status_dict = {}
    for _, row in overall_df.iterrows():
        status_dict[str(row["Op Code"])] = row["Overall Status"]

    # Apply to heatmap
    for idx, row in result.iterrows():
        op_code = str(row["Op Code"])
        if op_code in status_dict:
            result.at[idx, "Status"] = status_dict[op_code]

    return result


# ============================================================================
# Private Helper Functions
# ============================================================================

def _to_float(val):
    """Convert a value to float, returning 0.0 for non-numeric."""
    if val is None:
        return 0.0
    try:
        v = float(str(val).strip())
        return v
    except (ValueError, TypeError):
        return 0.0


def _parse_dot_status(val):
    """
    Parse a dot status value.
    Users encode as: G or GREEN, Y or YELLOW, R or RED, or leave blank for N/A.
    The bullet character '●' means there's a dot - but we need the color info.
    """
    if val is None:
        return "N/A"
    val = str(val).strip().upper()
    if not val or val == "●":
        # Can't determine color from plain text bullet
        return "N/A"
    if val in ("G", "GREEN"):
        return "GREEN"
    if val in ("Y", "YELLOW"):
        return "YELLOW"
    if val in ("R", "RED"):
        return "RED"
    return "N/A"


def _get_tested_avl(heatmap_df, op_code, tested_car_name):
    """
    Look up the tested AVL score from heatmap for a given op code.
    Corresponds to VBA GetTestedAVL.
    """
    if heatmap_df is None or heatmap_df.empty:
        return 0.0

    # Find the column for the tested vehicle
    avl_col = None
    for col in heatmap_df.columns:
        if col not in ("Op Code", "Operation Mode", "Status"):
            if tested_car_name and tested_car_name.lower() in col.lower():
                avl_col = col
                break

    # Fallback: use last vehicle column
    if avl_col is None:
        vehicle_cols = [c for c in heatmap_df.columns
                       if c not in ("Op Code", "Operation Mode", "Status")]
        if vehicle_cols:
            avl_col = vehicle_cols[-1]

    if avl_col is None:
        return 0.0

    # Find row by op code
    mask = heatmap_df["Op Code"] == op_code
    if mask.any():
        val = heatmap_df.loc[mask, avl_col].iloc[0]
        if val is not None and pd.notna(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

    return 0.0


def _bench_diff(target_val, tested_val):
    """
    Calculate benchmark difference.
    Returns BENCH_SENTINEL when target is zero or both are zero.
    Corresponds to VBA benchDiff.
    """
    if target_val == 0.0 and tested_val == 0.0:
        return BENCH_SENTINEL
    if target_val == 0.0:
        return BENCH_SENTINEL
    return abs(tested_val - target_val)


def _evaluate_status(avl, p1, bench_diff, target_val, tested_val):
    """
    Evaluate individual status using AVL score, P1 color and benchmark difference.
    Corresponds to VBA EvaluateStatus.

    Rules:
      1. P1 = N/A                               -> N/A
      2. AVL < 7  OR  P1 = RED                  -> RED
      3. AVL >= 7 AND P1 = YELLOW               -> YELLOW
      4. AVL >= 7 AND P1 = GREEN AND no bench   -> GREEN
      5. AVL >= 7 AND P1 = GREEN AND bench OK   -> GREEN
      6. AVL >= 7 AND P1 = GREEN AND bench fail -> YELLOW
    """
    p1_upper = p1.upper().strip() if p1 else "N/A"

    # Rule 1
    if p1_upper == "N/A":
        return "N/A"

    # Rule 2
    if avl < AVL_THRESHOLD or p1_upper == "RED":
        return "RED"

    # Rule 3
    if avl >= AVL_THRESHOLD and p1_upper == "YELLOW":
        return "YELLOW"

    # Below: AVL >= 7 AND P1 = GREEN

    # Rule 4: No benchmark data
    if bench_diff == BENCH_SENTINEL:
        return "GREEN"

    # Rule 5 & 6: Evaluate benchmark
    if tested_val >= target_val:
        return "GREEN"
    elif (target_val - tested_val) <= BENCH_TOLERANCE:
        return "GREEN"
    else:
        return "YELLOW"


def _combine_status(driv_status, resp_status):
    """
    Combine Drivability and Responsiveness statuses into Final Status.
    Corresponds to VBA CombineStatus.
    """
    driv = (driv_status or "N/A").upper().strip()
    resp = (resp_status or "N/A").upper().strip()

    # Either RED -> RED
    if driv == "RED" or resp == "RED":
        return "RED"

    # Either YELLOW -> YELLOW
    if driv == "YELLOW" or resp == "YELLOW":
        return "YELLOW"

    # Both GREEN -> GREEN
    if driv == "GREEN" and resp == "GREEN":
        return "GREEN"

    # One GREEN, one N/A -> GREEN
    if (driv == "GREEN" and resp == "N/A") or (driv == "N/A" and resp == "GREEN"):
        return "GREEN"

    # Both N/A -> N/A
    return "N/A"
