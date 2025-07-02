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
    log = logging.getLogger("MdToWeChat")
    if not os.path.exists(config_path):
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
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(default_config, f, allow_unicode=True)
            log.info(f"Created default config.yaml at {config_path}")
        except Exception as e:
            log.error(f"Error creating default config.yaml: {e}")

if __name__ == "__main__":
    # 首先设置日志记录器
    log = setup_logger()
    
    try:
        log.info("Application starting...")
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
        log.info("MainWindow shown. Entering main event loop.")
        sys.exit(app.exec_())
    except Exception as e:
        log.critical(f"Unhandled exception occurred: {e}", exc_info=True)
        sys.exit(1)
