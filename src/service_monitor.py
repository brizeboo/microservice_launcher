import time
import threading
import psutil
import subprocess
from health_checker import HealthChecker

class ServiceMonitor:
    def __init__(self, config_manager, process_manager, log_manager, starter):
        """
        初始化 ServiceMonitor。
        Initialize ServiceMonitor.
        """
        self.config_manager = config_manager
        self.process_manager = process_manager
        self.log_manager = log_manager
        self.starter = starter
        
        self.services = self.config_manager.get_services()
        self.service_status = {s["service_name"]: "STOPPED" for s in self.services}
        self.service_restart_counts = {s["service_name"]: 0 for s in self.services}
        self.last_restart_time = {s["service_name"]: 0 for s in self.services}
        
        self.running = False
        self.monitor_thread = None

    def start_monitoring(self):
        """
        开始监控线程。
        Start the monitoring thread.
        """
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """
        停止监控。
        Stop monitoring.
        """
        self.running = False
        # Do not join here if called from main thread while loop is running, 
        # but since it's daemon, we might just let it die or wait.
        # Joining might block if loop is sleeping.
        
    def update_services(self):
        """
        更新服务列表（在配置重新加载后）。
        Update service list (after config reload).
        """
        self.services = self.config_manager.get_services()
        # Ensure new services are in status dict
        for s in self.services:
            name = s["service_name"]
            if name not in self.service_status:
                self.service_status[name] = "STOPPED"
                self.service_restart_counts[name] = 0
                self.last_restart_time[name] = 0

    def get_status(self, service_name):
        """
        获取服务的当前状态。
        Get the current status of a service.
        """
        return self.service_status.get(service_name, "UNKNOWN")

    def _monitor_loop(self):
        """
        监控服务状态并处理自动重启的内部循环。
        Internal loop to monitor service status and handle auto-restart.
        """
        while self.running:
            for service in self.services:
                name = service["service_name"]
                
                # 1. 进程检查
                # 1. Process Check
                is_running = self.process_manager.is_process_running(name)
                
                # 2. 健康检查（如果正在运行）
                # 2. Health Check (if running)
                health_status = True
                if is_running:
                    check_type = service.get("health_check_type", "none")
                    if check_type != "none":
                        health_status, _ = HealthChecker.check(check_type, service.get("health_check_config", {}))

                dep_ok = True
                win_dep = service.get("windows_service_dependency")
                if win_dep:
                    deps = win_dep if isinstance(win_dep, list) else [win_dep]
                    for dep in deps:
                        try:
                            srv = psutil.win_service_get(dep)
                            if srv.status().lower() != "running":
                                self.log_manager.log("System", "WARN", f"Dependency Windows service '{dep}' not running for {name}. Attempting to start.")
                                try:
                                    result = subprocess.run(
                                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Start-Service -Name '{dep}'"],
                                        capture_output=True, text=True
                                    )
                                    if result.returncode != 0:
                                        self.log_manager.log("System", "ERROR", f"Failed to start dependency '{dep}': {result.stderr.strip()}")
                                        dep_ok = False
                                    else:
                                        start_time = time.time()
                                        ok = False
                                        while time.time() - start_time < 30:
                                            srv = psutil.win_service_get(dep)
                                            if srv.status().lower() == "running":
                                                ok = True
                                                break
                                            time.sleep(1)
                                        if not ok:
                                            self.log_manager.log("System", "ERROR", f"Dependency '{dep}' did not reach running state.")
                                            dep_ok = False
                                except Exception as e:
                                    self.log_manager.log("System", "ERROR", f"Exception starting dependency '{dep}': {e}")
                                    dep_ok = False
                        except psutil.NoSuchProcess:
                            dep_ok = False
                        except Exception:
                            dep_ok = False

                # 3. 确定状态
                # 3. Determine Status
                if not is_running:
                    new_status = "STOPPED"
                elif not health_status:
                    new_status = "ERROR" # Running but unhealthy
                elif not dep_ok:
                    new_status = "ERROR"
                    self.log_manager.log(name, "ERROR", "Dependency Windows service not running.")
                else:
                    new_status = "RUNNING" # Running and healthy (or no check)

                # 4. 自动重启逻辑
                # 4. Auto Restart Logic
                is_tracked = (name in self.process_manager.processes)
                
                if is_tracked and not is_running:
                    # 崩溃或退出
                    # CRASHED or Exited
                    new_status = "ERROR"
                    
                    restart_policy = service.get("restart", "no")
                    should_restart = False
                    
                    if restart_policy == "always" or restart_policy == "unless-stopped":
                        should_restart = True
                    elif restart_policy == "on-failure":
                        exit_code = self.process_manager.get_exit_code(name)
                        if exit_code is not None and exit_code != 0:
                            should_restart = True
                        else:
                            self.log_manager.log(name, "INFO", f"Process exited normally (code {exit_code}). Not restarting.")
                            self.process_manager.stop_service(name)
                            is_tracked = False

                    if should_restart:
                        max_retries = service.get("max_restart_times", 0)
                        current_retries = self.service_restart_counts[name]
                        interval = service.get("restart_interval", 3)
                        
                        if max_retries == 0 or current_retries < max_retries:
                            now = time.time()
                            if now - self.last_restart_time[name] >= interval:
                                self.log_manager.log(name, "WARN", f"Service exited. Restarting (Policy: {restart_policy})...")
                                self.process_manager.stop_service(name)
                                self.process_manager.start_service(service)
                                self.service_restart_counts[name] += 1
                                self.last_restart_time[name] = now
                            else:
                                # Waiting for interval
                                pass
                        else:
                            self.log_manager.log(name, "ERROR", "Max restart times reached.")
                            self.process_manager.stop_service(name)
                    elif is_tracked and not should_restart:
                         self.process_manager.stop_service(name)
                         new_status = "STOPPED"

                self.service_status[name] = new_status
            
            time.sleep(1)
