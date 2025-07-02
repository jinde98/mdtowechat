# gui/status_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt5.QtCore import Qt

class StatusDialog(QDialog):
    """一个简单的对话框，用于显示操作状态（如“处理中”、“成功”、“失败”）。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("发布状态")
        self.setMinimumWidth(350)
        # 设置为模态对话框，但在显示后需要立即处理事件以避免UI冻结
        self.setModal(True) 

        self.layout = QVBoxLayout(self)
        
        self.message_label = QLabel("正在发布，请稍候...")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.layout.addWidget(self.message_label)

        self.button_box = QDialogButtonBox()
        self.layout.addWidget(self.button_box)

    def update_status(self, message, is_finished=False):
        """
        更新对话框显示的消息。
        如果操作完成，则添加一个关闭按钮。
        """
        self.message_label.setText(message)
        if is_finished:
            self.setWindowTitle("发布完成")
            close_button = self.button_box.addButton(QDialogButtonBox.Close)
            close_button.clicked.connect(self.accept)
