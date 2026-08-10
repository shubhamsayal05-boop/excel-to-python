"""Export operation mode tables from config.py to operation_modes.json for EXE bundling."""

import json

import config

payload = {
    "BUILD_STAMP": config.BUILD_STAMP,
    "OPERATION_MODE_MAPPING": {
        str(code): name for code, name in config.OPERATION_MODE_MAPPING.items()
    },
    "AVL_ODRIV_MAPPING": config.AVL_ODRIV_MAPPING,
    "HEATMAP_OPERATION_CODES": config.HEATMAP_OPERATION_CODES,
    "PARENT_OPERATION_CODES": sorted(config.PARENT_OPERATION_CODES),
    "GEAR_SHIFT_GENERAL_CODES": sorted(config.GEAR_SHIFT_GENERAL_CODES),
}

with open("operation_modes.json", "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")

print(f"Wrote operation_modes.json ({len(payload['HEATMAP_OPERATION_CODES'])} heatmap rows)")
print(f"BUILD_STAMP: {payload['BUILD_STAMP']}")
print(f"10090100 present: {10090100 in payload['HEATMAP_OPERATION_CODES']}")
print(f"10090200 present: {10090200 in payload['HEATMAP_OPERATION_CODES']}")
