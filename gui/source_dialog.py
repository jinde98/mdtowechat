from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

class SourceDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HTML 源代码") # 设置窗口标题为“HTML 源代码”。
        self.setGeometry(150, 150, 800, 600) # 设置窗口初始位置和大小。

        layout = QVBoxLayout(self) # 创建垂直布局。

        self.source_text = QTextEdit() # 创建文本编辑框显示源代码。
        self.source_text.setPlainText(html_content) # 设置文本内容。
        self.source_text.setReadOnly(True) # 设置为只读。
        layout.addWidget(self.source_text)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok) # 创建确定按钮。
        self.button_box.accepted.connect(self.accept)
        layout.addWidget(self.button_box)
