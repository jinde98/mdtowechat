import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
import os
import yaml
from core.logger import setup_logger
import logging

def create_default_config(config_path="config.yaml"):
    """
    创建默认的config.yaml文件，如果它不存在的话。
    """
    log = logging.getLogger("MdToWeChat") # 获取日志记录器实例。
    if not os.path.exists(config_path): # 如果配置文件不存在，则创建默认配置。
        default_config = {
            "DEFAULT_AUTHOR": "你的默认作者",
            "wechat": {
                "app_id": "your_wechat_app_id",
                "app_secret": "your_wechat_app_secret"
            },
            "DEFAULT_COVER_MEDIA_ID": "", # 预上传的默认封面图media_id
            "STORAGE_DAYS_TO_KEEP": 30
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f: # 允许写入Unicode字符。
                yaml.safe_dump(default_config, f, allow_unicode=True)
            log.info(f"Created default config.yaml at {config_path}") # 记录默认配置文件创建成功信息。
        except Exception as e:
            log.error(f"Error creating default config.yaml: {e}") # 记录创建默认配置文件失败信息。

if __name__ == "__main__": # 程序入口。
    # 首先设置日志记录器
    log = setup_logger()
    
    try:
        log.info("Application starting...") # 记录应用启动信息。
        # 将项目根目录添加到sys.path，以便正确导入模块
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # 确保data, logs, assets目录存在
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("assets", exist_ok=True)

        # 检查并创建默认config.yaml
        create_default_config()

        app = QApplication(sys.argv)
        
        # 设置全局字体大小，使其更舒适
        from PyQt5.QtGui import QFont
        default_font = QFont()
        default_font.setPointSize(11) # 可以根据需要调整大小
        app.setFont(default_font)

        main_window = MainWindow()
        main_window.show()
        log.info("MainWindow shown. Entering main event loop.") # 记录主窗口显示信息，进入主事件循环。
        sys.exit(app.exec_())
    except Exception as e:
        log.critical(f"Unhandled exception occurred: {e}", exc_info=True) # 记录未处理的异常信息。
        sys.exit(1)
