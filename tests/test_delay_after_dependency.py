import json
import os
import time
import sys
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from config_manager import ServiceConfig
from sequential_starter import SequentialStarter

class CaptureLogger:
    def __init__(self):
        self.events = []
    def log(self, service_name, level, message):
        ts = time.time()
        self.events.append((ts, service_name, level, message))
    def get_logger(self, service_name, log_path):
        return None

class DummyProcessManager:
    def __init__(self):
        self.order = []
        self.processes = {}
    def start_service(self, service):
        name = service["service_name"]
        if not self.is_process_running(name):
            self.order.append(name)
        self.processes[name] = True
        return True
    def is_process_running(self, service_name):
        return self.processes.get(service_name, False)
    def stop_service(self, service_name):
        self.processes.pop(service_name, None)
    def get_exit_code(self, service_name):
        return None

def write_config(path, interval_sec):
    data = {
        "services": [
            {
                "service_name": "redis",
                "command": ["echo", "redis"],
                "working_dir": os.getcwd(),
                "health_check_type": "none",
                "health_check_config": {
                    "interval": interval_sec
                }
            },
            {
                "service_name": "gateway",
                "command": ["echo", "gateway"],
                "working_dir": os.getcwd(),
                "health_check_type": "none",
                "depends_on": ["redis"]
            }
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    interval = 0.5
    cfg_path = os.path.join(os.getcwd(), "tests_services_delay.json")
    write_config(cfg_path, interval)
    cfg = ServiceConfig(cfg_path)
    pm = DummyProcessManager()
    lg = CaptureLogger()
    starter = SequentialStarter(cfg, pm, lg)
    starter.start_all()

    t_dep_ok = None
    t_start_gateway = None

    deadline = time.time() + 5
    while time.time() < deadline and (t_dep_ok is None or t_start_gateway is None):
        for ts, svc, lvl, msg in lg.events:
            if "Dependency 'redis' is running." in msg:
                t_dep_ok = ts
            if msg.startswith("Starting gateway"):
                t_start_gateway = ts
        time.sleep(0.05)

    out_path = os.path.join(os.getcwd(), "tests", "out_delay_check.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"t_dep_ok={t_dep_ok}\n")
        f.write(f"t_start_gateway={t_start_gateway}\n")
        f.write(f"delta={None if (t_dep_ok is None or t_start_gateway is None) else (t_start_gateway - t_dep_ok)}\n")
        f.write(f"interval={interval}\n")

    if t_dep_ok is None or t_start_gateway is None:
        raise SystemExit("Missing expected log events for verification")
    if (t_start_gateway - t_dep_ok) < interval * 0.9:
        raise SystemExit("Delay before starting dependent is shorter than configured interval")

if __name__ == "__main__":
    main()

