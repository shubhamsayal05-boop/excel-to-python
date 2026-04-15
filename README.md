# AVL-DRIVE Heatmap Tool — Python Version

A standalone Python web application that fully replicates the Excel-based **AVL-DRIVE Heatmap Tool v5.1** — completely independent of Excel.

## 🚗 What This Tool Does

This tool evaluates vehicle drivability and responsiveness by:

1. **Loading HeatMap Data** — AVL-DRIVE ratings (scores) for each vehicle across operation modes (e.g., Drive away, Acceleration, Tip in, etc.)
2. **Loading Sheet1 Data** — Drivability and Responsiveness evaluation data with P1/P2/P3 status dots and benchmark percentages for target vs. tested vehicles
3. **Running Evaluation** — Applies the AVL-DRIVE evaluation rules to determine GREEN / YELLOW / RED / N/A status for each operation
4. **Generating Results** — Produces color-coded evaluation results, overall status summaries, and group-level status assessments

### Features Replicated from Excel

| Excel Feature | Python Equivalent |
|---|---|
| HeatMap Sheet (data display) | 🔥 HeatMap View page with color-coded scores |
| Data Transfer Sheet → HeatMap | 📋 HeatMap Data Input with auto-transfer |
| Sheet1 (Drivability/Responsiveness) | 📊 Sheet1 Data Input with dot color encoding |
| Evaluation Results sheet | 📈 Evaluation Results with full status logic |
| RefreshHeatmap macro | Automatic data transfer on import |
| EvaluateAVLStatus macro | Run Evaluation button with all rules |
| BuildUniqueOverallStatus | Overall Status by Op Code summary |
| UpdateSubOperationHeatMap | Auto-updates heatmap status column |
| Operation Mode Group Status | Group-level OK/Acceptable/NOK assessment |
| Color-coded dots (Green/Yellow/Red) | Text-encoded status (G/Y/R) with color display |
| Excel export | CSV and Excel download buttons |

## 🛠️ Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd excel-to-python

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

## 📖 Usage Guide

### Step 1: Load HeatMap Data

1. Navigate to **📋 HeatMap Data Input**
2. Copy the data from your Excel **Data Transfer Sheet** (or HeatMap Sheet)
3. Paste the tab-separated data into the text area
4. Click **🔄 Process HeatMap Data**

**Expected format** (tab-separated):
```
	Operation Modes	Vehicle1_Name	Vehicle2_Name
	Operation Modes	DR	DR
10000000	AVL-DRIVE Rating	8.3	8.2
10100000	Drive away	7.9	7.4
10101300	Creep	7.2	6.9
```

### Step 2: Load Sheet1 Data

1. Navigate to **📊 Sheet1 Data Input**
2. Copy your Sheet1 data from Excel
3. **Encode dot colors as text** since colors can't be pasted:
   - `G` = Green ●
   - `Y` = Yellow ●
   - `R` = Red ●
   - Leave blank = White/N/A
4. Paste the tab-separated data
5. Click **🔄 Process Sheet1 Data**

### Step 3: View HeatMap

1. Navigate to **🔥 HeatMap View**
2. Select Target and Tested vehicles
3. Toggle "Hide rows without tested vehicle data" as needed
4. Scores are color-coded: Green (≥8), Yellow (≥7), Red (<7)

### Step 4: Run Evaluation

1. Navigate to **📈 Evaluation Results**
2. Confirm Target and Tested vehicle names
3. Click **🔄 Run Evaluation**
4. Review:
   - **Detailed Results** — per-operation status
   - **Overall Status by Op Code** — aggregated status
   - **Status Distribution** — counts per status
   - **Operation Mode Group Status** — section-level assessment
5. Download results as CSV or Excel

## 📊 Evaluation Rules

### Individual Status (per Drivability or Responsiveness)

| Condition | Status |
|-----------|--------|
| P1 dot is white/missing (N/A) | **N/A** |
| AVL Score < 7.0 OR P1 = RED | **RED** 🔴 |
| AVL ≥ 7.0 AND P1 = YELLOW | **YELLOW** 🟡 |
| AVL ≥ 7.0 AND P1 = GREEN AND no benchmark data | **GREEN** 🟢 |
| AVL ≥ 7.0 AND P1 = GREEN AND tested ≥ target | **GREEN** 🟢 |
| AVL ≥ 7.0 AND P1 = GREEN AND (target − tested) ≤ 2 | **GREEN** 🟢 |
| AVL ≥ 7.0 AND P1 = GREEN AND (target − tested) > 2 | **YELLOW** 🟡 |

### Final Status (combined Drivability + Responsiveness)

| Condition | Final Status |
|-----------|-------------|
| Either is RED | **RED** 🔴 |
| Either is YELLOW | **YELLOW** 🟡 |
| Both GREEN | **GREEN** 🟢 |
| One GREEN + one N/A | **GREEN** 🟢 |
| Both N/A | **N/A** |

### Group Status

| Condition | Group Status |
|-----------|-------------|
| Any RED in the group | **NOK** 🔴 |
| >35% YELLOW in the group | **Acceptable** 🟡 |
| Otherwise | **OK** 🟢 |

## 📁 Project Structure

```
excel-to-python/
├── app.py                  # Streamlit web application (main entry point)
├── config.py               # Constants, mappings, thresholds, colors
├── heatmap_engine.py       # HeatMap data processing logic
├── evaluation_engine.py    # Evaluation logic (status rules, combining)
├── requirements.txt        # Python dependencies
├── sample_data/
│   ├── heatmap_data.tsv    # Sample HeatMap data for testing
│   └── sheet1_data.tsv     # Sample Sheet1 data for testing
├── tests/
│   └── test_evaluation.py  # Unit tests for evaluation logic
└── README.md               # This file
```

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

## 📝 Sample Data

Sample data files are provided in the `sample_data/` directory:
- `heatmap_data.tsv` — Example Data Transfer Sheet data
- `sheet1_data.tsv` — Example Sheet1 Drivability/Responsiveness data

You can copy the contents of these files and paste them directly into the application.

## 🔧 Technical Notes

- The original Excel tool used VBA macros for data processing and colored cell formatting
- This Python version uses Streamlit for the web UI and pandas for data processing
- Dot colors from the Excel tool (which rely on font color) are preserved when uploading the original Excel file directly. The tool reads the actual ● font color (green / yellow / red / white) using openpyxl. When pasting as text, dot colors are encoded as text (G/Y/R) since web-based text input cannot carry color metadata
- All evaluation rules, thresholds, and status combination logic are faithfully ported from the VBA code
- The operation mode mappings and AVL-ODRIV mappings are embedded in `config.py`