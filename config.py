"""
Configuration and constants for the AVL-DRIVE Heatmap Tool.
Contains all operation mode mappings, evaluation thresholds, and color definitions.
"""

# ============================================================================
# Operation Mode Mapping (Mapping Sheet)
# Maps operation code -> standard operation mode name
# ============================================================================
OPERATION_MODE_MAPPING = {
    10000000: "AVL-DRIVE Rating",
    10100000: "Drive away",
    10101300: "Creep",
    10101100: "Standing start",
    10102400: "Rolling start",
    10120000: "Acceleration",
    10120100: "Full load",
    10120200: "Constant load",
    10120300: "Load increase",
    10120900: "Load decrease",
    10030000: "Tip in",
    10030100: "At deceleration",
    10030200: "At constant speed / acceleration",
    10040000: "Tip out",
    10040300: "At constant speed / acceleration",
    10070100: "Transition to constant speed",
    10070000: "Deceleration",
    10070500: "Without brake",
    10071000: "Constant brake",
    10090000: "Gear shift",
    10092300: "Power-on upshift",
    10092500: "Tip out upshift",
    10098200: "Tip in upshift",
    10098400: "Load reversal upshift",
    10092100: "Coast / brake-on upshift",
    10093200: "Power-on downshift",
    10098100: "Tip out downshift",
    10093100: "Kick down / tip in downshift",
    10098300: "Load reversal downshift",
    10093400: "Coast / brake-on downshift",
    10097800: "Maneuvering",
    10097900: "Selector lever change",
    10090100: "Upshift",
    10090200: "Downshift",
    10080000: "Constant speed",
    10080200: "Without load",
    10080100: "Constant load",
    10010000: "Idle",
    10011000: "Vehicle stationary",
    10010200: "Air conditioning on / off",
    10010700: "Transition to idle",
    10015200: "Rev-up",
    10020000: "Engine start",
    10020100: "Manual start",
    10020200: "Auto start vehicle stationary",
    10020300: "Auto start vehicle moving",
    10140000: "Engine shut off",
    10140600: "Manual stop",
    10140700: "Auto stop",
    10460000: "TCC control",
    10467300: "Converter controlled slip",
    10467200: "Converter lock up",
    10467500: "Converter release",
    10430000: "Cylinder deactivation",
    10431300: "Cylinder deactivation",
    10431400: "Cylinder reactivation",
    10450000: "Vehicle stationary",
    10451400: "Vehicle stop",
    10451500: "Vehicle at standstill",
}

