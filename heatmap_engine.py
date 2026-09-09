"""
Heatmap Engine - Handles the HeatMap Sheet logic.
Corresponds to the VBA RefreshHeatmap macro and related functions.
"""

import pandas as pd
from config import (
    OPERATION_MODE_MAPPING,
    HEATMAP_OPERATION_CODES,
    HEATMAP_OPERATION_LABELS,
)


def apply_heatmap_display_labels(df):
    """Apply HeatMap-tab-only operation names; leaves other pages unchanged."""
    if df is None or df.empty or "Op Code" not in df.columns:
        return df
    result = df.copy()
    for idx, row in result.iterrows():
        op_code = row["Op Code"]
        if op_code in HEATMAP_OPERATION_LABELS:
            result.at[idx, "Operation Mode"] = HEATMAP_OPERATION_LABELS[op_code]
    return result


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
      - Header row with vehicle names (may have empty separator columns)
      - Sub-header row with 'DR' markers (may have empty separator columns)
      - Data rows: OpCode | OperationMode | Vehicle1_Score | (sep) | Vehicle2_Score | ...

    The Excel Data Transfer Sheet often has empty separator columns between
    vehicle data columns. This parser detects them and maps scores to the
    correct vehicles using column positions from the header row.

    Args:
        text_input: Tab-separated text data

    Returns:
        dict with keys:
            'vehicle_names': list of vehicle names
            'data': pd.DataFrame with columns [Op Code, Operation Mode, Vehicle1, Vehicle2, ...]
    """
    lines = [l for l in text_input.split("\n") if l.strip()]
    if not lines:
        return None

    header_parts = lines[0].split("\t")

    vehicle_names = []
    # Column indices (0-based) in the raw tab-split that hold vehicle data
    vehicle_col_indices = []
    data_start = 0

    # Try to detect if the first line is a header or already data
    try:
        int(header_parts[0].strip())
        # First column is numeric — no header row, all lines are data.
        # Use DR row detection or fall back to treating every column as a
        # vehicle column.
        data_start = 0
        # Assume columns 2..end are all scores (no separator info available)
        vehicle_col_indices = list(range(2, len(header_parts)))
        vehicle_names = [f"Vehicle {i+1}" for i in range(len(vehicle_col_indices))]
    except (ValueError, IndexError):
        # First line is a header — extract vehicle names *and* their column
        # positions so we can skip separator columns in data rows.
        skip_labels = {"", "operation modes", "dr", "status", "comments"}
        for col_idx, part in enumerate(header_parts):
            part_stripped = part.strip()
            if col_idx < 2:
                # Columns 0–1 are Op Code / Operation Mode — never vehicles
                continue
            if part_stripped and part_stripped.lower() not in skip_labels:
                vehicle_names.append(part_stripped)
                vehicle_col_indices.append(col_idx)

        # Check if the second line carries DR markers
        if len(lines) > 1:
            second_parts = lines[1].split("\t")
            has_dr = any(
                "dr" in p.strip().lower() for p in second_parts if p.strip()
            )
            if has_dr:
                data_start = 2
                # If no vehicle names were found from the header row, derive
                # them from DR-marker positions instead.
                if not vehicle_names:
                    for col_idx, p in enumerate(second_parts):
                        if col_idx >= 2 and p.strip().upper().startswith("DR"):
                            vehicle_col_indices.append(col_idx)
                            vehicle_names.append(f"Vehicle {len(vehicle_names)+1}")
            else:
                data_start = 1

    # Fallback: if we still have no vehicle columns, treat everything from
    # column 2 onward as vehicle data (original behaviour).
    if not vehicle_col_indices:
        # Peek at the first data line to determine column count
        if data_start < len(lines):
            n_cols = len(lines[data_start].split("\t"))
            vehicle_col_indices = list(range(2, n_cols))
            vehicle_names = [f"Vehicle {i+1}" for i in range(len(vehicle_col_indices))]

    # Parse data rows — only pull scores from vehicle_col_indices
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

        row = {"Op Code": op_code, "Operation Mode": op_name}
        for j, col_idx in enumerate(vehicle_col_indices):
            if col_idx < len(parts):
                val = parts[col_idx].strip()
                try:
                    row[vehicle_names[j]] = float(val)
                except (ValueError, TypeError):
                    row[vehicle_names[j]] = None
            else:
                row[vehicle_names[j]] = None

        data_rows.append(row)

    if not data_rows:
        return None

    df = pd.DataFrame(data_rows)

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
