from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QLabel, QMessageBox
from core.template_manager import TemplateManager

class TemplateEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑模板") # 设置窗口标题。
        self.setMinimumSize(600, 500) # 设置最小尺寸。

        self.template_manager = TemplateManager()
        self.init_ui()
        self.load_templates()

    def init_ui(self):
        """初始化UI组件。"""
        layout = QVBoxLayout(self) # 创建垂直布局。

        # 头部模板
        layout.addWidget(QLabel("头部模板 (Markdown):")) # 头部模板标签。
        self.header_editor = QTextEdit() # 头部模板编辑器。
        self.header_editor.setPlaceholderText("在此输入头部模板内容...")
        layout.addWidget(self.header_editor)

        # 尾部模板
        layout.addWidget(QLabel("尾部模板 (Markdown):")) # 尾部模板标签。
        self.footer_editor = QTextEdit() # 尾部模板编辑器。
        self.footer_editor.setPlaceholderText("在此输入尾部模板内容...")
        layout.addWidget(self.footer_editor)

        # 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel) # 保存和取消按钮。
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_templates(self):
        """加载现有模板到编辑器中。"""
        header, footer = self.template_manager.get_templates()
        self.header_editor.setPlainText(header)
        self.footer_editor.setPlainText(footer)

    def accept(self):
        """保存模板并关闭对话框。"""
        header_content = self.header_editor.toPlainText()
        footer_content = self.footer_editor.toPlainText()
        
        success, error_message = self.template_manager.save_templates(header_content, footer_content)
        
        if success: # 如果保存成功。
            QMessageBox.information(self, "成功", "模板已成功保存！")
            super().accept()
        else: # 如果保存失败。
            QMessageBox.critical(self, "错误", f"保存模板失败: {error_message}")

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = TemplateEditorDialog()
    if dialog.exec_():
        print("Templates were saved.")
    else:
        print("Template editing was cancelled.")
    sys.exit()
