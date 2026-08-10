import sys
import os
import threading
import webbrowser
import time
import socket


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def open_browser(port):
    for _ in range(30):
        if is_port_in_use(port):
            webbrowser.open(f"http://localhost:{port}")
            return
        time.sleep(1)


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

    # Streamlit and sibling imports must resolve inside the bundle, not from
    # another copy of the project on sys.path (common when building from a
    # repo that also exists elsewhere on the machine).
    os.chdir(base_path)
    for mod_name in ('config', 'heatmap_engine', 'evaluation_engine', 'heatmap_excel_export', 'app'):
        sys.modules.pop(mod_name, None)

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
