import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def setup_logger():
    """
    配置并返回一个全局日志记录器 (Logger)。

    该函数实现了以下功能：
    1.  **分级日志**：将不同级别的日志输出到不同的目的地。
        - `INFO` 及以上级别的日志会被记录到 `logs/operation.log` 和控制台。
        - `ERROR` 及以上级别的日志会被额外记录到 `logs/error.log`。
    2.  **日志轮换**：使用 `TimedRotatingFileHandler`，日志文件会每天（午夜）自动切割，
        并保留最近30天的备份，防止日志文件无限增大。
    3.  **格式清晰**：为不同类型的日志设置了不同的格式。错误日志会包含文件名和行号，
        便于快速定位问题。
    4.  **防止重复记录**：在配置前会清空已有的处理器，避免因重复调用导致日志被多次记录。

    :return: 一个配置好的 `logging.Logger` 实例。
    """
    log_dir = "logs"  # 定义日志文件存放的目录
    if not os.path.exists(log_dir):  # 如果目录不存在，则自动创建
        os.makedirs(log_dir)

    # 获取名为 "MdToWeChat" 的主记录器实例。在整个应用中应使用同一个名称来获取记录器。
    logger = logging.getLogger("MdToWeChat")
    logger.setLevel(logging.INFO)  # 设置记录器处理的最低日志级别

    # 如果记录器已经有处理器，则清空它们，以防止重复添加和日志重复输出。
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- 1. 配置操作日志处理器 (用于记录普通信息) ---
    op_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器：将INFO及以上级别的日志写入 `operation.log`
    op_log_file = os.path.join(log_dir, "operation.log")
    # `when="midnight"`: 每天午夜进行轮换
    # `backupCount=30`: 保留30个备份文件
    op_handler = TimedRotatingFileHandler(op_log_file, when="midnight", interval=1, backupCount=30, encoding='utf-8')
    op_handler.setFormatter(op_formatter)
    op_handler.setLevel(logging.INFO)
    
    # --- 2. 配置错误日志处理器 (专门记录错误) ---
    err_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件处理器：将ERROR及以上级别的日志写入 `error.log`
    err_log_file = os.path.join(log_dir, "error.log")
    err_handler = TimedRotatingFileHandler(err_log_file, when="midnight", interval=1, backupCount=30, encoding='utf-8')
    err_handler.setFormatter(err_formatter)
    err_handler.setLevel(logging.ERROR)

    # --- 3. 配置控制台处理器 (用于在运行时实时查看日志) ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(op_formatter)  # 控制台使用和操作日志相同的格式
    console_handler.setLevel(logging.INFO)

    # --- 4. 将所有配置好的处理器添加到主记录器 ---
    logger.addHandler(op_handler)
    logger.addHandler(err_handler)
    logger.addHandler(console_handler)
    
    return logger

# 在模块加载时立即执行日志配置，并提供一个全局可访问的 `log` 实例。
# 其他模块可以通过 `from core.logger import log` 来直接使用这个配置好的记录器。
log = setup_logger()
