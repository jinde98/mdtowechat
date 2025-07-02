import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def setup_logger():
    """
    配置全局日志记录器。
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建一个主记录器
    logger = logging.getLogger("MdToWeChat")
    logger.setLevel(logging.INFO)

    # 防止重复添加处理器
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- 操作日志处理器 ---
    op_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # 操作日志文件处理器 (按天轮换)
    op_log_file = os.path.join(log_dir, "operation.log")
    op_handler = TimedRotatingFileHandler(op_log_file, when="midnight", interval=1, backupCount=30, encoding='utf-8')
    op_handler.setFormatter(op_formatter)
    op_handler.setLevel(logging.INFO)
    
    # --- 错误日志处理器 ---
    err_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 错误日志文件处理器 (按天轮换)
    err_log_file = os.path.join(log_dir, "error.log")
    err_handler = TimedRotatingFileHandler(err_log_file, when="midnight", interval=1, backupCount=30, encoding='utf-8')
    err_handler.setFormatter(err_formatter)
    err_handler.setLevel(logging.ERROR)

    # --- 控制台处理器 ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(op_formatter)
    console_handler.setLevel(logging.INFO)

    # 将处理器添加到记录器
    logger.addHandler(op_handler)
    logger.addHandler(err_handler)
    logger.addHandler(console_handler)
    
    return logger

# 获取一个已配置的记录器实例
log = setup_logger()