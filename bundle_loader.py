"""Load application modules from .py files inside the PyInstaller bundle.

Streamlit reruns app.py on each interaction. Frozen bytecode in the PYZ
archive can lag behind the source tree used by ``streamlit run``. Loading
from the copied .py files in ``_MEIPASS`` keeps the EXE in sync with the
project folder at build time.
"""

import importlib.util
import os
import sys

# Order matters: each module may import earlier entries.
_BUNDLE_MODULES = [
    ("config", "config.py"),
    ("heatmap_engine", "heatmap_engine.py"),
    ("evaluation_engine", "evaluation_engine.py"),
    ("heatmap_excel_export", "heatmap_excel_export.py"),
]


def load_bundle_modules(base_path=None):
    """Import local app modules from source files in the bundle directory."""
    if not getattr(sys, "frozen", False):
        return

    if base_path is None:
        base_path = sys._MEIPASS

    for mod_name, filename in _BUNDLE_MODULES:
        sys.modules.pop(mod_name, None)
        filepath = os.path.join(base_path, filename)
        if not os.path.isfile(filepath):
            raise RuntimeError(
                f"Bundle is missing {filename}. Rebuild the EXE from the latest branch."
            )
        spec = importlib.util.spec_from_file_location(mod_name, filepath)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load bundle module from {filepath}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)


def bundle_config_info():
    """Return a short diagnostic string for the Help page."""
    if "config" not in sys.modules:
        return "config not loaded"
    cfg = sys.modules["config"]
    stamp = getattr(cfg, "BUILD_STAMP", "?")
    codes = getattr(cfg, "HEATMAP_OPERATION_CODES", [])
    has_gs = 10090100 in codes and 10090200 in codes
    origin = getattr(cfg, "__file__", "?")
    return f"{stamp} · rows={len(codes)} · gearshift_general={'yes' if has_gs else 'no'} · from={origin}"
