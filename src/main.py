import tkinter as tk
import sys
import os
from gui import ServiceLauncherGUI

if __name__ == "__main__":
    # 检查 Windows 服务参数
    # Check for Windows Service arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "remove", "start", "stop", "restart", "debug", "--startup"]:
        try:
            import service_wrapper
            import win32serviceutil
            win32serviceutil.HandleCommandLine(service_wrapper.MicroserviceLauncherService)
        except ImportError as e:
            print(f"Error: pywin32 or service_wrapper not found. {e}")
            print("Please run: pip install pywin32")
    else:
        # 检查配置路径参数
        # Check for config path argument
        config_path = None
        if len(sys.argv) > 1:
            # 假设参数是配置文件路径（如果不是服务命令）
            # Assume the argument is the config file path if it's not a service command
            possible_path = sys.argv[1]
            if not possible_path.startswith("-"): # Avoid flags if any
                 config_path = possible_path
        
        # 启动 GUI
        # Start GUI
        root = tk.Tk()
        app = ServiceLauncherGUI(root, config_path=config_path)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
