from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QDialogButtonBox, QMessageBox, QGroupBox, QTextEdit)
from core.config import ConfigManager

class SettingsDialog(QDialog):
    """
    应用程序的设置对话框。
    提供一个集中的界面，用于修改存储在 `config.yaml` 文件中的所有配置。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(600)
        
        # 获取全局唯一的配置管理器实例
        self.config_manager = ConfigManager()
        # 获取当前配置的一个深层副本，我们将在副本上进行修改，只有在保存时才真正更新。
        self.config_data = self.config_manager.config.copy()

        self._init_ui()
        self._populate_data()

    def _init_ui(self):
        """
        初始化用户界面，使用 QGroupBox 对设置项进行分组。
        """
        layout = QVBoxLayout(self)
        
        # --- 微信公众号设置 ---
        wechat_group = QGroupBox("微信公众号设置")
        wechat_layout = QFormLayout()
        self.app_id_edit = QLineEdit()
        self.app_secret_edit = QLineEdit()
        self.app_secret_edit.setEchoMode(QLineEdit.Password) # 隐藏敏感信息
        self.author_edit = QLineEdit()
        wechat_layout.addRow("微信AppID:", self.app_id_edit)
        wechat_layout.addRow("微信AppSecret:", self.app_secret_edit)
        wechat_layout.addRow("默认作者:", self.author_edit)
        wechat_group.setLayout(wechat_layout)
        layout.addWidget(wechat_group)

        # --- Jina AI 设置 ---
        jina_group = QGroupBox("Jina AI Reader 设置 (用于抓取网页)")
        jina_layout = QFormLayout()
        self.jina_api_key_edit = QLineEdit()
        self.jina_api_key_edit.setEchoMode(QLineEdit.Password)
        self.jina_api_key_edit.setPlaceholderText("可选，填入可提高抓取稳定性")
        jina_layout.addRow("Jina API 密钥:", self.jina_api_key_edit)
        jina_group.setLayout(jina_layout)
        layout.addWidget(jina_group)

        # --- 大语言模型（LLM）设置 ---
        llm_group = QGroupBox("大语言模型(LLM)设置 (兼容OpenAI接口)")
        llm_layout = QFormLayout()
        self.llm_api_key_edit = QLineEdit()
        self.llm_api_key_edit.setEchoMode(QLineEdit.Password)
        self.llm_base_url_edit = QLineEdit()
        self.llm_base_url_edit.setPlaceholderText("例如：https://api.openai.com/v1")
        self.llm_model_edit = QLineEdit()
        self.llm_model_edit.setPlaceholderText("例如：gpt-4-turbo")
        self.llm_system_prompt_edit = QTextEdit()
        self.llm_system_prompt_edit.setMinimumHeight(100)
        self.llm_rewrite_prompt_edit = QTextEdit()
        self.llm_rewrite_prompt_edit.setMinimumHeight(100)

        llm_layout.addRow("API 密钥:", self.llm_api_key_edit)
        llm_layout.addRow("API 地址 (Base URL):", self.llm_base_url_edit)
        llm_layout.addRow("模型名称 (Model):", self.llm_model_edit)
        llm_layout.addRow("抓取文章处理提示词:", self.llm_system_prompt_edit)
        llm_layout.addRow("AI改写默认提示词:", self.llm_rewrite_prompt_edit)
        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

        # --- 底部按钮 ---
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Save).setText("保存")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_data(self):
        """
        从配置管理器中读取当前的配置值，并填充到UI控件中。
        """
        # 使用 config_manager.get() 可以安全地处理可能不存在的嵌套键
        self.app_id_edit.setText(self.config_manager.get("wechat.app_id", ""))
        self.app_secret_edit.setText(self.config_manager.get("wechat.app_secret", ""))
        self.author_edit.setText(self.config_manager.get("wechat.default_author", ""))
        
        self.jina_api_key_edit.setText(self.config_manager.get("jina.api_key", ""))

        self.llm_api_key_edit.setText(self.config_manager.get("llm.api_key", ""))
        self.llm_base_url_edit.setText(self.config_manager.get("llm.base_url", ""))
        self.llm_model_edit.setText(self.config_manager.get("llm.model", ""))
        self.llm_system_prompt_edit.setPlainText(self.config_manager.get("llm.system_prompt", ""))
        self.llm_rewrite_prompt_edit.setPlainText(self.config_manager.get("llm.rewrite_prompt", ""))

    def accept(self):
        """
        当用户点击“保存”按钮时被调用。
        此方法负责将UI控件中的新值写回配置字典，并调用ConfigManager进行持久化。
        """
        # 使用 setdefault 确保即使原始配置中没有某个键（如'wechat'），也能正常处理
        wechat_config = self.config_data.setdefault("wechat", {})
        wechat_config['app_id'] = self.app_id_edit.text().strip()
        wechat_config['app_secret'] = self.app_secret_edit.text().strip()
        wechat_config['default_author'] = self.author_edit.text().strip()

        jina_config = self.config_data.setdefault("jina", {})
        jina_config['api_key'] = self.jina_api_key_edit.text().strip()

        llm_config = self.config_data.setdefault("llm", {})
        llm_config['api_key'] = self.llm_api_key_edit.text().strip()
        llm_config['base_url'] = self.llm_base_url_edit.text().strip()
        llm_config['model'] = self.llm_model_edit.text().strip()
        llm_config['system_prompt'] = self.llm_system_prompt_edit.toPlainText().strip()
        llm_config['rewrite_prompt'] = self.llm_rewrite_prompt_edit.toPlainText().strip()
        
        # 这是一个很好的向后兼容处理：如果旧的顶层'DEFAULT_AUTHOR'字段还存在，就将其删除。
        if 'DEFAULT_AUTHOR' in self.config_data:
            del self.config_data['DEFAULT_AUTHOR']

        try:
            # 调用配置管理器的 save 方法，将更新后的字典写回 config.yaml 文件
            self.config_manager.save(self.config_data)
            QMessageBox.information(self, "成功", "设置已成功保存。")
            # 调用父类的 accept，关闭对话框并返回 QDialog.Accepted
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
