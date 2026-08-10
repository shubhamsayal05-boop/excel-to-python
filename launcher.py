import sys
import os
import threading
import webbrowser
import time
import socket
import importlib.util


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def open_browser(port):
    for _ in range(30):
        if is_port_in_use(port):
            webbrowser.open(f"http://localhost:{port}")
            return
        time.sleep(1)


def _load_bundle_loader(base_path):
    loader_path = os.path.join(base_path, "bundle_loader.py")
    spec = importlib.util.spec_from_file_location("bundle_loader", loader_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load bundle_loader from {loader_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bundle_loader"] = module
    spec.loader.exec_module(module)
    return module


def main():
    PORT = 8501

    if is_port_in_use(PORT):
        webbrowser.open(f"http://localhost:{PORT}")
        sys.exit(0)

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    os.chdir(base_path)

    if getattr(sys, 'frozen', False):
        bundle_loader = _load_bundle_loader(base_path)
        bundle_loader.load_bundle_modules(base_path)

    threading.Thread(target=open_browser, args=(PORT,), daemon=True).start()

    from streamlit.web import cli as stcli

    app_path = os.path.join(base_path, "app.py")
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.headless=true",
        f"--server.port={PORT}",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
        "--global.developmentMode=false",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
