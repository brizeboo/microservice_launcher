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

    def get_logger(self, service_name, log_path):
        """
        获取或创建指定服务的 logger。
        Get or create a logger for a specific service.
        """
        if service_name in self.loggers:
            return self.loggers[service_name]

        logger = logging.getLogger(service_name)
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
        if logger:
            if level == "INFO":
                logger.info(message)
            elif level == "ERROR":
                logger.error(message)
            elif level == "WARN":
                logger.warning(message)
        
        # 格式化 GUI 显示: 时间戳 | 服务 | 级别 | 消息
        # Format for GUI: Timestamp | Service | Level | Message
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{service_name}] [{level}] {message}"
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