# ============================================================================
# AVL-ODRIV Mapping
# Maps detailed operation names to their parent operation codes.
# Multiple detailed names can map to the same code.
# ============================================================================
AVL_ODRIV_MAPPING = {
    "AVL-DRIVE Rating": 10000000,
    "Drive away": 10100000,
    "Creep": 10101300,
    "Drive Away Creep Eng On": 10101300,
    "Drive Away Creep Eng On - Cold": 10101300,
    "Drive Away Creep Eng Off": 10101300,
    "Drive Away Creep": 10101300,
    "Standing start": 10101100,
    "DASS Eng On": 10101100,
    "DASS Eng On - Cold": 10101100,
    "DASS Eng Off quick": 10101100,
    "DASS Eng Off slow": 10101100,
    "DASS - Eng Off - COM": 10101100,
    "DASS - Extended Eng Off": 10101100,
    "DASS": 10101100,
    "Rolling start": 10102400,
    "DA Rolling Start": 10102400,
    "Acceleration": 10120000,
    "Full load": 10120100,
    "Constant load": 10120200,
    "Accel Cst Load": 10120200,
    "Accel Cst Load - Cold": 10120200,
    "Load increase": 10120300,
    "Accel Load Increase": 10120300,
    "Load decrease": 10120900,
    "Accel Load Decrease": 10120900,
    "Tip in": 10030000,
    "At deceleration": 10030100,
    "Tip in at deceleration": 10030100,
    "At constant speed / acceleration": 10030200,
    "Tip in at constant speed": 10030200,
    "Tip out": 10040000,
    "Tip Out At Constant Speed": 10040300,
    "Tip Out After Acceleration": 10040300,
    "Deceleration": 10070000,
    "Decel Trans to Cst Spd": 10070100,
    "Decel - Trans to Cst Spd - Cold": 10070100,
    "Transition to constant speed": 10070100,
    "Without brake": 10070500,
    "Decel Without Brake": 10070500,
    "Decel Without Brake - Cold": 10070500,
    "Constant brake": 10071000,
    "Constant Brake": 10071000,
    "Decel Cst Brake": 10071000,
    "Decel Cst Brake - Cold": 10071000,
    "Gear shift": 10090000,
    "Power-on upshift": 10092300,
    "Power-on upshift Cold": 10092300,
    "Tip out upshift": 10092500,
    "Tip in upshift": 10098200,
    "Load reversal upshift": 10098400,
    "Coast / brake-on upshift": 10092100,
    "Power-on downshift": 10093200,
    "Tip out downshift": 10098100,
    "Kick down / tip in downshift": 10093100,
    "(PT) KD - tip in downshift": 10093100,
    "(TO) KD - tip in downshift": 10093100,
    "Coast-brake-on downshift Cold": 10093100,
    "Load reversal downshift": 10098300,
    "Coast / brake-on downshift": 10093400,
    "Upshift": 10090100,
    "GS Upshift": 10090100,
    "Gearshift Upshift": 10090100,
    "Downshift": 10090200,
    "GS Downshift": 10090200,
    "Gearshift Downshift": 10090200,
    "Maneuvering": 10097800,
    "Maneuvering - Cold": 10097800,
    "Maneuvering with throttle": 10097800,
    "Selector lever change": 10097900,
    "Lever change": 10097900,
    "Constant speed": 10080000,
    "Without load": 10080200,
    "Cst Speed Without Load": 10080200,
    "Cst Speed Without Load - Cold": 10080200,
    "Cst Speed Cst Load": 10080100,
    "Cst Speed Cst Load - Cold": 10080100,
    "Idle": 10010000,
    "Vehicle stationary": 10011000,
    "Air conditioning on / off": 10010200,
    "Idle Air Cond On-Off": 10010200,
    "Transition to idle": 10010700,
    "Rev-up": 10015200,
    "Engine start": 10020000,
    "Manual start": 10020100,
    "Auto start vehicle stationary": 10020200,
    "Auto start vehicle moving": 10020300,
    "Engine shut off": 10140000,
    "Manual stop": 10140600,
    "Auto stop": 10140700,
    "TCC control": 10460000,
    "Converter controlled slip": 10467300,
    "Converter lock up": 10467200,
    "Converter release": 10467500,
    "Cylinder deactivation": 10430000,
    "Cylinder reactivation": 10431400,
    "Idle Vehicle Stationary": 10450000,
    "Idle Vehicle Stationary - Cold": 10450000,
    "Vehicle stop": 10451400,
    "Vehicle Stop": 10451400,
    "Vehicle Stop - Cold": 10451400,
    "Vehicle at standstill": 10451500,
}

# ============================================================================
# HeatMap Sheet Operation Modes (ordered as in the sheet, rows 4-61)
# These are the operation codes in column A of the HeatMap Sheet
# ============================================================================
HEATMAP_OPERATION_CODES = [
    10000000, 10100000, 10101300, 10101100, 10102400,
    10120000, 10120100, 10120200, 10120300, 10120900,
    10030000, 10030100, 10030200,
    10040000, 10040300,
    10070000, 10070500, 10070100, 10071000,
    10090000, 10092300, 10092500, 10098200, 10098400,
    10092100, 10093200, 10098100, 10093100, 10098300,
    10093400, 10097800, 10097900, 10090100, 10090200,
    10080000, 10080200, 10080100,
    10010000, 10011000, 10010200, 10010700, 10015200,
    10020000, 10020100, 10020200, 10020300,
    10140000, 10140600, 10140700,
    10460000, 10467300, 10467200, 10467500,
    10430000, 10431300, 10431400,
    10450000, 10451400, 10451500,
]

# Parent (group header) operation codes – rendered bold with a shaded background
# in the HeatMap Sheet.  All other codes are child (sub-operation) rows.
PARENT_OPERATION_CODES = {
    10100000,  # Drive away
    10120000,  # Acceleration
    10030000,  # Tip in
    10040000,  # Tip out
    10070000,  # Deceleration
    10090000,  # Gear shift
    10080000,  # Constant speed
    10010000,  # Idle
    10020000,  # Engine start
    10140000,  # Engine shut off
    10460000,  # TCC control
    10430000,  # Cylinder deactivation
    10450000,  # Vehicle stationary
}

