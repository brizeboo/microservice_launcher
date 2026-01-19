import time
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from process_manager import ProcessManager
from log_manager import LogManager

def main():
    lm = LogManager()
    pm = ProcessManager(lm)
    service = {
        "service_name": "env_test_service",
        "command": ["python", "-c", "import os,sys,time; print(os.getenv('TEST_ENV','NO')); sys.stdout.flush(); time.sleep(0.2)"],
        "working_dir": None,
        "environment": {"TEST_ENV": "xyz"}
    }
    ok = pm.start_service(service)
    if not ok:
        with open("tests/env_result.txt", "w", encoding="utf-8") as f:
            f.write("START_FAIL")
        return
    time.sleep(0.5)
    logs = lm.get_gui_logs()
    found = any("xyz" in msg for _, msg in logs)
    with open("tests/env_result.txt", "w", encoding="utf-8") as f:
        f.write("ENV_OK" if found else "ENV_FAIL")
    pm.stop_service("env_test_service")

if __name__ == "__main__":
    main()
