import yaml
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QDialogButtonBox, QMessageBox)

class SettingsDialog(QDialog):
    def __init__(self, config_path="config.yaml", parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.config_path = config_path
        self.config_data = self._load_config()

        self._init_ui()
        self._populate_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.app_id_edit = QLineEdit()
        self.app_secret_edit = QLineEdit()
        self.app_secret_edit.setEchoMode(QLineEdit.Password)
        self.author_edit = QLineEdit()

        form_layout.addRow("微信AppID:", self.app_id_edit)
        form_layout.addRow("微信AppSecret:", self.app_secret_edit)
        form_layout.addRow("默认作者:", self.author_edit)

        layout.addLayout(form_layout)

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
        wechat_config = self.config_data.get("wechat", {})
        self.app_id_edit.setText(wechat_config.get("app_id", ""))
        self.app_secret_edit.setText(wechat_config.get("app_secret", ""))
        self.author_edit.setText(self.config_data.get("DEFAULT_AUTHOR", ""))

    def accept(self):
        # Update the dictionary with new values
        self.config_data.setdefault("wechat", {})['app_id'] = self.app_id_edit.text().strip()
        self.config_data['wechat']['app_secret'] = self.app_secret_edit.text().strip()
        self.config_data['DEFAULT_AUTHOR'] = self.author_edit.text().strip()

        # Save back to YAML file
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, allow_unicode=True, default_flow_style=False)
            QMessageBox.information(self, "成功", "设置已保存。")
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
