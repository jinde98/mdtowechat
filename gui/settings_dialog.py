from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QDialogButtonBox, QMessageBox, QGroupBox, QTextEdit)
from core.config import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(600)
        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.config # 获取当前配置的副本

        self._init_ui()
        self._populate_data()

    def _init_ui(self):
        layout = QVBoxLayout(self) # 初始化UI布局。
        # Wechat Settings
        wechat_group = QGroupBox("微信公众号设置")
        wechat_layout = QFormLayout()
        self.app_id_edit = QLineEdit()
        self.app_secret_edit = QLineEdit()
        self.app_secret_edit.setEchoMode(QLineEdit.Password)
        self.author_edit = QLineEdit()
        wechat_layout.addRow("微信AppID:", self.app_id_edit)
        wechat_layout.addRow("微信AppSecret:", self.app_secret_edit)
        wechat_layout.addRow("默认作者:", self.author_edit)
        wechat_group.setLayout(wechat_layout)
        layout.addWidget(wechat_group)

        # Jina Settings
        jina_group = QGroupBox("Jina AI Reader 设置")
        jina_layout = QFormLayout()
        self.jina_api_key_edit = QLineEdit()
        self.jina_api_key_edit.setEchoMode(QLineEdit.Password)
        self.jina_api_key_edit.setPlaceholderText("在此输入您的 Jina API 密钥")
        jina_layout.addRow("Jina API 密钥:", self.jina_api_key_edit)
        jina_group.setLayout(jina_layout)
        layout.addWidget(jina_group)

        # LLM Settings
        llm_group = QGroupBox("大语言模型 (LLM) 设置 (OpenAI 兼容)")
        llm_layout = QFormLayout()
        self.llm_api_key_edit = QLineEdit()
        self.llm_api_key_edit.setEchoMode(QLineEdit.Password)
        self.llm_base_url_edit = QLineEdit()
        self.llm_base_url_edit.setPlaceholderText("例如：https://api.openai.com/v1")
        self.llm_model_edit = QLineEdit()
        self.llm_model_edit.setPlaceholderText("例如：gpt-4-turbo")
        self.llm_system_prompt_edit = QTextEdit()
        self.llm_system_prompt_edit.setMinimumHeight(120)
        llm_layout.addRow("API 密钥:", self.llm_api_key_edit)
        llm_layout.addRow("API 地址:", self.llm_base_url_edit)
        llm_layout.addRow("模型名称:", self.llm_model_edit)
        llm_layout.addRow("系统提示词:", self.llm_system_prompt_edit)
        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

        button_box = QDialogButtonBox()
        save_button = button_box.addButton("保存", QDialogButtonBox.AcceptRole)
        cancel_button = button_box.addButton("取消", QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_data(self):
        # 使用 config_manager.get() 来安全地获取嵌套值
        self.app_id_edit.setText(self.config_manager.get("wechat.app_id", ""))
        self.app_secret_edit.setText(self.config_manager.get("wechat.app_secret", ""))
        self.author_edit.setText(self.config_manager.get("wechat.default_author", ""))
        
        self.jina_api_key_edit.setText(self.config_manager.get("jina.api_key", ""))

        self.llm_api_key_edit.setText(self.config_manager.get("llm.api_key", ""))
        self.llm_base_url_edit.setText(self.config_manager.get("llm.base_url", ""))
        self.llm_model_edit.setText(self.config_manager.get("llm.model", ""))
        self.llm_system_prompt_edit.setPlainText(self.config_manager.get("llm.system_prompt", ""))

    def accept(self):
        # 使用新值更新配置字典。
        # Update WeChat config
        wechat_config = self.config_data.setdefault("wechat", {})
        wechat_config['app_id'] = self.app_id_edit.text().strip()
        wechat_config['app_secret'] = self.app_secret_edit.text().strip()
        wechat_config['default_author'] = self.author_edit.text().strip()

        # Update Jina config
        jina_config = self.config_data.setdefault("jina", {})
        jina_config['api_key'] = self.jina_api_key_edit.text().strip()

        # Update LLM config
        llm_config = self.config_data.setdefault("llm", {})
        llm_config['api_key'] = self.llm_api_key_edit.text().strip()
        llm_config['base_url'] = self.llm_base_url_edit.text().strip()
        llm_config['model'] = self.llm_model_edit.text().strip()
        llm_config['system_prompt'] = self.llm_system_prompt_edit.toPlainText().strip()
        
        # **自动清理废弃的顶层'DEFAULT_AUTHOR'字段**
        if 'DEFAULT_AUTHOR' in self.config_data:
            del self.config_data['DEFAULT_AUTHOR']

        # 使用ConfigManager保存配置
        try:
            self.config_manager.save(self.config_data)
            QMessageBox.information(self, "成功", "设置已保存。")
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
