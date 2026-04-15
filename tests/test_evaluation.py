"""
Unit tests for the AVL-DRIVE Heatmap Tool evaluation logic.
"""

import sys
import os
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation_engine import (
    _evaluate_status,
    _combine_status,
    _bench_diff,
    _to_float,
    _parse_dot_status,
    evaluate_avl_status,
    build_overall_status,
    calculate_group_status,
    parse_sheet1_data,
)
from heatmap_engine import (
    build_heatmap_template,
    parse_heatmap_data,
    refresh_heatmap,
    filter_heatmap_rows,
)
from config import BENCH_SENTINEL


# ============================================================================
# Tests for _evaluate_status
# ============================================================================
class TestEvaluateStatus:
    def test_p1_na_returns_na(self):
        assert _evaluate_status(8.0, "N/A", 0, 100, 100) == "N/A"

    def test_avl_below_7_returns_red(self):
        assert _evaluate_status(6.5, "GREEN", 0, 100, 100) == "RED"

    def test_p1_red_returns_red(self):
        assert _evaluate_status(8.0, "RED", 0, 100, 100) == "RED"

    def test_p1_yellow_returns_yellow(self):
        assert _evaluate_status(8.0, "YELLOW", 0, 100, 100) == "YELLOW"

    def test_green_no_benchmark_returns_green(self):
        assert _evaluate_status(8.0, "GREEN", BENCH_SENTINEL, 0, 0) == "GREEN"

    def test_green_tested_ge_target_returns_green(self):
        assert _evaluate_status(8.0, "GREEN", 0, 90, 95) == "GREEN"

    def test_green_within_tolerance_returns_green(self):
        assert _evaluate_status(8.0, "GREEN", 1.5, 95, 93.5) == "GREEN"

    def test_green_exceeds_tolerance_returns_yellow(self):
        assert _evaluate_status(8.0, "GREEN", 5.0, 100, 95) == "YELLOW"

    def test_avl_exactly_7_with_green_p1(self):
        assert _evaluate_status(7.0, "GREEN", BENCH_SENTINEL, 0, 0) == "GREEN"

    def test_avl_exactly_7_with_yellow_p1(self):
        assert _evaluate_status(7.0, "YELLOW", 0, 100, 100) == "YELLOW"


# ============================================================================
# Tests for _combine_status
# ============================================================================
class TestCombineStatus:
    def test_both_green(self):
        assert _combine_status("GREEN", "GREEN") == "GREEN"

    def test_either_red(self):
        assert _combine_status("RED", "GREEN") == "RED"
        assert _combine_status("GREEN", "RED") == "RED"

    def test_either_yellow(self):
        assert _combine_status("YELLOW", "GREEN") == "YELLOW"
        assert _combine_status("GREEN", "YELLOW") == "YELLOW"

    def test_green_and_na(self):
        assert _combine_status("GREEN", "N/A") == "GREEN"
        assert _combine_status("N/A", "GREEN") == "GREEN"

    def test_both_na(self):
        assert _combine_status("N/A", "N/A") == "N/A"

    def test_red_over_yellow(self):
        assert _combine_status("RED", "YELLOW") == "RED"

    def test_yellow_and_na(self):
        assert _combine_status("YELLOW", "N/A") == "YELLOW"


# ============================================================================
# Tests for _bench_diff
# ============================================================================
class TestBenchDiff:
    def test_both_zero(self):
        assert _bench_diff(0, 0) == BENCH_SENTINEL

    def test_target_zero(self):
        assert _bench_diff(0, 50) == BENCH_SENTINEL

    def test_normal_diff(self):
        assert _bench_diff(100, 95) == 5.0

    def test_tested_higher(self):
        assert _bench_diff(90, 100) == 10.0


# ============================================================================
# Tests for _to_float
# ============================================================================
class TestToFloat:
    def test_valid_number(self):
        assert _to_float("8.3") == 8.3

    def test_int_string(self):
        assert _to_float("100") == 100.0

    def test_empty_string(self):
        assert _to_float("") == 0.0

    def test_none(self):
        assert _to_float(None) == 0.0

    def test_non_numeric(self):
        assert _to_float("abc") == 0.0


# ============================================================================
# Tests for _parse_dot_status
# ============================================================================
class TestParseDotStatus:
    def test_green(self):
        assert _parse_dot_status("G") == "GREEN"
        assert _parse_dot_status("GREEN") == "GREEN"

    def test_yellow(self):
        assert _parse_dot_status("Y") == "YELLOW"
        assert _parse_dot_status("YELLOW") == "YELLOW"

    def test_red(self):
        assert _parse_dot_status("R") == "RED"
        assert _parse_dot_status("RED") == "RED"

    def test_blank(self):
        assert _parse_dot_status("") == "N/A"
        assert _parse_dot_status(None) == "N/A"

    def test_bullet(self):
        assert _parse_dot_status("●") == "N/A"