# General gearshift assessments — separate from detailed upshift/downshift sub-modes
# (Power-on upshift, Tip out upshift, etc.). Listed at the end of the Gear shift
# block on the HeatMap sheet.
GEAR_SHIFT_GENERAL_CODES = {10090100, 10090200}

_GEAR_SHIFT_SECTION_START = HEATMAP_OPERATION_CODES.index(10090000)
_GEAR_SHIFT_SECTION_END = HEATMAP_OPERATION_CODES.index(10080000)
GEAR_SHIFT_DETAILED_CODES = {
    code for code in HEATMAP_OPERATION_CODES[_GEAR_SHIFT_SECTION_START + 1:_GEAR_SHIFT_SECTION_END]
    if code not in GEAR_SHIFT_GENERAL_CODES
}

# ============================================================================
# Evaluation Thresholds
# ============================================================================
AVL_THRESHOLD = 7.0          # AVL score below this is RED
BENCH_TOLERANCE = 2.0        # Benchmark diff tolerance
BENCH_SENTINEL = 999.0       # Sentinel for missing benchmark data
YELLOW_GROUP_THRESHOLD = 0.35  # >35% yellow in group = group is yellow

# ============================================================================
# Color Definitions
# All RGB values extracted from the Excel workbook conditional formatting
# and cell styles so the Python tool matches the Excel tool exactly.
# ============================================================================
COLOR_GREEN = "#00B050"       # Excel status GREEN / OK / score-scale green endpoint
COLOR_YELLOW = "#FFC000"      # Excel status YELLOW (Evaluation Results sheet)
COLOR_YELLOW_BRIGHT = "#FFFF00"  # Excel HeatMap "Acceptable" / score-scale yellow midpoint
COLOR_RED = "#FF0000"         # Excel status RED / NOK / score-scale red endpoint
COLOR_DARK_RED = "#C00000"
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#000000"

# Sheet1 header & section colors (from Excel Sheet1 / ODRIV RATING tab)
COLOR_SHEET1_HEADER = "#17375E"   # dark navy – Sheet1 header rows
COLOR_SHEET1_SECTION_BG = "#F2F2F2"  # light gray – section header rows
COLOR_SHEET1_DOT_BG = "#D9D9D9"     # gray – dot (●) cell background

# HeatMap view colors (resolved from Excel theme: lt1=#FFFFFF with tint applied)
# Header/sub-header/parent rows: theme=0 (white), tint=-0.15 → #D9D9D9
COLOR_HEATMAP_HEADER = "#D9D9D9"     # gray – header, sub-header, parent rows
COLOR_HEATMAP_BORDER = "#000000"     # auto/black borders in Excel HeatMap Sheet
# Evaluation Results sheet header (explicit RGB in Excel, not theme-based)
COLOR_BLUE_HEADER = "#4472C4"
COLOR_LIGHT_BLUE = "#D9E1F2"

# Status to color mapping (for Evaluation Results rendering)
STATUS_COLORS = {
    "GREEN": COLOR_GREEN,
    "YELLOW": COLOR_YELLOW,
    "RED": COLOR_RED,
    "N/A": COLOR_WHITE,
}

# Dot color hex codes used in Sheet1
# Font colors from the Excel: green=008000, yellow=FFFF00, red=FF0000, white=FFFFFF
DOT_FONT_COLORS = {
    "GREEN": "#008000",
    "YELLOW": "#FFFF00",
    "RED": "#FF0000",
    "BLUE": "#99FBFB",
    "WHITE": "#FFFFFF",
}

# Score color-scale endpoints (3-point gradient matching Excel conditional formatting)
SCORE_SCALE_MIN = 1.0         # red endpoint
SCORE_SCALE_MID = 7.0         # yellow midpoint
SCORE_SCALE_MAX = 10.0        # green endpoint
SCORE_COLOR_MIN = (0xFF, 0x00, 0x00)   # #FF0000
SCORE_COLOR_MID = (0xFF, 0xFF, 0x00)   # #FFFF00
SCORE_COLOR_MAX = (0x00, 0xB0, 0x50)   # #00B050
