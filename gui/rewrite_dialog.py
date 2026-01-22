import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QPushButton, QDialogButtonBox, QMessageBox)
import yaml
import os

class RewriteDialog(QDialog):
    """
    一个用于收集用户AI改写指令的对话框。
    """
    def __init__(self, original_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用AI改写文章")
        self.setMinimumWidth(600)
        
        self.original_content = original_content
        self.config_path = 'config.yaml'
        self.config = self._load_config()

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """
        初始化对话框的用户界面。
        """
        layout = QVBoxLayout(self)

        # 1. 自定义要求输入框
        layout.addWidget(QLabel("你的改写要求 (例如：风格改为活泼、内容缩减一半):"))
        self.custom_prompt_input = QLineEdit()
        self.custom_prompt_input.setPlaceholderText("必填：请输入你本次改写的具体指令")
        layout.addWidget(self.custom_prompt_input)

        # 2. 系统级提示词编辑框
        layout.addWidget(QLabel("AI改写提示词 (System Prompt) - 可在“设置”中修改默认值:"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setMinimumHeight(100)
        layout.addWidget(self.system_prompt_input)

        # 3. 原文内容预览框
        layout.addWidget(QLabel("原文预览 (只读):"))
        self.original_content_preview = QTextEdit()
        self.original_content_preview.setPlainText(self.original_content)
        self.original_content_preview.setReadOnly(True)
        self.original_content_preview.setMinimumHeight(200)
        layout.addWidget(self.original_content_preview)

        # 4. 标准的OK/Cancel按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("开始改写")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_config(self):
        """
        从 `config.yaml` 加载配置。
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {} # 如果文件损坏，返回空字典
        return {}

    def _load_settings(self):
        """
        从加载的配置中读取 `rewrite_prompt` 并设置到UI控件中。
        """
        system_prompt = self.config.get('llm', {}).get('rewrite_prompt', '')
        self.system_prompt_input.setPlainText(system_prompt)

    def accept(self):
        """
        重写 `accept` 方法，在用户点击"OK"时进行校验。
        """
        # 确保用户填写了本次改写的具体要求
        if not self.custom_prompt_input.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入你的改写要求。")
            return  # 校验失败，阻止对话框关闭
        
        # 校验通过，调用父类的 accept 方法，这会让对话框的 exec_() 返回 QDialog.Accepted
        super().accept()

    def get_data(self):
        """
        这是对话框向外部返回数据的公共接口。
        它返回用户输入的自定义改写要求。
        注意：修改后的 System Prompt 也在此对话框的属性中，可以被外部访问。
        """
        return self.custom_prompt_input.text()
