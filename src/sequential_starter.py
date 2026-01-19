import threading
import time
import psutil
import subprocess
from health_checker import HealthChecker

class SequentialStarter:
    def __init__(self, service_config, process_manager, log_manager):
        """
        初始化 SequentialStarter。
        Initialize SequentialStarter.
        """
        self.service_config = service_config
        self.process_manager = process_manager
        self.log_manager = log_manager
        self.stop_flag = False
        self.is_starting = False

    def start_all(self, callback_on_complete=None):
        """
        开始所有服务的顺序启动。
        Start sequential startup of all services.
        """
        if self.is_starting:
            return
        self.is_starting = True
        self.stop_flag = False
        threading.Thread(target=self._start_sequence, args=(callback_on_complete,), daemon=True).start()

    def stop_sequence(self):
        """
        停止启动序列。
        Stop the startup sequence.
        """
        self.stop_flag = True
        self.is_starting = False

    def _wait_for_windows_service(self, service_name, timeout=30):
        """
        等待 Windows 服务处于“正在运行”状态。
        Wait for a Windows service to be in 'running' state.
        Returns True if running, False otherwise.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.stop_flag:
                return False
            
            try:
                srv = psutil.win_service_get(service_name)
                if srv.status().lower() == "running":
                    return True
            except psutil.NoSuchProcess:
                self.log_manager.log("System", "WARN", f"Windows service '{service_name}' not found.")
                return False
            except Exception as e:
                self.log_manager.log("System", "WARN", f"Error checking service '{service_name}': {e}")
            
            time.sleep(1)
        
        return False

    def _start_windows_service(self, service_name):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Start-Service -Name '{service_name}'"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log_manager.log("System", "ERROR", f"Failed to start Windows service '{service_name}': {result.stderr.strip()}")
                return False
            return True
        except Exception as e:
            self.log_manager.log("System", "ERROR", f"Exception starting Windows service '{service_name}': {e}")
            return False

    def _start_sequence(self, callback_on_complete):
        """
        执行启动序列的内部方法。
        Internal method to execute the startup sequence.
        """
        services = self.service_config.get_services()
        
        for service in services:
            if self.stop_flag:
                self.log_manager.log("System", "WARN", "Sequential startup stopped by user.")
                break

            name = service["service_name"]
            
            win_dep = service.get("windows_service_dependency")
            if win_dep:
                deps = win_dep if isinstance(win_dep, list) else [win_dep]
                for dep in deps:
                    self.log_manager.log("System", "INFO", f"Checking Windows Service dependency for {name}: {dep}...")
                    if not self._wait_for_windows_service(dep):
                        self.log_manager.log("System", "WARN", f"Windows Service '{dep}' is not running. Attempting to start.")
                        if self._start_windows_service(dep):
                            if not self._wait_for_windows_service(dep, timeout=30):
                                self.log_manager.log("System", "ERROR", f"Windows Service '{dep}' failed to reach running state. Stopping sequence.")
                                break
                        else:
                            self.log_manager.log("System", "ERROR", f"Windows Service '{dep}' could not be started. Stopping sequence.")
                            break
                if self.stop_flag:
                    break

            self.log_manager.log("System", "INFO", f"Starting {name}...")
            
            # 启动进程
            # Start Process
            if not self.process_manager.start_service(service):
                self.log_manager.log("System", "ERROR", f"Failed to start {name}. Stopping sequence.")
                break

            # 检查健康状态
            # Check Health
            health_type = service.get("health_check_type", "none")
            health_config = service.get("health_check_config", {})
            
            if health_type != "none":
                self.log_manager.log("System", "INFO", f"Waiting for {name} to be healthy...")
                is_healthy = False
                retries = 20 # Wait up to 20 * 1 = 20 seconds? Or make it configurable. 
                # Requirements say "Wait until healthy", let's use a reasonable timeout loop
                
                for _ in range(retries):
                    if self.stop_flag: break
                    
                    is_ok, msg = HealthChecker.check(health_type, health_config)
                    if is_ok:
                        self.log_manager.log(name, "INFO", f"Health Check Passed: {msg}")
                        is_healthy = True
                        break
                    time.sleep(1)
                
                if not is_healthy and not self.stop_flag:
                    self.log_manager.log("System", "ERROR", f"{name} failed health check. Stopping sequence.")
                    break
            else:
                time.sleep(1) # Small buffer if no check

        self.is_starting = False
        self.log_manager.log("System", "INFO", "Sequential startup finished.")
        if callback_on_complete:
            callback_on_complete()
