import tkinter as tk
from tkinter import ttk
import sys
import os
from gui import ServiceLauncherGUI
from i18n import i18n

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
        root.withdraw()
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        conf_dir = os.path.join(exe_dir, "conf")
        last_config_bat = os.path.join(conf_dir, "last_config.dat")
        try:
            if os.path.exists(last_config_bat):
                with open(last_config_bat, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.lower().startswith("set "):
                            kv = line[4:].strip()
                            if "=" in kv:
                                k, v = kv.split("=", 1)
                                if k.strip().upper() == "LANG":
                                    lang = v.strip().lower()
                                    if lang in ["en", "zh"]:
                                        i18n.set_language(lang)
                                        break
        except Exception:
            pass
        splash = tk.Toplevel(root)
        splash.overrideredirect(True)
        w, h = 320, 120
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        splash.geometry(f"{w}x{h}+{x}+{y}")
        frame = ttk.Frame(splash, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        logo_img = None
        logo_path_candidates = [
            os.path.join(exe_dir, "app_logo.png"),
            os.path.join(conf_dir, "app_logo.png"),
            os.path.join(exe_dir, "logo.png"),
            os.path.join(conf_dir, "logo.png"),
        ]
        for p in logo_path_candidates:
            if os.path.exists(p):
                try:
                    logo_img = tk.PhotoImage(file=p)
                except Exception:
                    logo_img = None
                break
        if logo_img:
            ttk.Label(frame, image=logo_img).pack(pady=(0, 10))
            splash.logo_img_ref = logo_img
        lbl = ttk.Label(frame, text=i18n.get("loading"))
        lbl.pack(pady=10)
        pb = ttk.Progressbar(frame, mode="indeterminate", length=200)
        pb.pack()
        pb.start(10)
        splash.update_idletasks()
        app = ServiceLauncherGUI(root, config_path=config_path)
        splash.destroy()
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.deiconify()
        root.mainloop()
