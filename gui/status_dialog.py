# gui/status_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt5.QtCore import Qt

class StatusDialog(QDialog):
    """
    一个简单的模态对话框，用于在执行长耗时任务（如发布、AI处理）时，
    向用户显示当前的操作状态。
    """
    def __init__(self, title="操作状态", parent=None):
        """
        初始化状态对话框。
        
        :param title: 对话框的初始标题。
        :param parent: 父窗口。
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        # 设置为模态对话框，会阻塞父窗口的交互，但允许通过信号槽更新自身内容。
        self.setModal(True)

        self.layout = QVBoxLayout(self)
        
        # 用于显示状态信息的标签
        self.message_label = QLabel("正在处理，请稍候...")
        self.message_label.setAlignment(Qt.AlignCenter) # 文本居中
        self.message_label.setWordWrap(True) # 自动换行
        self.layout.addWidget(self.message_label)

        # 用于放置完成后的关闭按钮
        self.button_box = QDialogButtonBox()
        self.layout.addWidget(self.button_box)

    def update_status(self, message, is_finished=False):
        """
        更新对话框显示的状态消息。
        这是从外部（通常是Worker线程的信号）调用的核心方法。
        
        :param message: 要显示的新状态文本。
        :param is_finished: 一个布尔值，指示操作是否已完成。
        """
        self.message_label.setText(message)
        
        # 如果操作已完成，则动态添加一个“关闭”按钮
        if is_finished:
            self.setWindowTitle("操作完成")
            # 清空可能已存在的按钮，以防重复添加
            self.button_box.clear()
            close_button = self.button_box.addButton(QDialogButtonBox.Close)
            close_button.setText("关闭")
            close_button.clicked.connect(self.accept) # 点击按钮时关闭对话框
