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
    PARENT_OPERATION_CODES,
    HEATMAP_OPERATION_CODES,
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

# Indexed-color map used by ODRIV RATING sheets (openpyxl COLOR_INDEX).
_INDEXED_DOT_MAP = {
    17: "GREEN",   # 00008000 - dark green
    11: "GREEN",   # 0000FF00 - bright green
    3:  "GREEN",   # 0000FF00 - bright green (alternate)
    10: "RED",     # 00FF0000 - red
    2:  "RED",     # 00FF0000 - red (alternate)
    13: "YELLOW",  # 00FFFF00 - yellow
    5:  "YELLOW",  # 00FFFF00 - yellow (alternate)
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


def parse_odriv_from_excel(file_obj):
    """
    Parse the RATING sheet from an AVL-ODRIV Excel (.xlsm) file.

    The ODRIV RATING sheet has a different layout from the Heatmap Tool's
    Sheet1.  This function reads the RATING sheet and produces the same
    output dict as ``parse_sheet1_from_excel`` so that the rest of the
    evaluation pipeline works unchanged.

    Layout (column numbers are 1-based):

    Row 2, col 4  : Tested vehicle (application) name
    Row 20        : "Drivability" / "Responsiveness" section labels
    Row 21        : Headers – "Current Status", vehicle names,
                    "Driveability Index", "Responsiveness Index",
                    "Drivability Lowest Events", "Responsiveness Lowest Events"
    Row 22        : Sub-headers – "USE CASE", "P1", "P2", "P3"
    Row 23+       : Data rows
        Section headers : col 2 has name, col 3 is empty
        Data rows       : col 3 has op-code, col 4 has op-name
                          Driv P1/P2/P3 dots at offsets from first
                          "Current Status", Resp P1/P2/P3 dots at second.
                          Driv tested % at "Driveability Index" col,
                          Resp tested % at "Responsiveness Index" col.
                          Target vehicle % at the column immediately before
                          "Drivability / Responsiveness Lowest Events".

    Dot colors are stored as *indexed* colors (openpyxl COLOR_INDEX).

    Args:
        file_obj: file-like object for an .xlsm workbook containing a
                  "RATING" sheet.

    Returns:
        Same dict as ``parse_sheet1_from_excel`` on success, or ``None``.
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_obj, data_only=False)
    if "RATING" not in wb.sheetnames:
        wb.close()
        return None

    ws = wb["RATING"]

    # --- Locate key columns by scanning the header row (row 21) ---
    driv_current_col = None   # first "Current Status" → Driv P1
    resp_current_col = None   # second "Current Status" → Resp P1
    driv_idx_col = None       # "Driveability Index" → tested driv %
    resp_idx_col = None       # "Responsiveness Index" → tested resp %
    driv_target_col = None    # col before "Drivability Lowest Events"
    resp_target_col = None    # col before "Responsiveness Lowest Events"

    for col_idx in range(1, ws.max_column + 1):
        val = ws.cell(row=21, column=col_idx).value
        if val is None:
            continue
        val_str = str(val).strip()
        val_lower = val_str.lower()

        if val_lower == "current status":
            if driv_current_col is None:
                driv_current_col = col_idx
            else:
                resp_current_col = col_idx

        if "driveability index" in val_lower or "drivability index" in val_lower:
            driv_idx_col = col_idx

        if "responsiveness index" in val_lower:
            resp_idx_col = col_idx

        if "drivability lowest" in val_lower or "driveability lowest" in val_lower:
            driv_target_col = col_idx - 1

        if "responsiveness lowest" in val_lower:
            resp_target_col = col_idx - 1

    # Fallback: if we couldn't find all required columns, bail out
    if driv_current_col is None:
        wb.close()
        return None

    # Derive P1/P2/P3 offsets (P1 is at the "Current Status" col itself,
    # P2 is +1, P3 is +2 – confirmed from row 22 sub-headers).
    driv_p1_col = driv_current_col
    driv_p2_col = driv_current_col + 1
    driv_p3_col = driv_current_col + 2

    resp_p1_col = resp_current_col if resp_current_col else None
    resp_p2_col = (resp_current_col + 1) if resp_current_col else None
    resp_p3_col = (resp_current_col + 2) if resp_current_col else None

    # --- Vehicle names ---
    # Row 2, col 4 often contains a formula (e.g. =HOME!Project); since we
    # load with data_only=False the formula string is returned.  Fall back to
    # reading the project name from the HOME sheet when available.
    raw_tested = ws.cell(row=2, column=4).value
    tested_car = ""
    if raw_tested is not None:
        tested_str = str(raw_tested).strip()
        if not tested_str.startswith("="):
            tested_car = tested_str
    if not tested_car and "HOME" in wb.sheetnames:
        home_val = wb["HOME"].cell(row=9, column=3).value
        if home_val:
            tested_car = str(home_val).strip()
    if not tested_car:
        tested_car = "Tested Vehicle"

    target_car = "Target Vehicle"
    if driv_target_col:
        t = ws.cell(row=21, column=driv_target_col).value
        if t:
            target_car = str(t).strip()

    # --- Helper: read dot color from a cell (indexed + rgb fallback) ---
    def _odriv_dot(cell):
        """Return GREEN / YELLOW / RED / N/A from a cell's font color."""
        val = cell.value
        if val is None:
            return "N/A"
        val_str = str(val).strip()
        if val_str.upper() in ("G", "GREEN"):
            return "GREEN"
        if val_str.upper() in ("Y", "YELLOW"):
            return "YELLOW"
        if val_str.upper() in ("R", "RED"):
            return "RED"
        if val_str != "●":
            return "N/A"
        try:
            fc = cell.font.color
            if fc is None:
                return "N/A"
            if fc.type == "indexed" and fc.indexed is not None:
                return _INDEXED_DOT_MAP.get(fc.indexed, "N/A")
            if fc.type == "rgb":
                rgb_str = str(fc.rgb)
                # Try the direct map first (FFRRGGBB)
                result = _DOT_COLOR_MAP.get(rgb_str)
                if result:
                    return result
                # Strip alpha and compare
                if len(rgb_str) == 8:
                    core = rgb_str[2:]
                    if core.upper() in ("008000", "00FF00"):
                        return "GREEN"
                    if core.upper() == "FF0000":
                        return "RED"
                    if core.upper() in ("FFFF00", "FFC000"):
                        return "YELLOW"
                    if core.upper() == "FFFFFF":
                        return "N/A"
                return "N/A"
        except (AttributeError, TypeError):
            pass
        return "N/A"

    # --- Walk data rows (starting from row 23 – right after the sub-header) ---
    # Find the first data row by looking for "USE CASE" in row 22
    data_start = 23
    for r in range(20, 30):
        cell_val = ws.cell(row=r, column=2).value
        if cell_val and "USE CASE" in str(cell_val).upper():
            data_start = r + 1
            break

    sections = []
    operations = []
    current_section = None

    for row_idx in range(data_start, ws.max_row + 1):
        col_b = ws.cell(row=row_idx, column=2).value   # section name
        col_c = ws.cell(row=row_idx, column=3).value   # op code
        col_d = ws.cell(row=row_idx, column=4).value   # op name

        col_b_str = str(col_b).strip() if col_b is not None else ""
        col_c_str = str(col_c).strip() if col_c is not None else ""
        col_d_str = str(col_d).strip() if col_d is not None else ""

        # Detect section header: col B has text but col C is empty
        is_section = bool(col_b_str and not col_c_str)

        if is_section:
            driv_tested_avg = _to_float(
                ws.cell(row=row_idx, column=driv_idx_col).value if driv_idx_col else None
            )
            driv_target_avg = _to_float(
                ws.cell(row=row_idx, column=driv_target_col).value if driv_target_col else None
            )
            resp_tested_avg = _to_float(
                ws.cell(row=row_idx, column=resp_idx_col).value if resp_idx_col else None
            )
            resp_target_avg = _to_float(
                ws.cell(row=row_idx, column=resp_target_col).value if resp_target_col else None
            )
            sections.append({
                "name": col_b_str,
                "driv_tested_avg": driv_tested_avg,
                "driv_target_avg": driv_target_avg,
                "resp_tested_avg": resp_tested_avg,
                "resp_target_avg": resp_target_avg,
            })
            current_section = col_b_str
            continue

        # Data row — need either an op code in col C or an op name in col D
        op_code = None
        if col_c_str:
            try:
                op_code = int(col_c_str)
            except (ValueError, TypeError):
                pass

        op_name = col_d_str

        # If no op code but we have an op name, try looking it up
        if op_code is None and op_name:
            op_code = AVL_ODRIV_MAPPING.get(op_name)

        if op_code is None and not op_name:
            # Empty / unrecognised row — skip
            continue

        if op_code is None:
            # Op name present but no code — still include with code 0
            op_code = 0

        op_data = {
            "section": current_section,
            "op_code": op_code,
            "operation": op_name,
            "driv_p1": _odriv_dot(ws.cell(row=row_idx, column=driv_p1_col)),
            "driv_p2": _odriv_dot(ws.cell(row=row_idx, column=driv_p2_col)),
            "driv_p3": _odriv_dot(ws.cell(row=row_idx, column=driv_p3_col)),
            "driv_tested": _to_float(
                ws.cell(row=row_idx, column=driv_idx_col).value if driv_idx_col else None
            ),
            "driv_target": _to_float(
                ws.cell(row=row_idx, column=driv_target_col).value if driv_target_col else None
            ),
            "resp_p1": _odriv_dot(ws.cell(row=row_idx, column=resp_p1_col)) if resp_p1_col else "N/A",
            "resp_p2": _odriv_dot(ws.cell(row=row_idx, column=resp_p2_col)) if resp_p2_col else "N/A",
            "resp_p3": _odriv_dot(ws.cell(row=row_idx, column=resp_p3_col)) if resp_p3_col else "N/A",
            "resp_tested": _to_float(
                ws.cell(row=row_idx, column=resp_idx_col).value if resp_idx_col else None
            ),
            "resp_target": _to_float(
                ws.cell(row=row_idx, column=resp_target_col).value if resp_target_col else None
            ),
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
    Corresponds to VBA UpdateSubOperationHeatMap + Update_All_Operation_Mode_Status.

    Sub-operation rows get a status of GREEN / YELLOW / RED (displayed as
    colored dots in the UI).  Parent (group header) rows get an aggregate
    status of OK / Acceptable / NOK using the same logic as
    ``calculate_group_status``.

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
    overall_df = build_overall_status(eval_results_df)
    status_dict = {}
    for _, row in overall_df.iterrows():
        status_dict[str(row["Op Code"])] = row["Overall Status"]

    # Apply sub-operation statuses
    for idx, row in result.iterrows():
        op_code = str(row["Op Code"])
        if op_code in status_dict:
            result.at[idx, "Status"] = status_dict[op_code]

    # --- Compute parent (group header) statuses ---
    # Walk the heatmap in order; each parent row owns the sub-operation rows
    # that follow it until the next parent row.
    op_codes_in_order = result["Op Code"].tolist()
    parent_indices = []
    for idx, code in enumerate(op_codes_in_order):
        if code in PARENT_OPERATION_CODES:
            parent_indices.append(idx)

    for pi, parent_idx in enumerate(parent_indices):
        # Children span from the row after this parent to just before the next
        # parent (or end of table).
        child_start = parent_idx + 1
        child_end = (
            parent_indices[pi + 1] if pi + 1 < len(parent_indices)
            else len(op_codes_in_order)
        )
        # Build a list of pseudo-operation dicts so we can reuse
        # calculate_group_status with the "final_status" key.
        child_ops = []
        for ci in range(child_start, child_end):
            s = str(result.iat[ci, result.columns.get_loc("Status")]).upper()
            if s in ("GREEN", "YELLOW", "RED"):
                child_ops.append({"final_status": s})

        group_status = calculate_group_status(child_ops, "final_status")
        if group_status:
            result.iat[parent_idx, result.columns.get_loc("Status")] = group_status

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


# ============================================================================
# ODRIV Detail Sheet Parsing & Auto-Comment Generation
# ============================================================================

# Sheets in the ODRIV workbook that are *not* operation-detail sheets.
_SKIP_DETAIL_SHEETS = {
    "RATING", "HOME", "Sheet1", "Mapping Sheet", "HeatMap Sheet",
    "HeatMap Template", "Data Transfer Sheet", "AVL-Odriv Mapping",
    "Evaluation Results", "Lists", "HOME ", "Info", "Configuration",
    # ODRIV v29+ internal sheets
    "Résultats", "ANNEECONFIG", "DATA", "GRILLE", "Palette",
    "DBStructure", "Graph_status", "Calculs", "POWERTRAIN",
    "CONFIGURATIONS SEETINGS", "CONFIGURATIONS ARRAY", "UTILISATEURS",
    "SETTINGS", "TARGET VEHICLE", "CONFIGURATIONS", "ENTETE_COLONNE",
    "PARAMETRES GRAPH", "CFG", "totalPoint", "cfg_criticity",
    "DEFINITION SDV", "SDV MANAGER", "VERSIONS", "GRAPHIQUES",
    "VIERGE", "TARGETS", "structure", "DNT", "DocVersions",
}


def _find_resp_section_start(ws, max_scan_row=10):
    """Return the column index where the Responsiveness section starts.

    ODRIV v29+ detail sheets contain two side-by-side regions:
    * **Drivability** (left, typically cols 1-50)
    * **Responsiveness** (right, typically starting around col 60)

    The Responsiveness section is identified by a cell containing
    ``"RESPONSIVENESS SUMMARY"`` in the first few rows.  Returns the column
    of that cell, or ``None`` if the sheet has no Responsiveness section.
    """
    max_col = min(ws.max_column or 1, 200)
    for row_idx in range(1, max_scan_row + 1):
        for col_idx in range(1, max_col + 1):
            v = ws.cell(row=row_idx, column=col_idx).value
            if v and "responsiveness summary" in str(v).lower():
                return col_idx
    return None


def parse_odriv_detail_sheets(file_obj):
    """Parse event-level data from ODRIV operation-detail sub-sheets.

    Each sub-sheet in the ODRIV workbook (other than RATING, HOME, etc.)
    contains detailed event/criteria evaluations for a specific operation
    mode.  The function scans each sheet for a header row containing columns
    like ``Priority``, ``Event Rating``, ``Value``, ``File``, ``Criteria``,
    and reads the data rows below.

    ODRIV v29+ sheets contain **two side-by-side sections**: Drivability
    (left) and Responsiveness (right).  Both are parsed separately.
    Responsiveness events are stored under the key
    ``"<sheet_name>__resp"``.

    Args:
        file_obj: file-like object for an .xlsm workbook.

    Returns:
        dict: ``{sheet_name: [event_dict, ...]}`` where *event_dict* has
        keys ``file``, ``criteria``, ``priority``, ``rating``, ``value``.
        Responsiveness sections use key ``"<sheet_name>__resp"``.
        Only sheets where at least one event was successfully parsed are
        included.
    """
    import openpyxl

    wb = openpyxl.load_workbook(file_obj, data_only=True)

    result = {}
    for sheet_name in wb.sheetnames:
        if sheet_name.strip() in _SKIP_DETAIL_SHEETS:
            continue
        ws = wb[sheet_name]

        # Detect Responsiveness section boundary so we can parse each
        # half independently and avoid mixing up columns.
        resp_start = _find_resp_section_start(ws)

        # Parse the Drivability section (left side).
        driv_col_end = (resp_start - 1) if resp_start else None
        events = _parse_detail_sheet(ws, col_end=driv_col_end)
        if events:
            result[sheet_name] = events

        # Parse the Responsiveness section (right side) if it exists.
        if resp_start:
            resp_events = _parse_detail_sheet(ws, col_start=resp_start)
            if resp_events:
                result[f"{sheet_name}__resp"] = resp_events

    wb.close()
    return result


# RGB values that should be treated as "no color" even when patternType
# is ``solid`` (white / fully transparent).
_UNCOLORED_RGBS = frozenset({"00000000", "FFFFFFFF"})


def _cell_has_color_fill(cell):
    """Return ``True`` if *cell* has a visible background fill color.

    ODRIV detail sheets color rated-criteria cells (red / yellow / green)
    while leaving input-parameter cells uncolored.  This function detects
    whether a cell has a meaningful (non-white, non-transparent) solid fill.
    """
    fill = cell.fill
    if fill.patternType != "solid":
        return False
    fg = fill.fgColor
    if fg is None:
        return False
    if fg.type == "rgb" and fg.rgb:
        return str(fg.rgb) not in _UNCOLORED_RGBS
    if fg.type == "indexed" and fg.indexed is not None:
        # Indexed colors 0 (black) and 64 (system window bg / white) are
        # not meaningful rating colors.
        return fg.indexed not in (0, 64)
    if fg.type == "theme" and fg.theme is not None:
        # Theme color 0 is usually white in standard Office themes.
        return fg.theme != 0
    return False


def _parse_detail_sheet(ws, col_start=1, col_end=None):
    """Parse a single ODRIV detail sheet and return a list of event dicts.

    Supports two layout formats:

    **Narrow format** (simple):  Explicit ``Criteria``, ``Value`` columns –
    each row describes one criteria evaluation.

    **Wide format** (ODRIV v29+):  Individual criteria names are *column
    headers* (e.g. ``Brake release bump``, ``Acceleration disturbances``)
    and each data row contains scores for all criteria.  The parser detects
    this when it finds ``Event Priority`` + ``Event Rating`` headers but no
    single ``Criteria`` / ``Value`` column, and then identifies the criteria
    score columns automatically.

    Args:
        ws: openpyxl worksheet object.
        col_start: first column index to scan (default 1).
        col_end: last column index to scan (inclusive).  When ``None``,
                 defaults to ``min(ws.max_column, 200)``.
    """
    # ------------------------------------------------------------------
    # Phase 1: locate the header row
    # ------------------------------------------------------------------
    # Keyword families for explicit (narrow-format) columns.
    # Order matters: more specific keys are matched first so that
    # "Event Rating" is not captured by the "event" keyword in criteria.
    # Each entry is (key, include_keywords, exclude_keywords).
    _HEADER_KEYWORDS_ORDERED = [
        ("rating", ("event rating", "event_rating", "eventrating", "rating"), ()),
        ("priority", ("priority", "prio"), ()),
        ("file", ("file", "measurement", "filename", "file name",
                  "acquisition name", "acquisition"), ()),
        ("value", ("value", "score", "event value", "dr"), ()),
        ("criteria", ("criteria", "criterion", "event name", "event"),
                     ("start time", "sub event")),
    ]

    # Column headers that should never be treated as criteria score
    # columns in the wide-format detection.
    _NON_CRITERIA_HEADERS = (
        "start time", "indice", "id bdd", "id_bdd",
        "criticality", "selector", "throttle",
        "speed", "em speed", "pedal change", "ax max",
        "acquisition", "event priority", "event rating",
    )

    header_row = None
    col_map = {}
    row_vals_at_header = {}

    max_scan_row = min(ws.max_row or 1, 25)
    max_scan_col = min(col_end or (ws.max_column or 1), 200)

    for row_idx in range(1, max_scan_row + 1):
        row_vals = {}
        for col_idx in range(col_start, max_scan_col + 1):
            cell_val = ws.cell(row=row_idx, column=col_idx).value
            if cell_val is not None:
                row_vals[col_idx] = str(cell_val).strip().lower()

        matches = {}
        claimed_cols = set()
        for key, keywords, excludes in _HEADER_KEYWORDS_ORDERED:
            for col_idx, val in row_vals.items():
                if col_idx in claimed_cols:
                    continue
                if any(ex in val for ex in excludes):
                    continue
                if any(kw in val for kw in keywords):
                    if key not in matches:
                        matches[key] = col_idx
                        claimed_cols.add(col_idx)
                        break

        # Accept the row as a header if it contains at least 3 keyword
        # matches (narrow format) or at least priority + rating (wide).
        if len(matches) >= 3:
            header_row = row_idx
            col_map = matches
            row_vals_at_header = row_vals
            break
        if len(matches) >= 2 and "priority" in matches and "rating" in matches:
            header_row = row_idx
            col_map = matches
            row_vals_at_header = row_vals
            break

    if header_row is None:
        return []

    # ------------------------------------------------------------------
    # Phase 2: detect wide-format criteria columns if needed
    # ------------------------------------------------------------------
    # Wide format is used when we found priority + rating but there is no
    # explicit "criteria" or "value" column.
    wide_criteria_cols = {}  # {col_idx: header_text}
    is_wide = "criteria" not in col_map or "value" not in col_map

    if is_wide and header_row < (ws.max_row or header_row):
        claimed = set(col_map.values())
        for col_idx, header_text in row_vals_at_header.items():
            if col_idx in claimed:
                continue
            if not header_text:
                continue
            # Skip known non-criteria columns.
            if any(nc in header_text for nc in _NON_CRITERIA_HEADERS):
                continue
            # Peek at the first data row: if the cell is numeric, this
            # column is a candidate criteria score column.
            peek_val = ws.cell(row=header_row + 1, column=col_idx).value
            if peek_val is not None:
                try:
                    float(str(peek_val))
                    raw = ws.cell(row=header_row, column=col_idx).value
                    wide_criteria_cols[col_idx] = str(raw).strip() if raw else header_text
                except (ValueError, TypeError):
                    pass

    # ------------------------------------------------------------------
    # Phase 3: read data rows
    # ------------------------------------------------------------------
    events = []
    for row_idx in range(header_row + 1, (ws.max_row or header_row) + 1):
        event = {}

        # --- file ---
        if "file" in col_map:
            v = ws.cell(row=row_idx, column=col_map["file"]).value
            event["file"] = str(v).strip() if v else ""
        else:
            event["file"] = ""

        # --- priority ---
        if "priority" in col_map:
            v = ws.cell(row=row_idx, column=col_map["priority"]).value
            try:
                event["priority"] = int(float(str(v)))
            except (ValueError, TypeError):
                event["priority"] = 0
        else:
            event["priority"] = 0

        # --- rating ---
        if "rating" in col_map:
            v = ws.cell(row=row_idx, column=col_map["rating"]).value
            event["rating"] = str(v).strip() if v else ""
        else:
            event["rating"] = ""

        # --- criteria & value ---
        if is_wide and wide_criteria_cols:
            # Wide format: find the criteria column with the lowest numeric
            # score in this row, considering **only** cells that have a
            # coloured background fill (red / yellow / green).  Uncoloured
            # cells are input parameters, not rated criteria.
            best_col = None
            best_val = None
            for c_col in wide_criteria_cols:
                cell = ws.cell(row=row_idx, column=c_col)
                cv = cell.value
                if cv is None:
                    continue
                try:
                    fv = float(str(cv))
                except (ValueError, TypeError):
                    continue
                # Only consider cells with a meaningful fill colour.
                if not _cell_has_color_fill(cell):
                    continue
                if best_val is None or fv < best_val:
                    best_val = fv
                    best_col = c_col
            event["criteria"] = wide_criteria_cols.get(best_col, "") if best_col else ""
            event["value"] = best_val
        else:
            # Narrow format: explicit criteria / value columns.
            if "criteria" in col_map:
                v = ws.cell(row=row_idx, column=col_map["criteria"]).value
                event["criteria"] = str(v).strip() if v else ""
            else:
                event["criteria"] = ""

            if "value" in col_map:
                v = ws.cell(row=row_idx, column=col_map["value"]).value
                try:
                    event["value"] = float(str(v))
                except (ValueError, TypeError):
                    event["value"] = None
            else:
                event["value"] = None

        # Skip empty / header-echo rows.
        if not event["criteria"] and not event["file"] and event["priority"] == 0:
            continue

        events.append(event)

    return events


def _normalize_for_match(s):
    """Lower-case a string and strip spaces, hyphens, underscores."""
    return s.lower().replace(" ", "").replace("-", "").replace("_", "")


# Common abbreviations used in ODRIV sheet names.
_ABBREVIATION_MAP = {
    "cst": "constant",
    "decel": "deceleration",
    "accel": "acceleration",
    "da": "driveaway",
}


def _expand_abbreviations(text):
    """Expand common ODRIV abbreviations (e.g. ``Cst`` → ``Constant``)."""
    words = text.lower().replace("-", " ").replace("_", " ").split()
    expanded = [_ABBREVIATION_MAP.get(w, w) for w in words]
    return "".join(expanded)


def _match_sheet_to_operation(sheet_names, section, op_name):
    """Find the best-matching detail sheet name for *section* + *op_name*.

    Tries exact match first (e.g. ``"Driveaway-Creep"`` for section
    ``"Drive away"`` and operation ``"Creep"``), then progressively
    fuzzier matching, including expanding common abbreviations.

    Returns the matching sheet name, or ``None``.
    """
    if not sheet_names:
        return None

    candidates = []
    if section and op_name:
        candidates.append(f"{section}-{op_name}")
        candidates.append(f"{section}_{op_name}")
        candidates.append(f"{section} {op_name}")
        short_section = section.replace(" ", "")
        candidates.append(f"{short_section}-{op_name}")
        candidates.append(f"{short_section}_{op_name}")
    if op_name:
        candidates.append(op_name)

    # 1) Exact normalized match.
    for sheet in sheet_names:
        ns = _normalize_for_match(sheet)
        for cand in candidates:
            if _normalize_for_match(cand) == ns:
                return sheet

    # 2) Sheet name contains both section and operation.
    if section and op_name:
        norm_sec = _normalize_for_match(section)
        norm_op = _normalize_for_match(op_name)
        for sheet in sheet_names:
            ns = _normalize_for_match(sheet)
            if norm_sec in ns and norm_op in ns:
                return sheet

    # 3) Sheet name contains just the operation name.
    if op_name:
        norm_op = _normalize_for_match(op_name)
        for sheet in sheet_names:
            if norm_op in _normalize_for_match(sheet):
                return sheet

    # 4) Abbreviation-expanded matching (e.g. "Cst" → "Constant").
    for sheet in sheet_names:
        es = _expand_abbreviations(sheet)
        for cand in candidates:
            if _expand_abbreviations(cand) == es:
                return sheet

    # 5) Abbreviation-expanded containment of section + operation.
    if section and op_name:
        exp_sec = _expand_abbreviations(section)
        exp_op = _expand_abbreviations(op_name)
        for sheet in sheet_names:
            es = _expand_abbreviations(sheet)
            if exp_sec in es and exp_op in es:
                return sheet

    # 6) Abbreviation-expanded containment of just the operation name.
    #    Also strip "/" from op names like "At constant speed / acceleration".
    #    Prefer sheets that also contain the section when available.
    if op_name:
        clean_op = op_name.split("/")[0].strip()
        exp_op = _expand_abbreviations(clean_op)
        # First try matching with section constraint.
        if section:
            exp_sec = _expand_abbreviations(section)
            for sheet in sheet_names:
                es = _expand_abbreviations(sheet)
                if exp_sec in es and exp_op in es:
                    return sheet
        # Then fall back to just the operation name.
        for sheet in sheet_names:
            if exp_op in _expand_abbreviations(sheet):
                return sheet

    return None


def _extract_file_prefix(file_name):
    """Extract the test-condition prefix from a measurement file name.

    AVL-DRIVE file names typically follow the pattern::

        {TestCondition}_{DriveMode}_{Standard}_{VehicleName}_{ID}_{Source}

    e.g. ``GS-RL_0%_Normal_Standard_BYD_Dolphin_Surf_BEV001_inca``
    → returns ``GS_RL_0%``.

    The heuristic splits on ``_`` and stops at common keywords.
    """
    if not file_name:
        return ""

    # Normalise hyphens to underscores for consistency.
    cleaned = file_name.replace("-", "_")
    parts = cleaned.split("_")

    stop_words = {
        "normal", "cold", "hot", "standard", "sport", "eco",
        "comfort", "byd", "bmw", "vw", "audi", "mercedes",
        "porsche", "toyota", "honda", "ford", "inca", "concerto",
    }

    prefix_parts = []
    for part in parts:
        if part.lower() in stop_words:
            break
        prefix_parts.append(part)

    if prefix_parts:
        return "_".join(prefix_parts)
    if parts:
        return parts[0]
    return ""


def generate_red_comments(sheet1_data, heatmap_df, odriv_details):
    """Auto-generate comments for sub-operations that have RED dot status.

    For each sub-operation with RED P1 (Drivability or Responsiveness),
    the function finds the corresponding ODRIV detail sheet, filters for
    RED/Red+ P1 events, picks the one with the lowest score, and builds
    a comment string.

    When the RED reason is **Responsiveness**, the function looks for a
    ``"<sheet>__resp"`` key in *odriv_details* (the Responsiveness section
    of the same sheet) and uses those events.  When the reason is
    **Drivability**, the base ``"<sheet>"`` key is used.

    Comment format::

        Red P1 Drivability, {Criteria}, {FilePrefix}

    Args:
        sheet1_data: dict produced by ``parse_sheet1_data`` /
                     ``parse_odriv_from_excel`` (must contain
                     ``operations``).
        heatmap_df:  DataFrame that already has a ``Status`` column
                     (from ``update_sub_operation_heatmap``).
        odriv_details: dict from ``parse_odriv_detail_sheets``.

    Returns:
        dict:  ``{op_code: comment_string}``  — only entries for ops
        where a comment could be generated.
    """
    if not sheet1_data or not odriv_details:
        return {}

    operations = sheet1_data.get("operations", [])
    # Build separate lists: base sheet names (Drivability) and resp names.
    base_sheet_names = [
        k for k in odriv_details.keys() if not k.endswith("__resp")
    ]
    comments = {}

    for op in operations:
        op_code = op.get("op_code")
        driv_p1 = op.get("driv_p1", "N/A").upper()
        resp_p1 = op.get("resp_p1", "N/A").upper()
        section = op.get("section", "") or ""
        op_name = op.get("operation", "") or ""

        # Only generate for operations where P1 is RED.
        if driv_p1 != "RED" and resp_p1 != "RED":
            continue

        # Find the matching detail sheet (base Drivability name).
        matched_sheet = _match_sheet_to_operation(
            base_sheet_names, section, op_name
        )

        # Collect comment parts for each RED reason.
        all_parts = []

        for reason, is_red, detail_key in [
            ("Red P1 Drivability", driv_p1 == "RED",
             matched_sheet),
            ("Red P1 Responsiveness", resp_p1 == "RED",
             f"{matched_sheet}__resp" if matched_sheet else None),
        ]:
            if not is_red:
                continue

            parts = [reason]

            # Try to enrich with criteria/file from the detail events.
            events = odriv_details.get(detail_key, []) if detail_key else []
            red_p1_events = [
                e for e in events
                if e.get("priority") == 1
                and str(e.get("rating", "")).lower().startswith("red")
                and e.get("value") is not None
            ]
            if red_p1_events:
                lowest = min(red_p1_events, key=lambda e: e["value"])
                criteria = lowest.get("criteria", "")
                file_prefix = _extract_file_prefix(lowest.get("file", ""))
                if criteria:
                    parts.append(criteria)
                if file_prefix:
                    parts.append(file_prefix)

            all_parts.append(", ".join(parts))

        comments[op_code] = " | ".join(all_parts)

    return comments
