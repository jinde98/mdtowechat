import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
import os
import yaml
from core.logger import setup_logger
import logging

def create_default_config(config_path="config.yaml"):
    """
    如果 config.yaml 文件不存在，则创建一个默认的配置文件。
    这样做可以避免在首次启动时因缺少配置文件而引发错误，并为用户提供一个清晰的配置模板。
    """
    log = logging.getLogger("MdToWeChat")  # 获取日志记录器实例
    if not os.path.exists(config_path):  # 检查配置文件是否存在
        default_config = {
            "DEFAULT_AUTHOR": "你的默认作者",
            "wechat": {
                "app_id": "your_wechat_app_id",
                "app_secret": "your_wechat_app_secret"
            },
            "DEFAULT_COVER_MEDIA_ID": "",  # 预上传的默认封面图media_id
            "STORAGE_DAYS_TO_KEEP": 30
        }
        try:
            # 使用 'w' 模式创建并写入文件，encoding='utf-8' 支持中文字符
            with open(config_path, "w", encoding="utf-8") as f:
                # allow_unicode=True 确保YAML文件能正确显示中文
                yaml.safe_dump(default_config, f, allow_unicode=True)
            log.info(f"已在 {config_path} 创建默认的 config.yaml 文件。")
        except Exception as e:
            log.error(f"创建默认的 config.yaml 文件时出错: {e}")

if __name__ == "__main__":  # 程序的唯一入口点
    # 步骤1: 初始化日志记录器
    # 这是整个应用程序启动的第一步，确保所有后续操作都能被记录下来。
    log = setup_logger()
    
    try:
        log.info("应用程序开始启动...")
        
        # 步骤2: 设置项目根目录到系统路径
        # 这确保了无论从哪里运行main.py，所有模块（如core, gui）都能被正确导入。
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # 步骤3: 确保核心目录存在
        # 这些是存放数据、日志和静态资源的文件夹，程序运行所必需。
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("assets", exist_ok=True)

        # 步骤4: 检查并创建默认配置文件
        create_default_config()

        # 步骤5: 初始化PyQt应用程序
        app = QApplication(sys.argv)

        # 步骤6: 设置应用程序的视觉元素
        # 设置图标
        from PyQt5.QtGui import QIcon
        app.setWindowIcon(QIcon('assets/icon.png'))
        
        # 设置全局默认字体大小，以提高UI的可读性
        from PyQt5.QtGui import QFont
        default_font = QFont()
        default_font.setPointSize(11)  # 11号字体在大多数屏幕上看起来很舒适
        app.setFont(default_font)

        # 步骤7: 创建并显示主窗口
        main_window = MainWindow()
        main_window.show()
        log.info("主窗口已显示。进入Qt主事件循环。")
        
        # 步骤8: 启动事件循环
        # app.exec_() 会阻塞程序，直到用户关闭主窗口。
        # sys.exit() 确保程序能干净地退出。
        sys.exit(app.exec_())
        
    except Exception as e:
        # 顶层异常捕获：这是最后的防线，防止任何未被捕获的异常导致程序闪退。
        log.critical(f"发生未处理的致命错误: {e}", exc_info=True)
        sys.exit(1)
