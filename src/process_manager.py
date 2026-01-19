import subprocess
import psutil
import threading
import os
import time

class ProcessManager:
    def __init__(self, log_manager):
        """
        初始化 ProcessManager 实例。
        Initialize the ProcessManager instance.
        """
        self.processes = {}  # service_name -> subprocess.Popen object
        self.log_manager = log_manager

    def start_service(self, service_config):
        """
        启动指定的服务。
        Start the specified service.
        """
        service_name = service_config["service_name"]
        
        # Docker Compose 风格: 获取 'command' 和 'working_dir'
        # Docker Compose style: 'command' and 'working_dir'
        command = service_config.get("command")
        working_dir = service_config.get("working_dir")
        environment = service_config.get("environment")
        
        if not command:
            self.log_manager.log(service_name, "ERROR", "Configuration error: Missing 'command'.")
            return False

        # 检查服务是否已经在运行
        # Check if already running
        if self.is_process_running(service_name):
            self.log_manager.log(service_name, "WARN", "Service is already running.")
            return True

        # 如果没有指定 working_dir，则默认为 None
        # Resolve working_dir if not absolute
        cwd = working_dir if working_dir else None
        
        # 检查命令是否为可执行文件路径
        # If command is a file path, we can check existence (optional but good for debugging)
        # But 'command' could be "python main.py", so simple os.path.exists might fail.
        # We only check if it looks like an absolute path to a file.
        if isinstance(command, str) and os.path.isabs(command) and os.path.isfile(command):
            if not os.path.exists(command):
                 self.log_manager.log(service_name, "ERROR", f"Command executable not found: {command}")
                 return False

        try:
            # 启动子进程
            # Handle command list vs string
            # If list, subprocess handles it. If string, we might need shell=True or rely on Windows parsing.
            # Docker compose allows both.
            # If we use shell=True, we can run "python main.py" easily.
            # But previously we used shell=False (default) with .bat file which works on Windows.
            
            # If command is string and not a simple path, splitting it might be needed if shell=False.
            # But let's try to keep it simple. 
            
            env = os.environ.copy()
            if environment:
                if isinstance(environment, dict):
                    for k, v in environment.items():
                        if k:
                            env[str(k)] = "" if v is None else str(v)
                elif isinstance(environment, list):
                    for item in environment:
                        if not isinstance(item, str):
                            continue
                        if "=" in item:
                            k, v = item.split("=", 1)
                            if k:
                                env[str(k)] = str(v)
                        else:
                            env[str(item)] = env.get(str(item), "")

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                text=True,
                cwd=cwd,
                shell=False,
                env=env
            )
            
            self.processes[service_name] = process
            self.log_manager.log(service_name, "INFO", f"Started process with PID: {process.pid}")

            # 启动线程读取 stdout 和 stderr
            # Start threads to read stdout/stderr
            threading.Thread(target=self._read_output, args=(process.stdout, service_name, "INFO"), daemon=True).start()
            threading.Thread(target=self._read_output, args=(process.stderr, service_name, "ERROR"), daemon=True).start()

            return True
        except Exception as e:
            self.log_manager.log(service_name, "ERROR", f"Failed to start service: {e}")
            return False

    def stop_service(self, service_name):
        """
        停止指定的服务。
        Stop the specified service.
        """
        process = self.processes.get(service_name)
        if not process:
            self.log_manager.log(service_name, "WARN", "Service is not running (No Process recorded).")
            return

        pid = process.pid
        try:
            # 检查 PID 是否存在并终止进程树
            if psutil.pid_exists(pid):
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                parent.kill()
                self.log_manager.log(service_name, "INFO", "Service stopped successfully.")
            else:
                 self.log_manager.log(service_name, "WARN", "Process not found (already stopped?).")
        except Exception as e:
            self.log_manager.log(service_name, "ERROR", f"Error stopping service: {e}")
        finally:
            # 从记录中移除进程
            if service_name in self.processes:
                del self.processes[service_name]

    def is_process_running(self, service_name):
        """
        检查指定服务是否正在运行。
        Check if the specified service is running.
        """
        process = self.processes.get(service_name)
        if process and process.poll() is None:
            return True
        return False
    
    def get_exit_code(self, service_name):
        """
        获取服务的退出代码。
        Get the exit code of the service.
        """
        process = self.processes.get(service_name)
        if process:
            return process.poll()
        return None

    def _read_output(self, pipe, service_name, level):
        """
        从子进程管道读取输出并记录日志。
        Reads output from subprocess pipe and logs it.
        """
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    self.log_manager.log(service_name, level, line.strip())
        except Exception as e:
             # This might happen if process is killed abruptly
             pass
        finally:
            pipe.close()
