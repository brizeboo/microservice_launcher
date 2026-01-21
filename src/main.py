import tkinter as tk
from tkinter import ttk
import sys
import os
import signal
import time
from gui import MicroServiceLauncherGUI
from i18n import i18n
from config_manager import ServiceConfig
from log_manager import LogManager
from process_manager import ProcessManager
from sequential_starter import SequentialStarter
from service_monitor import ServiceMonitor
 
class HeadlessLogger:
    def __init__(self):
        self._default_level = "INFO"
    def set_default_level(self, level_str):
        self._default_level = str(level_str).upper()
    def get_default_level_str(self):
        return self._default_level
    def get_logger(self, service_name, log_path):
        return None
    def log(self, service_name, level, message):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            sys.stderr.write(f"[{ts}] [{service_name}] {str(level).upper()}: {message}\n")
            sys.stderr.flush()
        except Exception:
            pass
    def get_gui_logs(self):
        return []

def run_headless(config_path=None):
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base_path) == "src":
            base_path = os.path.dirname(base_path)
    os.chdir(base_path)
    conf_dir = os.path.join(base_path, "conf")
    config_json = os.path.join(conf_dir, "config.json")
    services_json = os.path.join(conf_dir, "services.json")
    if config_path:
        try:
            cp = os.path.abspath(config_path)
            if os.path.isdir(cp):
                conf_dir = cp
                config_json = os.path.join(conf_dir, "config.json")
                services_json = os.path.join(conf_dir, "services.json")
            elif os.path.isfile(cp):
                bn = os.path.basename(cp).lower()
                if bn == "services.json":
                    services_json = cp
                    conf_dir = os.path.dirname(cp)
                    config_json = os.path.join(conf_dir, "config.json")
                elif bn == "config.json":
                    config_json = cp
                    conf_dir = os.path.dirname(cp)
                    services_json = os.path.join(conf_dir, "services.json")
        except Exception as e:
            try:
                sys.stderr.write(f"Invalid config_path: {e}\n")
                sys.stderr.flush()
            except Exception:
                pass
    cfg = None
    try:
        if os.path.exists(config_json):
            import json as _json
            with open(config_json, "r", encoding="utf-8") as f:
                cfg = _json.load(f)
                lang = str(cfg.get("lang", "")).lower()
                if lang in ["en", "zh"]:
                    i18n.set_language(lang)
    except Exception as e:
        cfg = None
        try:
            sys.stderr.write(f"Failed to read config.json: {e}\n")
            sys.stderr.flush()
        except Exception:
            pass
    logger = HeadlessLogger()
    try:
        if cfg is not None:
            lv = str(cfg.get("log_level", "")).upper()
            if lv in ["DEBUG", "INFO", "WARN", "WARNING", "ERROR"]:
                logger.set_default_level(lv)
    except Exception as e:
        try:
            logger.log("System", "WARNING", f"Set log level failed: {e}")
        except Exception:
            pass
    if not os.path.exists(services_json):
        msg = f"Required config not found: {services_json}"
        try:
            logger.log("System", "ERROR", msg)
        except Exception:
            pass
        try:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except Exception:
            pass
        sys.exit(2)
    cfgm = ServiceConfig(services_json)
    pm = ProcessManager(logger)
    starter = SequentialStarter(cfgm, pm, logger)
    monitor = ServiceMonitor(cfgm, pm, logger, starter)
    stop_flag = {"v": False}
    def _halt(*_a):
        stop_flag["v"] = True
    try:
        signal.signal(signal.SIGINT, _halt)
    except Exception as e:
        try:
            logger.log("System", "WARNING", f"Register SIGINT failed: {e}")
        except Exception:
            pass
    try:
        signal.signal(signal.SIGTERM, _halt)
    except Exception as e:
        try:
            logger.log("System", "WARNING", f"Register SIGTERM failed: {e}")
        except Exception:
            pass
    try:
        starter.start_all()
    except Exception as e:
        try:
            logger.log("System", "ERROR", f"Start failed: {e}")
        except Exception:
            pass
        try:
            services = cfgm.get_services()
            for service in services:
                try:
                    pm.stop_service(service.get("service_name") or service.get("name"))
                except Exception:
                    pass
        except Exception:
            pass
        sys.exit(3)
    try:
        monitor.start_monitoring()
    except Exception as e:
        try:
            logger.log("System", "ERROR", f"Monitor start failed: {e}")
        except Exception:
            pass
        try:
            services = cfgm.get_services()
            for service in services:
                try:
                    pm.stop_service(service.get("service_name") or service.get("name"))
                except Exception:
                    pass
        except Exception:
            pass
        sys.exit(4)
    try:
        while not stop_flag["v"]:
            time.sleep(1)
    finally:
        try:
            monitor.stop_monitoring()
        except Exception as e:
            try:
                logger.log("System", "WARNING", f"Stop monitoring failed: {e}")
            except Exception:
                pass
        try:
            services = cfgm.get_services()
            for service in services:
                try:
                    pm.stop_service(service.get("service_name") or service.get("name"))
                except Exception as e:
                    try:
                        name = service.get("service_name") or service.get("name") or "unknown"
                        logger.log("System", "WARNING", f"Stop service failed: {name}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            try:
                logger.log("System", "WARNING", f"Services cleanup failed: {e}")
            except Exception:
                pass

def run_gui(config_path=None):
    root = tk.Tk()
    root.withdraw()
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    conf_dir = os.path.join(exe_dir, "conf")
    config_json = os.path.join(conf_dir, "config.json")
    try:
        if os.path.exists(config_json):
            import json as _json
            with open(config_json, "r", encoding="utf-8") as f:
                cfg = _json.load(f)
                lang = str(cfg.get("lang", "")).lower()
                if lang in ["en", "zh"]:
                    i18n.set_language(lang)
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
        os.path.join(exe_dir, "logo.png"),
        os.path.join(exe_dir, "scripts", "assets", "logo2.png"),
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
        try:
            root.iconphoto(True, logo_img)
        except Exception:
            pass
    lbl = ttk.Label(frame, text=i18n.get("loading"))
    lbl.pack(pady=10)
    pb = ttk.Progressbar(frame, mode="indeterminate", length=200)
    pb.pack()
    pb.start(10)
    splash.update_idletasks()
    app = MicroServiceLauncherGUI(root, config_path=config_path)
    splash.destroy()
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.deiconify()
    root.mainloop()

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
    elif len(sys.argv) > 1 and sys.argv[1] in ["--nssm"]:
        cfg_arg = None
        if len(sys.argv) > 2:
            a2 = sys.argv[2]
            if a2 and not a2.startswith("-"):
                cfg_arg = a2
        run_headless(cfg_arg)
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
        run_gui(config_path)
