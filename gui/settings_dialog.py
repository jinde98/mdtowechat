import yaml
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QDialogButtonBox, QMessageBox, QGroupBox, QTextEdit)

class SettingsDialog(QDialog):
    def __init__(self, config_path="config.yaml", parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置") # 设置窗口标题。
        self.config_path = config_path
        self.config_data = self._load_config()

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
        jina_layout.addRow("Jina API Key:", self.jina_api_key_edit)
        jina_group.setLayout(jina_layout)
        layout.addWidget(jina_group)

        # LLM Settings
        llm_group = QGroupBox("大语言模型 (LLM) 设置")
        llm_layout = QFormLayout()
        self.llm_api_key_edit = QLineEdit()
        self.llm_api_key_edit.setEchoMode(QLineEdit.Password)
        self.llm_base_url_edit = QLineEdit()
        self.llm_model_edit = QLineEdit()
        self.llm_system_prompt_edit = QTextEdit()
        self.llm_system_prompt_edit.setMinimumHeight(120)
        llm_layout.addRow("API Key:", self.llm_api_key_edit)
        llm_layout.addRow("Base URL:", self.llm_base_url_edit)
        llm_layout.addRow("Model:", self.llm_model_edit)
        llm_layout.addRow("System Prompt:", self.llm_system_prompt_edit)
        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def _populate_data(self):
        # Populate WeChat data
        wechat_config = self.config_data.get("wechat", {})
        self.app_id_edit.setText(wechat_config.get("app_id", ""))
        self.app_secret_edit.setText(wechat_config.get("app_secret", ""))
        self.author_edit.setText(wechat_config.get("default_author", ""))

        # Populate Jina data
        jina_config = self.config_data.get("jina", {})
        self.jina_api_key_edit.setText(jina_config.get("api_key", ""))

        # Populate LLM data
        llm_config = self.config_data.get("llm", {})
        self.llm_api_key_edit.setText(llm_config.get("api_key", ""))
        self.llm_base_url_edit.setText(llm_config.get("base_url", ""))
        self.llm_model_edit.setText(llm_config.get("model", ""))
        self.llm_system_prompt_edit.setPlainText(llm_config.get("system_prompt", ""))

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

        # 将配置保存回YAML文件。
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, allow_unicode=True, default_flow_style=False)
            QMessageBox.information(self, "成功", "设置已保存。")
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
