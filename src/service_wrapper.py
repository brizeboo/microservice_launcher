import sys
import time
import os
import win32serviceutil
import win32service
import win32event
import servicemanager

from config_manager import ServiceConfig
from log_manager import LogManager
from process_manager import ProcessManager
from sequential_starter import SequentialStarter
from service_monitor import ServiceMonitor

class MicroserviceLauncherService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MicroserviceLauncher"
    _svc_display_name_ = "Microservice Launcher Service"
    _svc_description_ = "Manages microservices defined in services_config.json"

    def __init__(self, args):
        """
        初始化 Windows 服务。
        Initialize the Windows Service.
        """
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        """
        停止服务。
        Stop the service.
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
        
        # 停止逻辑
        # Stop Logic
        if hasattr(self, 'monitor'):
            self.monitor.stop_monitoring()
        if hasattr(self, 'starter'):
            self.starter.stop_sequence()
        if hasattr(self, 'process_manager'):
            # 停止所有服务
            # Stop all services
            services = self.config_manager.get_services()
            for service in services:
                self.process_manager.stop_service(service["service_name"])

    def SvcDoRun(self):
        """
        运行服务主循环。
        Run the service main loop.
        """
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        # 将工作目录更改为脚本目录
        # Change working directory to script directory
        if getattr(sys, 'frozen', False):
             base_path = os.path.dirname(sys.executable)
        else:
             base_path = os.path.dirname(os.path.abspath(__file__))
             # If running from src, use parent directory as root
             if os.path.basename(base_path) == 'src':
                 base_path = os.path.dirname(base_path)
        
        os.chdir(base_path)

        # 初始化逻辑
        # Initialize Logic
        try:
            self.config_manager = ServiceConfig()
            self.log_manager = LogManager()
            self.process_manager = ProcessManager(self.log_manager)
            self.starter = SequentialStarter(self.config_manager, self.process_manager, self.log_manager)
            self.monitor = ServiceMonitor(self.config_manager, self.process_manager, self.log_manager, self.starter)
            
            # 启动所有服务
            # Start everything
            self.starter.start_all()
            self.monitor.start_monitoring()
            
            # 等待停止信号
            # Wait for stop signal
            while self.running:
                rc = win32event.WaitForSingleObject(self.hWaitStop, 1000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
        except Exception as e:
            servicemanager.LogMsg(servicemanager.EVENTLOG_ERROR_TYPE,
                                  0xF000, # Generic error
                                  (self._svc_name_, f"Service failed: {e}"))
            
if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MicroserviceLauncherService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(MicroserviceLauncherService)
