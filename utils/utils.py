import sys
from pathlib import Path

# Get the script directory and add it to the system path
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

marvelmind_dir = f"{Path.home()}/Downloads/marvelmind_SW"
dashboard_dir = f"{marvelmind_dir}/01_Dashboard"
linux_dir = f"{dashboard_dir}/02_linux/x86"
logs_dir = f"{linux_dir}/logs"



if __name__ == "__main__":
    print("Script Directory:", SCRIPT_DIR)
    print("Base Directory:", BASE_DIR)
    print("Marvelmind Directory:", marvelmind_dir)
    print("Dashboard Directory:", dashboard_dir)
    print("Linux Directory:", linux_dir)
    print("Logs Directory:", logs_dir)
    print("System Path:", sys.path)

    # Print all in logs directory
    logs_path = Path(logs_dir).expanduser()
    if logs_path.exists() and logs_path.is_dir():
        print("Logs Directory Contents:")
        for item in logs_path.iterdir():
            print(" -", item.name)
