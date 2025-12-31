from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QLabel, QMessageBox
from core.template_manager import TemplateManager

class TemplateEditorDialog(QDialog):
    """
    一个用于编辑页眉和页脚 Markdown 模板的对话框。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑模板")
        self.setMinimumSize(600, 500)

        # 创建一个 TemplateManager 实例来处理文件的读写
        self.template_manager = TemplateManager()
        self._init_ui()
        self._load_templates()

    def _init_ui(self):
        """
        初始化对话框的用户界面。
        """
        layout = QVBoxLayout(self)

        # --- 页眉模板编辑区 ---
        layout.addWidget(QLabel("页眉模板 (Markdown):"))
        self.header_editor = QTextEdit()
        self.header_editor.setPlaceholderText("在此输入将添加到每篇文章顶部的通用内容...")
        layout.addWidget(self.header_editor)

        # --- 页脚模板编辑区 ---
        layout.addWidget(QLabel("页脚模板 (Markdown):"))
        self.footer_editor = QTextEdit()
        self.footer_editor.setPlaceholderText("在此输入将添加到每篇文章底部的通用内容，例如引导关注、版权声明等...")
        layout.addWidget(self.footer_editor)

        # --- 底部按钮 ---
        # 使用标准的 Save 和 Cancel 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText("保存")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")
        self.button_box.accepted.connect(self.accept) # "Save" 按钮连接到 accept 槽
        self.button_box.rejected.connect(self.reject) # "Cancel" 按钮连接到 reject 槽
        layout.addWidget(self.button_box)

    def _load_templates(self):
        """
        从 TemplateManager 加载当前的模板内容并填充到编辑器中。
        """
        header, footer = self.template_manager.get_templates()
        self.header_editor.setPlainText(header)
        self.footer_editor.setPlainText(footer)

    def accept(self):
        """
        当用户点击“保存”按钮时被调用。
        此方法负责将UI中的内容写回模板文件。
        """
        header_content = self.header_editor.toPlainText()
        footer_content = self.footer_editor.toPlainText()
        
        # 调用 TemplateManager 来执行实际的文件保存操作
        success, error_message = self.template_manager.save_templates(header_content, footer_content)
        
        if success:
            QMessageBox.information(self, "成功", "模板已成功保存！")
            super().accept()  # 保存成功后关闭对话框
        else:
            QMessageBox.critical(self, "错误", f"保存模板失败: {error_message}")
            # 保存失败时，不关闭对话框，让用户可以重试或取消