# ============================================================================
# Tests for build_heatmap_template
# ============================================================================
class TestBuildHeatmapTemplate:
    def test_returns_dataframe(self):
        df = build_heatmap_template()
        assert isinstance(df, pd.DataFrame)
        assert "Op Code" in df.columns
        assert "Operation Mode" in df.columns
        assert len(df) > 0

    def test_contains_known_operations(self):
        df = build_heatmap_template()
        op_codes = df["Op Code"].tolist()
        assert 10000000 in op_codes  # AVL-DRIVE Rating
        assert 10100000 in op_codes  # Drive away
        assert 10120200 in op_codes  # Constant load


# ============================================================================
# Tests for parse_heatmap_data
# ============================================================================
class TestParseHeatmapData:
    def test_basic_parse(self):
        text = (
            "\tOperation Modes\tVehicle A\tVehicle B\n"
            "\tOperation Modes\tDR\tDR\n"
            "10000000\tAVL-DRIVE Rating\t8.3\t8.2\n"
            "10100000\tDrive away\t7.9\t7.4\n"
        )
        result = parse_heatmap_data(text)
        assert result is not None
        assert len(result["vehicle_names"]) == 2
        assert len(result["data"]) == 2

    def test_empty_input(self):
        assert parse_heatmap_data("") is None
        assert parse_heatmap_data("   ") is None


# ============================================================================
# Tests for evaluate_avl_status
# ============================================================================
class TestEvaluateAVLStatus:
    def test_basic_evaluation(self):
        sheet1_data = {
            "target_car": "Car A",
            "tested_car": "Car B",
            "sections": [],
            "operations": [
                {
                    "section": "Drive away",
                    "op_code": 10101100,
                    "operation": "DASS",
                    "driv_p1": "GREEN",
                    "driv_p2": "GREEN",
                    "driv_p3": "GREEN",
                    "driv_tested": 99.8,
                    "driv_target": 100,
                    "resp_p1": "GREEN",
                    "resp_p2": "GREEN",
                    "resp_p3": "GREEN",
                    "resp_tested": 98,
                    "resp_target": 100,
                },
            ],
        }

        heatmap_df = pd.DataFrame({
            "Op Code": [10101100],
            "Operation Mode": ["Standing start"],
            "Car B": [7.6],
        })

        result = evaluate_avl_status(sheet1_data, heatmap_df, "Car A", "Car B")
        assert len(result) == 1
        assert result.iloc[0]["Driv Status"] == "GREEN"
        assert result.iloc[0]["Final Status"] == "GREEN"


# ============================================================================
# Tests for build_overall_status
# ============================================================================
class TestBuildOverallStatus:
    def test_all_green(self):
        df = pd.DataFrame({
            "Op Code": [10101100, 10101100],
            "Operation": ["Op1", "Op1"],
            "Final Status": ["GREEN", "GREEN"],
        })
        result = build_overall_status(df)
        assert result.iloc[0]["Overall Status"] == "GREEN"

    def test_any_red(self):
        df = pd.DataFrame({
            "Op Code": [10101100, 10101100],
            "Operation": ["Op1", "Op1"],
            "Final Status": ["GREEN", "RED"],
        })
        result = build_overall_status(df)
        assert result.iloc[0]["Overall Status"] == "RED"

    def test_all_na(self):
        df = pd.DataFrame({
            "Op Code": [10101100],
            "Operation": ["Op1"],
            "Final Status": ["N/A"],
        })
        result = build_overall_status(df)
        assert result.iloc[0]["Overall Status"] == "N/A"


# ============================================================================
# Tests for calculate_group_status
# ============================================================================
class TestCalculateGroupStatus:
    def test_all_green(self):
        ops = [
            {"driv_p1": "GREEN"},
            {"driv_p1": "GREEN"},
            {"driv_p1": "GREEN"},
        ]
        assert calculate_group_status(ops, "driv_p1") == "OK"

    def test_any_red(self):
        ops = [
            {"driv_p1": "GREEN"},
            {"driv_p1": "RED"},
            {"driv_p1": "GREEN"},
        ]
        assert calculate_group_status(ops, "driv_p1") == "NOK"

    def test_many_yellow(self):
        ops = [
            {"driv_p1": "YELLOW"},
            {"driv_p1": "YELLOW"},
            {"driv_p1": "GREEN"},
        ]
        # 66% yellow > 35% threshold
        assert calculate_group_status(ops, "driv_p1") == "Acceptable"

    def test_empty(self):
        assert calculate_group_status([], "driv_p1") == ""


# ============================================================================
# Tests for filter_heatmap_rows
# ============================================================================
class TestFilterHeatmapRows:
    def test_filter_removes_empty(self):
        df = pd.DataFrame({
            "Op Code": [1, 2, 3],
            "Operation Mode": ["A", "B", "C"],
            "Vehicle": [8.0, None, 7.5],
        })
        result = filter_heatmap_rows(df, "Vehicle")
        assert len(result) == 2
        assert 2 not in result["Op Code"].values
