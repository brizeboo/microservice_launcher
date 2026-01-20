import logging
import os
import datetime
from logging.handlers import TimedRotatingFileHandler
import queue

class LogManager:
    def __init__(self):
        """
        初始化 LogManager。
        Initialize LogManager.
        """
        self.loggers = {}
        self.gui_log_queue = queue.Queue() # Queue for GUI updates
        try:
            import logging as _logging
            self._default_level = _logging.INFO
        except Exception:
            self._default_level = 20

    def set_default_level(self, level_str):
        try:
            import logging as _logging
            lvl = str(level_str).upper() if level_str is not None else "INFO"
            if lvl in ("WARN", "WARNING"):
                self._default_level = _logging.WARNING
            elif lvl == "ERROR":
                self._default_level = _logging.ERROR
            elif lvl == "DEBUG":
                self._default_level = _logging.DEBUG
            else:
                self._default_level = _logging.INFO
        except Exception:
            pass
    def get_default_level_str(self):
        try:
            import logging as _logging
            if self._default_level == _logging.DEBUG:
                return "DEBUG"
            if self._default_level == _logging.ERROR:
                return "ERROR"
            if self._default_level == _logging.WARNING:
                return "WARN"
            return "INFO"
        except Exception:
            return "INFO"

    def get_logger(self, service_name, log_path):
        """
        获取或创建指定服务的 logger。
        Get or create a logger for a specific service.
        """
        if service_name in self.loggers:
            return self.loggers[service_name]

        logger = logging.getLogger(service_name)
        try:
            logger.setLevel(self._default_level)
        except Exception:
            logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        # Ensure log directory exists
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError:
                pass # Handle error if needed

        # 文件处理器 - 按天轮转 (午夜)
        # File Handler - Rotate by day (midnight)
        file_handler = TimedRotatingFileHandler(
            log_path, when="midnight", interval=1, backupCount=7, encoding='utf-8'
        )
        file_handler.suffix = "%Y-%m-%d"
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        self.loggers[service_name] = logger
        return logger

    def log(self, service_name, level, message):
        """
        将消息记录到文件并放入 GUI 队列。
        Log a message to file and queue for GUI.
        """
        logger = self.loggers.get(service_name)
        normalized_level = "INFO"
        if isinstance(level, str) and level:
            normalized_level = level.upper()
        if logger:
            msg_str = str(message)
            if normalized_level == "INFO":
                logger.info(msg_str)
            elif normalized_level == "ERROR":
                logger.error(msg_str)
            elif normalized_level in ("WARN", "WARNING"):
                logger.warning(msg_str)
            elif normalized_level == "DEBUG":
                logger.debug(msg_str)
            else:
                logger.info(msg_str)
            
        
        # 格式化 GUI 显示: 时间戳 | 服务 | 级别 | 消息
        # Format for GUI: Timestamp | Service | Level | Message
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{service_name}] [{normalized_level}] {message}"
        self.gui_log_queue.put((service_name, formatted_msg))

    def get_gui_logs(self):
        """
        检索所有待处理的 GUI 日志。
        Retrieve all pending logs for GUI update.
        """
        logs = []
        try:
            while True:
                logs.append(self.gui_log_queue.get_nowait())
        except queue.Empty:
            pass
        return logs
