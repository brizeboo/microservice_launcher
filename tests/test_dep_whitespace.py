import json
import os
import time
import sys
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from config_manager import ServiceConfig
from sequential_starter import SequentialStarter

class DummyLogger:
    def log(self, service_name, level, message):
        pass
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

def write_config(path):
    data = {
        "services": [
            {
                "service_name": "redis",
                "command": ["echo", "redis"],
                "working_dir": os.getcwd(),
                "health_check_type": "none"
            },
            {
                "service_name": "gateway",
                "command": ["echo", "gateway"],
                "working_dir": os.getcwd(),
                "health_check_type": "none",
                "depends_on": ["   redis   "]
            }
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    cfg_path = os.path.join(os.getcwd(), "tests_services_ws.json")
    write_config(cfg_path)
    cfg = ServiceConfig(cfg_path)
    pm = DummyProcessManager()
    lg = DummyLogger()
    starter = SequentialStarter(cfg, pm, lg)
    starter.start_all()
    time.sleep(2)
    out_path = os.path.join(os.getcwd(), "tests", "out_order_ws.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(",".join(pm.order))

if __name__ == "__main__":
    main()
