TRANSLATIONS = {
    "en": {
        "window_title": "Microservice Launcher",
        "init_error": "Initialization Error",
        "loading": "Loading, please wait…",
        "service_list": "Service List",
        "start": "Start",
        "stop": "Stop",
        "restart": "Rst",
        "filter": "Filter:",
        "all": "ALL",
        "system": "System",
        "clear_logs": "Clear Logs",
        "export": "Export",
        "keyword": "Keyword",
        "start_all": "Start All (Sequential)",
        "stop_all": "Stop All",
        "reload_config": "Reload Config",
        "info": "Info",
        "error": "Error",
        "config_reloaded": "Config reloaded (Parameters updated). Restart tool if services added/removed.",
        "reload_failed": "Failed to reload: {}",
        "logs_exported": "Logs exported to exported_logs.txt",
        "export_failed": "Export failed: {}",
        "language": "Language",
        "edit_config": "Edit Config",
        "save": "Save",
        "cancel": "Cancel",
        "config_saved": "Configuration saved successfully. Reloading...",
        "save_failed": "Failed to save configuration: {}",
        "invalid_json": "Invalid JSON format: {}",
        "install_service": "Install Win Service",
        "uninstall_service": "Uninstall Win Service",
        "service_installed": "Service installed successfully.",
        "service_uninstalled": "Service uninstalled successfully.",
        "service_action_failed": "Service action failed: {}",
        "confirm_uninstall": "Are you sure you want to uninstall the Windows Service?",
        "confirm_install_stop_all": "This will stop all services in the list. Continue?",
        "import_config": "Import Config",
        "create_config": "Create Config",
        "select_config": "Select Configuration File",
        "config_loaded": "Configuration loaded successfully."
    },
    "zh": {
        "window_title": "微服务启动器",
        "init_error": "初始化错误",
        "loading": "正在加载，请稍候…",
        "service_list": "服务列表",
        "start": "启动",
        "stop": "停止",
        "restart": "重启",
        "filter": "过滤:",
        "all": "全部",
        "system": "系统",
        "clear_logs": "清空日志",
        "export": "导出",
        "keyword": "关键字",
        "start_all": "一键启动 (顺序)",
        "stop_all": "一键停止",
        "reload_config": "重载配置",
        "info": "提示",
        "error": "错误",
        "config_reloaded": "配置已重载 (参数已更新)。如增减服务请重启工具。",
        "reload_failed": "重载失败: {}",
        "logs_exported": "日志已导出至 exported_logs.txt",
        "export_failed": "导出失败: {}",
        "language": "语言",
        "edit_config": "编辑配置",
        "save": "保存",
        "cancel": "取消",
        "config_saved": "配置保存成功。正在重载...",
        "save_failed": "保存配置失败: {}",
        "invalid_json": "无效的 JSON 格式: {}",
        "install_service": "注册为服务",
        "uninstall_service": "卸载服务",
        "service_installed": "服务注册成功。",
        "service_uninstalled": "服务卸载成功。",
        "service_action_failed": "服务操作失败: {}",
        "confirm_uninstall": "确定要卸载 Windows 服务吗？",
        "confirm_install_stop_all": "将停止服务列表中的所有服务，是否继续？",
        "import_config": "导入配置",
        "create_config": "新增配置",
        "select_config": "选择配置文件",
        "config_loaded": "配置加载成功。"
        ,
        "insert_win_service_dep": "插入 Windows 服务依赖",
        "select_windows_service": "选择 Windows 服务",
        "select_and_insert": "选择并插入",
        "list_services_failed": "获取服务列表失败: {}"
    }
}

# Extend English keys to match new UI strings
TRANSLATIONS["en"].update({
    "insert_win_service_dep": "Insert Win Service Dep",
    "select_windows_service": "Select Windows Service",
    "select_and_insert": "Select & Insert",
    "list_services_failed": "Failed to list services: {}",
})

class I18nManager:
    def __init__(self, initial_lang="zh"):
        """
        初始化 I18nManager。
        Initialize I18nManager.
        """
        self.current_lang = initial_lang

    def set_language(self, lang):
        """
        设置当前语言。
        Set the current language.
        """
        if lang in TRANSLATIONS:
            self.current_lang = lang

    def get(self, key, *args):
        """
        获取翻译后的文本。
        Get translated text.
        """
        text = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"]).get(key, key)
        if args:
            return text.format(*args)
        return text

# Global instance
i18n = I18nManager()
