import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from datetime import datetime
import psutil
import sys
import os
import ctypes
import json

from config_manager import ServiceConfig
from process_manager import ProcessManager
from log_manager import LogManager
from sequential_starter import SequentialStarter
from health_checker import HealthChecker
from i18n import i18n
from service_monitor import ServiceMonitor

class MicroServiceLauncherGUI:
    def __init__(self, root, config_path=None):
        """
        初始化 GUI 应用程序。
        Initialize the GUI application.
        """
        self.root = root
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.exe_dir = exe_dir
        self.conf_dir = os.path.join(exe_dir, "conf")
        os.makedirs(self.conf_dir, exist_ok=True)
        self.logs_dir = os.path.join(exe_dir, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.config_json = os.path.join(self.conf_dir, "config.json")
        cfg = self._load_app_config()
        lang_loaded = cfg.get("lang")
        self.initial_lang = lang_loaded if lang_loaded in ["en", "zh"] else "zh"
        i18n.set_language(self.initial_lang)
        self.root.title(i18n.get("window_title"))
        self.root.geometry("1000x700")

        self.default_config_path = os.path.join(self.conf_dir, "services.json")
        initial_config_path = config_path if config_path else cfg.get("last_config_path")
        if not initial_config_path or not os.path.exists(initial_config_path):
            if not os.path.exists(self.default_config_path):
                default_config = {
                    "services": [
                        {
                            "service_name": "Example Service",
                            "working_dir": "D:/path/to/service",
                            "command": ["python", "app.py"]
                        }
                    ]
                }
                with open(self.default_config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
            initial_config_path = self.default_config_path
        self._save_app_config({"last_config_path": initial_config_path}, merge=True)

        # Initialize Managers
        try:
            self.config_manager = ServiceConfig(initial_config_path)
            self.log_manager = LogManager()
            lvl = cfg.get("log_level")
            if lvl:
                self.log_manager.set_default_level(lvl)
            self.process_manager = ProcessManager(self.log_manager)
            self.starter = SequentialStarter(self.config_manager, self.process_manager, self.log_manager)
            self.monitor = ServiceMonitor(self.config_manager, self.process_manager, self.log_manager, self.starter)
        except Exception as e:
            messagebox.showerror(i18n.get("init_error"), str(e))
            root.destroy()
            return

        self.services = self.config_manager.get_services()
        try:
            self.log_manager.get_logger("System", os.path.join(self.logs_dir, "system.log"))
            for s in self.services:
                name = s["service_name"]
                self.log_manager.get_logger(name, os.path.join(self.logs_dir, f"{name}.log"))
        except Exception:
            pass
        
        # 检查服务是否为空加载 - 可能意味着未找到配置
        # Check if services loaded empty - might mean config not found
        if not self.services and not os.path.exists(self.config_manager.config_path):
             # Don't destroy, just warn or let user import
             # messagebox.showwarning(i18n.get("info"), "Config file not found. Please import a config.")
             pass

        self.selected_service_for_log = "ALL"
        self.log_filter_level = "ALL"
        self.log_keyword_var = tk.StringVar(value="")

        self._setup_ui()
        self._refresh_ui_text() # Initial text set
        
        # 启动循环
        # Start loops
        self.running = True
        self.monitor.start_monitoring()
        
        self._ui_update_loop()

    def _setup_ui(self):
        """
        设置主 UI 组件。
        Setup the main UI components.
        """
        # 主布局
        # Main Layout
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧面板 - 服务列表
        # Left Panel - Service List
        left_frame = ttk.Frame(main_paned, width=400)
        main_paned.add(left_frame, weight=1)

        # 右侧面板 - 日志
        # Right Panel - Logs
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # --- 左侧面板内容 ---
        # 顶部栏 - 语言选择
        # --- Left Panel Content ---
        # Top Bar for Language
        lang_frame = ttk.Frame(left_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        self.lbl_language = ttk.Label(lang_frame, text=i18n.get("language") + ":")
        self.lbl_language.pack(side=tk.LEFT, padx=5)
        
        self.lang_var = tk.StringVar(value=getattr(self, "initial_lang", "zh"))
        self.combo_lang = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["en", "zh"], state="readonly", width=5)
        self.combo_lang.pack(side=tk.LEFT)
        self.combo_lang.bind("<<ComboboxSelected>>", self._on_language_change)
        
        self.lbl_service_list = ttk.Label(left_frame, text=i18n.get("service_list"), font=("Arial", 12, "bold"))
        self.lbl_service_list.pack(pady=5)
        
        self.service_frame = ttk.Frame(left_frame)
        self.service_frame.pack(fill=tk.BOTH, expand=True)

        self.service_widgets = {} # Map service_name -> {label, status_lbl, btn_start, btn_stop}

        for idx, service in enumerate(self.services):
            s_frame = ttk.Frame(self.service_frame, relief="groove", borderwidth=1)
            s_frame.pack(fill=tk.X, pady=2, padx=2)
            
            name = service["service_name"]
            
            # 状态指示器 (色块)
            # Status Indicator (Color Block)
            status_lbl = tk.Label(s_frame, text="   ", bg="gray", width=4)
            status_lbl.pack(side=tk.LEFT, padx=5)
            
            # 服务名称
            # Service Name
            # We need to store the reference to update text later if needed (though service names might not change)
            # But "Order: X" needs translation
            name_lbl = ttk.Label(s_frame, text="", width=25) 
            name_lbl.pack(side=tk.LEFT, padx=5)

            # 按钮
            # Buttons
            btn_frame = ttk.Frame(s_frame)
            btn_frame.pack(side=tk.RIGHT, padx=5)
            
            start_btn = ttk.Button(btn_frame, text="Start", width=6, command=lambda n=name: self._manual_start(n))
            start_btn.pack(side=tk.LEFT)
            
            stop_btn = ttk.Button(btn_frame, text="Stop", width=6, command=lambda n=name: self._manual_stop(n))
            stop_btn.pack(side=tk.LEFT)
            
            restart_btn = ttk.Button(btn_frame, text="Rst", width=4, command=lambda n=name: self._manual_restart(n))
            restart_btn.pack(side=tk.LEFT)

            self.service_widgets[name] = {
                "status_lbl": status_lbl,
                "name_lbl": name_lbl,
                "start_btn": start_btn,
                "stop_btn": stop_btn,
                "restart_btn": restart_btn
            }

        # --- 右侧面板内容 ---
        # --- Right Panel Content ---
        top_log_bar = ttk.Frame(right_frame)
        top_log_bar.pack(fill=tk.X, pady=5)
        
        self.lbl_filter = ttk.Label(top_log_bar, text=i18n.get("filter"))
        self.lbl_filter.pack(side=tk.LEFT, padx=5)
        
        self.log_service_var = tk.StringVar(value="ALL")
        # We need to update these values if language changes for "ALL" and "System"? 
        # Actually the values are used for logic. Display text can be different?
        # OptionMenu is tricky to update. Let's stick to logical names for dropdown or just keep English keys?
        # User asked for internationalization. "ALL" and "System" should be translated.
        # But `log_service_var` is used for filtering. We can keep the internal value english?
        # Or we rebuild the menu on language change.
        self.option_menu_frame = ttk.Frame(top_log_bar)
        self.option_menu_frame.pack(side=tk.LEFT)
        self._build_log_filter_menu()

        ttk.Label(top_log_bar, text=i18n.get("keyword")).pack(side=tk.LEFT, padx=10)
        self.entry_keyword = ttk.Entry(top_log_bar, textvariable=self.log_keyword_var, width=16)
        self.entry_keyword.pack(side=tk.LEFT)

        self.btn_clear = ttk.Button(top_log_bar, text=i18n.get("clear_logs"), command=self._clear_logs)
        self.btn_clear.pack(side=tk.RIGHT, padx=5)
        
        self.btn_export = ttk.Button(top_log_bar, text=i18n.get("export"), command=self._export_logs)
        self.btn_export.pack(side=tk.RIGHT, padx=5)

        self.log_text = scrolledtext.ScrolledText(right_frame, state='disabled', height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志标签颜色
        # Log Tags for Colors
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARN", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")

        # --- 底部面板 ---
        # --- Bottom Panel ---
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        self.btn_start_all = ttk.Button(bottom_frame, text=i18n.get("start_all"), command=self._start_all)
        self.btn_start_all.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_all = ttk.Button(bottom_frame, text=i18n.get("stop_all"), command=self._stop_all)
        self.btn_stop_all.pack(side=tk.LEFT, padx=5)
        
        # Right Side Buttons (Packed in reverse order of appearance from right to left)
        # Visual desired: [Import] [Edit] [Reload] [Install] [Uninstall] |
        
        self.btn_uninstall_svc = ttk.Button(bottom_frame, text=i18n.get("uninstall_service"), command=self._uninstall_service)
        self.btn_uninstall_svc.pack(side=tk.RIGHT, padx=5)
        
        self.btn_install_svc = ttk.Button(bottom_frame, text=i18n.get("install_service"), command=self._install_service)
        self.btn_install_svc.pack(side=tk.RIGHT, padx=5)

        self.btn_reload = ttk.Button(bottom_frame, text=i18n.get("reload_config"), command=self._reload_config)
        self.btn_reload.pack(side=tk.RIGHT, padx=5)

        self.btn_edit_config = ttk.Button(bottom_frame, text=i18n.get("edit_config"), command=self._open_config_editor)
        self.btn_edit_config.pack(side=tk.RIGHT, padx=5)
        
        self.btn_import = ttk.Button(bottom_frame, text=i18n.get("import_config"), command=self._import_config)
        self.btn_import.pack(side=tk.RIGHT, padx=5)

    def _build_log_filter_menu(self):
        """
        构建日志过滤下拉菜单。
        Build the log filter dropdown menu.
        """
        # 销毁旧的
        # Destroy old if exists
        for widget in self.option_menu_frame.winfo_children():
            widget.destroy()
            
        display_items = [i18n.get("all"), i18n.get("system")] + [s["service_name"] for s in self.services]
        # 显示->内部值映射
        self._log_filter_value_map = {
            i18n.get("all"): "ALL",
            i18n.get("system"): "SYSTEM",
        }
        for s in self.services:
            name = s["service_name"]
            self._log_filter_value_map[name] = name

        def to_display(val):
            if val == "ALL":
                return i18n.get("all")
            if val == "SYSTEM":
                return i18n.get("system")
            return val

        # 依据当前内部选择设置显示值
        self.log_service_var.set(to_display(self.selected_service_for_log))
        ttk.OptionMenu(self.option_menu_frame, self.log_service_var, to_display(self.selected_service_for_log), *display_items, command=self._on_log_filter_change).pack(side=tk.LEFT)

    def _load_language_from_bat(self):
        try:
            if not os.path.exists(self.last_config_dat):
                return None
            with open(self.last_config_dat, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith("set "):
                        kv = line[4:].strip()
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            if k.strip().upper() == "LANG":
                                lang = v.strip().lower()
                                if lang in ["en", "zh"]:
                                    return lang
            return None
        except Exception:
            return None

    def _save_language_to_bat(self):
        try:
            content = "@echo off\nset LANG={}".format(self.lang_var.get())
            with open(self.last_config_dat, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass
    def _load_app_config(self):
        try:
            if not os.path.exists(self.config_json):
                return {}
            with open(self.config_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    def _save_app_config(self, data, merge=True):
        try:
            base = {}
            if merge:
                base = self._load_app_config()
                if not isinstance(base, dict):
                    base = {}
            if not isinstance(data, dict):
                return
            base.update(data)
            with open(self.config_json, "w", encoding="utf-8") as f:
                json.dump(base, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    def _load_log_level_from_dat(self):
        try:
            if not os.path.exists(self.last_config_dat):
                return None
            with open(self.last_config_dat, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith("set "):
                        kv = line[4:].strip()
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            if k.strip().upper() == "LOG_LEVEL":
                                lv = v.strip().upper()
                                if lv in ["DEBUG", "INFO", "WARN", "WARNING", "ERROR"]:
                                    return lv
            return None
        except Exception:
            return None

    def _import_config(self):
        """
        导入配置文件。
        Import configuration file.
        """
        file_path = filedialog.askopenfilename(
            title=i18n.get("select_config"),
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                self.config_manager.set_config_path(file_path)
                self.services = self.config_manager.get_services()
                self._rebuild_service_list_ui() # Need to implement this
                self.monitor.update_services()
                self._update_config_buttons_state()
                messagebox.showinfo(i18n.get("info"), i18n.get("config_loaded"))
                try:
                    self._save_app_config({"last_config_path": file_path}, merge=True)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror(i18n.get("error"), str(e))

    def _rebuild_service_list_ui(self):
        """
        重建服务列表 UI。
        Rebuild the service list UI.
        """
        # 清除现有的
        # Clear existing
        for widget in self.service_frame.winfo_children():
            widget.destroy()
        self.service_widgets = {}

        # 重建
        # Rebuild
        for idx, service in enumerate(self.services):
            s_frame = ttk.Frame(self.service_frame, relief="groove", borderwidth=1)
            s_frame.pack(fill=tk.X, pady=2, padx=2)
            
            name = service["service_name"]
            
            # Status Indicator (Color Block)
            status_lbl = tk.Label(s_frame, text="   ", bg="gray", width=4)
            status_lbl.pack(side=tk.LEFT, padx=5)
            
            # Service Name
            name_lbl = ttk.Label(s_frame, text=name, width=25) 
            name_lbl.pack(side=tk.LEFT, padx=5)

            # Buttons
            btn_frame = ttk.Frame(s_frame)
            btn_frame.pack(side=tk.RIGHT, padx=5)
            
            start_btn = ttk.Button(btn_frame, text=i18n.get("start"), width=6, command=lambda n=name: self._manual_start(n))
            start_btn.pack(side=tk.LEFT)
            
            stop_btn = ttk.Button(btn_frame, text=i18n.get("stop"), width=6, command=lambda n=name: self._manual_stop(n))
            stop_btn.pack(side=tk.LEFT)
            
            restart_btn = ttk.Button(btn_frame, text=i18n.get("restart"), width=4, command=lambda n=name: self._manual_restart(n))
            restart_btn.pack(side=tk.LEFT)

            self.service_widgets[name] = {
                "status_lbl": status_lbl,
                "name_lbl": name_lbl,
                "start_btn": start_btn,
                "stop_btn": stop_btn,
                "restart_btn": restart_btn
            }
        
        self._build_log_filter_menu()

    def _on_language_change(self, event):
        """
        处理语言更改事件。
        Handle language change event.
        """
        new_lang = self.lang_var.get()
        i18n.set_language(new_lang)
        self._refresh_ui_text()
        self._save_app_config({"lang": new_lang}, merge=True)

    def _refresh_ui_text(self):
        """
        刷新 UI 文本以反映当前语言。
        Refresh UI text to reflect current language.
        """
        self.root.title(i18n.get("window_title"))
        self.lbl_language.config(text=i18n.get("language") + ":")
        self.lbl_service_list.config(text=i18n.get("service_list"))
        self.lbl_filter.config(text=i18n.get("filter"))
        
        self.btn_clear.config(text=i18n.get("clear_logs"))
        self.btn_export.config(text=i18n.get("export"))
        self.btn_start_all.config(text=i18n.get("start_all"))
        self.btn_stop_all.config(text=i18n.get("stop_all"))
        self.btn_reload.config(text=i18n.get("reload_config"))
        self.btn_edit_config.config(text=i18n.get("edit_config"))
        self.btn_install_svc.config(text=i18n.get("install_service"))
        self.btn_uninstall_svc.config(text=i18n.get("uninstall_service"))
        self.btn_import.config(text=i18n.get("import_config"))
        
        self._update_config_buttons_state()
        
        # Service Items
        for name, widgets in self.service_widgets.items():
            widgets["start_btn"].config(text=i18n.get("start"))
            widgets["stop_btn"].config(text=i18n.get("stop"))
            widgets["restart_btn"].config(text=i18n.get("restart"))
            # Update name label
            widgets["name_lbl"].config(text=name)

        # Rebuild OptionMenu for logs
        self._build_log_filter_menu()

    # --- Actions ---
    def _manual_start(self, service_name):
        """
        手动启动服务。
        Manually start a service.
        """
        if self.starter:
            self.starter.start_with_dependencies(service_name)

    def _manual_stop(self, service_name):
        """
        手动停止服务。
        Manually stop a service.
        """
        threading.Thread(target=self.process_manager.stop_service, args=(service_name,), daemon=True).start()

    def _manual_restart(self, service_name):
        """
        手动重启服务。
        Manually restart a service.
        """
        def restart():
            self.process_manager.stop_service(service_name)
            time.sleep(1)
            service = self.config_manager.get_service_by_name(service_name)
            if service:
                self.process_manager.start_service(service)
        threading.Thread(target=restart, daemon=True).start()

    def _show_win_service_selector(self, parent, text_widget):
        """
        显示 Windows 服务选择器对话框。
        Show Windows Service selector dialog.
        """
        selector = tk.Toplevel(parent)
        selector.title(i18n.get("select_windows_service"))
        selector.geometry("400x500")
        
        # 搜索/过滤器
        # Search/Filter
        filter_frame = ttk.Frame(selector)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(filter_frame, text=i18n.get("filter")).pack(side=tk.LEFT)
        filter_var = tk.StringVar()
        entry_filter = ttk.Entry(filter_frame, textvariable=filter_var)
        entry_filter.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 列表框
        # Listbox
        list_frame = ttk.Frame(selector)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 加载服务
        # Load services
        all_services = []
        try:
            for s in psutil.win_service_iter():
                try:
                    all_services.append(s.name())
                except: pass
            all_services.sort()
        except Exception as e:
            messagebox.showerror(i18n.get("error"), i18n.get("list_services_failed", e), parent=selector)
            return

        def update_list(*args):
            search = filter_var.get().lower()
            listbox.delete(0, tk.END)
            for s in all_services:
                if search in s.lower():
                    listbox.insert(tk.END, s)
        
        filter_var.trace("w", update_list)
        update_list()
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                svc_name = listbox.get(selection[0])
                snippet = f',\n      "windows_service_dependency": ["{svc_name}"]'
                text_widget.insert(tk.INSERT, snippet)
                selector.destroy()
        
        btn_select = ttk.Button(selector, text=i18n.get("select_and_insert"), command=on_select)
        btn_select.pack(pady=5)

    def _open_config_editor(self):
        """
        打开配置编辑器。
        Open configuration editor.
        """
        if not os.path.exists(self.config_manager.config_path):
             self._create_config()
             return

        editor = tk.Toplevel(self.root)
        editor.title(i18n.get("edit_config"))
        editor.geometry("600x500")
        
        # 文本区域
        # Text Area
        text_area = scrolledtext.ScrolledText(editor, wrap=tk.WORD, font=("Consolas", 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 加载内容
        # Load Content
        try:
            with open(self.config_manager.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                text_area.insert(1.0, content)
        except Exception as e:
            messagebox.showerror(i18n.get("error"), str(e), parent=editor)
            
        # 按钮
        # Buttons
        btn_frame = ttk.Frame(editor)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def save():
            new_content = text_area.get(1.0, tk.END).strip()
            try:
                self.config_manager.save_config_content(new_content)
                messagebox.showinfo(i18n.get("info"), i18n.get("config_saved"), parent=editor)
                self._reload_config() # Refresh main UI
                editor.destroy()
            except ValueError as ve:
                messagebox.showerror(i18n.get("error"), i18n.get("invalid_json", ve), parent=editor)
            except Exception as e:
                messagebox.showerror(i18n.get("error"), i18n.get("save_failed", e), parent=editor)
        
        def insert_win_service():
            self._show_win_service_selector(editor, text_area)
            
        ttk.Button(btn_frame, text=i18n.get("insert_win_service_dep"), command=insert_win_service).pack(side=tk.LEFT, padx=5)
                
        ttk.Button(btn_frame, text=i18n.get("save"), command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=i18n.get("cancel"), command=editor.destroy).pack(side=tk.RIGHT, padx=5)

    def _update_config_buttons_state(self):
        """
        Update the state of configuration related buttons based on file existence.
        """
        exists = os.path.exists(self.config_manager.config_path)
        if exists:
            self.btn_edit_config.config(text=i18n.get("edit_config"))
            self.btn_reload.config(state="normal")
        else:
            self.btn_edit_config.config(text=i18n.get("create_config"))
            self.btn_reload.config(state="disabled")

    def _create_config(self):
        """
        Create a new configuration file.
        """
        default_config = {
            "services": [
                {
                    "service_name": "Example Service",
                    "working_dir": "D:/path/to/service",
                    "command": ["python", "app.py"]
                }
            ]
        }
        try:
            file_path = self.default_config_path
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            self.config_manager.set_config_path(file_path)
            self.services = self.config_manager.get_services()
            self._rebuild_service_list_ui()
            self.monitor.update_services()
            self._update_config_buttons_state()
            messagebox.showinfo(i18n.get("info"), i18n.get("config_loaded"))
            self._open_config_editor()
            try:
                with open(self.last_config_dat, "w", encoding="utf-8") as f:
                    f.write(file_path)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror(i18n.get("error"), str(e))

    def _start_all(self):
        """
        启动所有服务。
        Start all services.
        """
        self.starter.start_all()

    def _stop_all(self):
        """
        停止所有服务。
        Stop all services.
        """
        self.starter.stop_sequence()
        for s in self.services:
            self._manual_stop(s["service_name"])

    def _reload_config(self):
        """
        重新加载配置。
        Reload configuration.
        """
        try:
            self.config_manager.load_config()
            self.services = self.config_manager.get_services()
            self.monitor.update_services()
            # Note: A full UI rebuild might be needed if services changed properly, 
            # but for simplicity we just reload config values for existing logic.
            # Rebuilding UI is complex dynamically, so we assume service list doesn't change 
            # or require restart of tool for structure changes.
            self._update_config_buttons_state()
            messagebox.showinfo(i18n.get("info"), i18n.get("config_reloaded"))
        except Exception as e:
            self._update_config_buttons_state()
            messagebox.showerror(i18n.get("error"), i18n.get("reload_failed", e))

    def _clear_logs(self):
        """
        清除日志显示。
        Clear log display.
        """
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def _export_logs(self):
        """
        导出日志到文件。
        Export logs to file.
        """
        try:
            with open("exported_logs.txt", "w", encoding="utf-8") as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo(i18n.get("info"), i18n.get("logs_exported"))
        except Exception as e:
            messagebox.showerror(i18n.get("error"), i18n.get("export_failed", e))

    def _on_log_filter_change(self, val):
        """
        处理日志过滤器更改。
        Handle log filter change.
        """
        try:
            internal = self._log_filter_value_map.get(val, val)
            self.selected_service_for_log = internal
        except Exception:
            self.selected_service_for_log = "ALL"

    def _run_admin_command(self, action):
        """
        使用管理员权限运行应用程序本身以执行特定操作。
        Run the application itself with admin privileges and specific action.
        action: 'install' or 'remove'
        """
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            executable = sys.executable
            # When running as service/installing, we assume the exe handles args.
            # "install" arg triggers HandleCommandLine in main.py
            args = f'{action}'
        else:
            # Running as script
            executable = sys.executable
            current_dir = os.path.dirname(os.path.abspath(__file__))
            main_script = os.path.join(current_dir, "main.py")
            args = f'"{main_script}" {action}'
        
        try:
            # ShellExecuteW(hwnd, operation, file, parameters, directory, show_cmd)
            # show_cmd: 1 (SW_SHOWNORMAL), 0 (SW_HIDE)
            # We use 1 so user can see if any console output (though noconsole exe won't show)
            cwd = os.getcwd()
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, cwd, 1)
            return ret > 32
        except Exception as e:
            self.log_manager.log("System", "ERROR", f"Failed to run admin command: {e}")
            return False

    def _install_service(self):
        """
        安装 Windows 服务。
        Install Windows Service.
        """
        if not messagebox.askyesno(i18n.get("info"), i18n.get("confirm_install_stop_all")):
            return
        self._stop_all()
        start_time = time.time()
        while True:
            all_stopped = True
            for s in self.services:
                status = self.monitor.get_status(s["service_name"])
                if status in ("RUNNING", "STARTING"):
                    all_stopped = False
                    break
            if all_stopped:
                break
            if time.time() - start_time > 30:
                break
            self.root.update_idletasks()
            time.sleep(0.5)
        script_candidates = [
            os.path.join(os.getcwd(), "scripts", "register_service_nssm.bat"),
            os.path.join(os.getcwd(), "register_service_nssm.bat"),
        ]
        for script_path in script_candidates:
            if os.path.exists(script_path):
                try:
                    os.startfile(script_path)
                    self.root.after(5000, self._check_service_installed)
                    return
                except Exception as e:
                    self.log_manager.log("System", "ERROR", f"Failed to run batch script: {e}")
        
        messagebox.showerror(i18n.get("error"), i18n.get("service_action_failed", "NSSM 脚本缺失：请将 register_service_nssm.bat 放置到 scripts 或同级目录"))

    def _uninstall_service(self):
        """
        卸载 Windows 服务。
        Uninstall Windows Service.
        """
        if not messagebox.askyesno(i18n.get("info"), i18n.get("confirm_uninstall")):
            return
            
        script_candidates = [
            os.path.join(os.getcwd(), "scripts", "unregister_service_nssm.bat"),
            os.path.join(os.getcwd(), "unregister_service_nssm.bat"),
        ]
        for script_path in script_candidates:
            if os.path.exists(script_path):
                try:
                    os.startfile(script_path)
                    self.root.after(5000, self._check_service_uninstalled)
                    return
                except Exception as e:
                    self.log_manager.log("System", "ERROR", f"Failed to run batch script: {e}")
            
        messagebox.showerror(i18n.get("error"), i18n.get("service_action_failed", "NSSM 脚本缺失：请将 unregister_service_nssm.bat 放置到 scripts 或同级目录"))

    def _check_service_installed(self):
        """
        检查服务是否已安装。
        Check if the service is installed.
        """
        try:
            psutil.win_service_get("MicroserviceLauncher")
            messagebox.showinfo(i18n.get("info"), i18n.get("service_installed"))
            # Optionally start it?
            # self._run_admin_command("start") 
        except psutil.NoSuchProcess:
            messagebox.showerror(i18n.get("error"), i18n.get("service_action_failed", "Service not found after installation"))
        except Exception as e:
            # It might exist but access denied? psutil usually allows query
             messagebox.showerror(i18n.get("error"), i18n.get("service_action_failed", str(e)))

    def _check_service_uninstalled(self):
        """
        检查服务是否已卸载。
        Check if the service is uninstalled.
        """
        try:
            psutil.win_service_get("MicroserviceLauncher")
            # Still exists
            messagebox.showerror(i18n.get("error"), i18n.get("service_action_failed", "Service still exists"))
        except psutil.NoSuchProcess:
            messagebox.showinfo(i18n.get("info"), i18n.get("service_uninstalled"))
        except Exception as e:
             messagebox.showerror(i18n.get("error"), i18n.get("service_action_failed", str(e)))

    # --- Background Logic ---
    # Moved to service_monitor.py
    
    def _ui_update_loop(self):
        """
        UI 更新循环，用于刷新日志和状态。
        UI update loop to refresh logs and status.
        """
        # 更新日志
        # Update Logs
        logs = self.log_manager.get_gui_logs()
        if logs:
            self.log_text.config(state='normal')
            for service, msg in logs:
                # 过滤逻辑
                # Filter logic
                # 内部枚举: "ALL" / "SYSTEM" / 具体服务名
                selected = self.selected_service_for_log
                show = False
                if selected == "ALL":
                    show = True
                elif selected == "SYSTEM":
                    show = (service == "System")
                else:
                    show = (service == selected)

                if not show:
                    continue

                # 关键字过滤
                kw = self.log_keyword_var.get().strip()
                if kw and kw.lower() not in msg.lower():
                    continue
                if not show:
                    continue
                
                # Insert with color
                tag = "INFO"
                
                self.log_text.insert(tk.END, msg + "\n", tag)
            
            # Keep only last 1000 lines
            num_lines = int(self.log_text.index('end-1c').split('.')[0])
            if num_lines > 1000:
                self.log_text.delete(1.0, f"{num_lines-1000}.0")
            
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')

        # 更新状态颜色
        # Update Status Colors
        for name, status in self.monitor.service_status.items():
            lbl = self.service_widgets.get(name, {}).get("status_lbl")
            if lbl:
                color = "gray"
                if status == "RUNNING": color = "#82B71E"
                elif status == "STARTING": color = "yellow"
                elif status == "ERROR": color = "red"
                lbl.config(bg=color)

        self.root.after(500, self._ui_update_loop)

    def on_close(self):
        """
        关闭应用程序并清理资源。
        Close the application and cleanup resources.
        """
        try:
            try:
                lang = self.lang_var.get()
            except Exception:
                lang = None
            try:
                log_level = self.log_manager.get_default_level_str()
            except Exception:
                log_level = None
            data = {}
            if isinstance(lang, str) and lang:
                data["lang"] = lang
            if isinstance(log_level, str) and log_level:
                data["log_level"] = log_level
            try:
                cfg_path = getattr(self.config_manager, "config_path", None)
                if isinstance(cfg_path, str) and cfg_path:
                    data["last_config_path"] = cfg_path
            except Exception:
                pass
            if data:
                self._save_app_config(data, merge=True)
        except Exception:
            pass
        self.running = False
        self.monitor.stop_monitoring()
        self.starter.stop_sequence()
        # 终止所有进程
        # Kill all processes
        for service in self.services:
            self.process_manager.stop_service(service["service_name"])
        self.root.destroy()
