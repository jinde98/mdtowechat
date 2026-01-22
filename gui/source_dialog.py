from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

class SourceDialog(QDialog):
    """
    一个简单的对话框，用于显示渲染后的HTML源代码。
    当用户在预览区右键点击并选择“显示源代码”时，会弹出此对话框。
    """
    def __init__(self, html_content, parent=None):
        """
        初始化源代码对话框。
        
        :param html_content: 要显示的HTML源代码字符串。
        :param parent: 父窗口。
        """
        super().__init__(parent)
        self.setWindowTitle("HTML 源代码")
        self.setGeometry(150, 150, 800, 600)  # 设置一个合适的默认尺寸和位置

        layout = QVBoxLayout(self)

        # 创建一个只读的文本编辑框来显示源代码
        self.source_text = QTextEdit()
        self.source_text.setPlainText(html_content)
        self.source_text.setReadOnly(True)  # 用户只能查看和复制，不能编辑
        # 为了更好的代码可读性，可以设置一个等宽字体
        self.source_text.setStyleSheet("font-family: 'Consolas', 'Monaco', 'Courier New', monospace;")
        layout.addWidget(self.source_text)

        # 添加一个标准的 "OK" 按钮来关闭对话框
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.button(QDialogButtonBox.Ok).setText("确定")
        self.button_box.accepted.connect(self.accept) # 连接 accepted 信号到 accept 槽
        layout.addWidget(self.button_box)
