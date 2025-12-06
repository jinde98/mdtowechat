import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QPushButton, QDialogButtonBox, QMessageBox)
import yaml
import os

class RewriteDialog(QDialog):
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
        layout = QVBoxLayout(self)

        # Custom Prompt
        layout.addWidget(QLabel("你的改写要求 (例如：风格改为活泼、内容缩减一半):"))
        self.custom_prompt_input = QLineEdit()
        self.custom_prompt_input.setPlaceholderText("请输入你的具体改写指令")
        layout.addWidget(self.custom_prompt_input)

        # System Prompt
        layout.addWidget(QLabel("AI改写提示词 (System Prompt) - 可在设置中修改:"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setMinimumHeight(100)
        layout.addWidget(self.system_prompt_input)

        # Original Content Preview
        layout.addWidget(QLabel("原文预览 (只读):"))
        self.original_content_preview = QTextEdit()
        self.original_content_preview.setPlainText(self.original_content)
        self.original_content_preview.setReadOnly(True)
        self.original_content_preview.setMinimumHeight(200)
        layout.addWidget(self.original_content_preview)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("开始改写")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def _load_settings(self):
        system_prompt = self.config.get('llm', {}).get('rewrite_prompt', '')
        self.system_prompt_input.setPlainText(system_prompt)
        # Even if the prompt is empty, the user can still edit it, so we don't disable the OK button.
        # if not system_prompt:
        #     self.system_prompt_input.setPlaceholderText("请先在“设置”中配置 'llm.rewrite_prompt'")
        #     self.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).setEnabled(False)
        # else:
        #     self.system_prompt_input.setPlainText(system_prompt)

    def accept(self):
        if not self.custom_prompt_input.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入你的改写要求。")
            return
        super().accept()

    def get_data(self):
        return self.custom_prompt_input.text()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    sample_content = """# 原始标题

这是原始的文章内容。
- 列表一
- 列表二
"""
    dialog = RewriteDialog(sample_content)
    if dialog.exec_() == QDialog.Accepted:
        print("改写要求:", dialog.get_data())
    sys.exit(app.exec_())
