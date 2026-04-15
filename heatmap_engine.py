"""
Heatmap Engine - Handles the HeatMap Sheet logic.
Corresponds to the VBA RefreshHeatmap macro and related functions.
"""

import pandas as pd
from config import OPERATION_MODE_MAPPING, HEATMAP_OPERATION_CODES


def build_heatmap_template():
    """
    Build an empty heatmap DataFrame with all operation modes.
    Corresponds to the HeatMap Sheet structure.

    Returns:
        pd.DataFrame with columns: Op Code, Operation Mode
    """
    rows = []
    for code in HEATMAP_OPERATION_CODES:
        name = OPERATION_MODE_MAPPING.get(code, f"Unknown ({code})")
        rows.append({"Op Code": code, "Operation Mode": name})
    return pd.DataFrame(rows)


def parse_heatmap_data(text_input):
    """
    Parse tab-separated heatmap data pasted by the user.
    Expected format (from Data Transfer Sheet or HeatMap Sheet):
      - Header row with vehicle names
      - Sub-header row with 'DR' markers
      - Data rows: OpCode | OperationMode | Vehicle1_Score | Vehicle2_Score | ...

    Args:
        text_input: Tab-separated text data

    Returns:
        dict with keys:
            'vehicle_names': list of vehicle names
            'data': pd.DataFrame with columns [Op Code, Operation Mode, Vehicle1, Vehicle2, ...]
    """
    lines = [l for l in text_input.strip().split("\n") if l.strip()]
    if not lines:
        return None

    # Try to parse as structured data
    # First line could be headers with vehicle names
    # Second line could be DR markers
    # Remaining lines are data

    header_parts = lines[0].split("\t")

    # Check if first data column looks like a number (op code)
    # If so, no header row - all data
    first_data_line = None
    vehicle_names = []
    data_start = 0

    # Try to detect if first line is a header
    try:
        int(header_parts[0].strip())
        # First column is numeric - no header, treat as data
        data_start = 0
        vehicle_names = [f"Vehicle {i+1}" for i in range(len(header_parts) - 2)]
    except (ValueError, IndexError):
        # First line has non-numeric first column - could be header
        # Look for vehicle names (skip empty and "Operation Modes" type headers)
        for part in header_parts:
            part = part.strip()
            if part and part.lower() not in ("", "operation modes", "dr"):
                vehicle_names.append(part)

        # Check if second line is DR markers
        if len(lines) > 1:
            second_parts = lines[1].split("\t")
            has_dr = any("dr" in p.strip().lower() for p in second_parts if p.strip())
            if has_dr:
                data_start = 2
            else:
                data_start = 1

    # Parse data rows
    data_rows = []
    for line in lines[data_start:]:
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        try:
            op_code = int(parts[0].strip())
        except (ValueError, IndexError):
            continue

        op_name = parts[1].strip() if len(parts) > 1 else ""

        scores = []
        for i in range(2, len(parts)):
            val = parts[i].strip()
            try:
                scores.append(float(val))
            except (ValueError, TypeError):
                scores.append(None)

        row = {"Op Code": op_code, "Operation Mode": op_name}
        for j, score in enumerate(scores):
            if j < len(vehicle_names):
                row[vehicle_names[j]] = score
            else:
                row[f"Vehicle {j+1}"] = score

        data_rows.append(row)

    if not data_rows:
        return None

    df = pd.DataFrame(data_rows)

    # Update vehicle names if we auto-generated them
    actual_vehicle_cols = [c for c in df.columns if c not in ("Op Code", "Operation Mode")]
    if not vehicle_names:
        vehicle_names = actual_vehicle_cols

    return {
        "vehicle_names": vehicle_names,
        "data": df,
    }


def refresh_heatmap(template_df, source_data):
    """
    Transfer data from source (Data Transfer Sheet) to heatmap template.
    Corresponds to the VBA RefreshHeatmap macro.

    Args:
        template_df: DataFrame from build_heatmap_template()
        source_data: dict from parse_heatmap_data() with vehicle data

    Returns:
        pd.DataFrame - filled heatmap with vehicle scores
    """
    if source_data is None:
        return template_df

    source_df = source_data["data"]
    vehicle_names = source_data["vehicle_names"]

    # Build mode indices from source: by op code and by name (case-insensitive)
    code_index = {}
    name_index = {}
    for _, row in source_df.iterrows():
        op_code = row.get("Op Code")
        op_name = str(row.get("Operation Mode", "")).strip()
        if op_code is not None and op_code not in code_index:
            code_index[op_code] = row
        if op_name:
            name_lower = op_name.lower()
            if name_lower not in name_index:
                name_index[name_lower] = row

    # Fill template
    result = template_df.copy()
    for vname in vehicle_names:
        result[vname] = None

    for idx, row in result.iterrows():
        op_code = row["Op Code"]
        op_name = row["Operation Mode"]

        # Match by op code first, then by name (case-insensitive)
        src_row = code_index.get(op_code)
        if src_row is None and op_name:
            src_row = name_index.get(op_name.lower())

        if src_row is not None:
            for vname in vehicle_names:
                if vname in src_row.index:
                    val = src_row[vname]
                    if val is not None and pd.notna(val):
                        try:
                            val = float(val)
                            if val > 0:
                                result.at[idx, vname] = val
                        except (ValueError, TypeError):
                            pass

    return result


def filter_heatmap_rows(heatmap_df, tested_vehicle_col=None):
    """
    Filter heatmap rows: hide rows where the tested vehicle has no data.
    Corresponds to HideRowsMissingLastVehicle VBA.

    Args:
        heatmap_df: DataFrame from refresh_heatmap()
        tested_vehicle_col: column name of the tested vehicle (last vehicle)

    Returns:
        pd.DataFrame with only rows that have data for the tested vehicle
    """
    if tested_vehicle_col is None or tested_vehicle_col not in heatmap_df.columns:
        return heatmap_df

    mask = heatmap_df[tested_vehicle_col].notna() & (heatmap_df[tested_vehicle_col] > 0)
    return heatmap_df[mask].reset_index(drop=True)
