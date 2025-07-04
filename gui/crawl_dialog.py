import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QPushButton, QDialogButtonBox, QCheckBox, QMessageBox)
import yaml
import os

class CrawlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("从网页抓取内容")
        self.setMinimumWidth(500)
        
        self.config_path = 'config.yaml'
        self.config = self._load_config()

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("网页URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入要抓取的网页地址")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # AI提示词预览
        layout.addWidget(QLabel("AI处理提示词 (System Prompt) - 只读预览:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setMinimumHeight(150)
        self.prompt_input.setReadOnly(True) # 设置为只读
        layout.addWidget(self.prompt_input)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def _load_settings(self):
        # 加载System Prompt
        system_prompt = self.config.get('llm', {}).get('system_prompt', '')
        if not system_prompt:
            self.prompt_input.setPlaceholderText("请先在“设置”中配置'llm.system_prompt'")
            # 考虑禁用OK按钮，如果prompt为空
            # self.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.prompt_input.setPlainText(system_prompt)

    def accept(self):
        if not self.url_input.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入有效的网页URL。")
            return
        
        if not self.prompt_input.toPlainText().strip():
            QMessageBox.warning(self, "配置错误", "System Prompt为空，请先在“设置”中配置。")
            return

        super().accept()

    def get_data(self):
        # Jina API Key不再从这个对话框获取
        return (self.url_input.text(),
                self.prompt_input.toPlainText())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = CrawlDialog()
    if dialog.exec_() == QDialog.Accepted:
        print(dialog.get_data())
    sys.exit(app.exec_())