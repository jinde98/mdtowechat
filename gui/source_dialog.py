from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

class SourceDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HTML Source Code")
        self.setGeometry(150, 150, 800, 600)

        layout = QVBoxLayout(self)

        self.source_text = QTextEdit()
        self.source_text.setPlainText(html_content)
        self.source_text.setReadOnly(True)
        layout.addWidget(self.source_text)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        layout.addWidget(self.button_box)
