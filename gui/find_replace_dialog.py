from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QCheckBox, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextDocument, QTextCursor

class FindReplaceDialog(QDialog):
    """
    查找和替换对话框 (非模态)。
    允许用户在 Markdown 编辑器中查找和替换文本。
    """
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("查找和替换")
        self.setModal(False) # 设置为非模态，允许用户同时操作编辑器
        self.setFixedSize(400, 250)
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 输入区域
        input_group = QGroupBox()
        input_layout = QVBoxLayout()
        
        # 查找
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("查找内容:"))
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self._update_buttons)
        find_layout.addWidget(self.find_input)
        input_layout.addLayout(find_layout)

        # 替换
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("替换为:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        input_layout.addLayout(replace_layout)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # 选项区域
        options_layout = QHBoxLayout()
        self.case_sensitive_check = QCheckBox("区分大小写")
        self.whole_words_check = QCheckBox("全字匹配")
        self.backward_check = QCheckBox("向上查找")
        
        options_layout.addWidget(self.case_sensitive_check)
        options_layout.addWidget(self.whole_words_check)
        options_layout.addWidget(self.backward_check)
        layout.addLayout(options_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        self.find_next_btn = QPushButton("查找下一个")
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_next_btn.setDefault(True)
        
        self.replace_btn = QPushButton("替换")
        self.replace_btn.clicked.connect(self.replace)
        
        self.replace_all_btn = QPushButton("全部替换")
        self.replace_all_btn.clicked.connect(self.replace_all)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.find_next_btn)
        btn_layout.addWidget(self.replace_btn)
        btn_layout.addWidget(self.replace_all_btn)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self._update_buttons()

    def _update_buttons(self):
        has_text = bool(self.find_input.text())
        self.find_next_btn.setEnabled(has_text)
        self.replace_btn.setEnabled(has_text)
        self.replace_all_btn.setEnabled(has_text)

    def _get_find_flags(self):
        flags = QTextDocument.FindFlags()
        if self.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.whole_words_check.isChecked():
            flags |= QTextDocument.FindWholeWords
        if self.backward_check.isChecked():
            flags |= QTextDocument.FindBackward
        return flags

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return False
            
        flags = self._get_find_flags()
        
        # 执行查找
        found = self.editor.find(text, flags)
        
        if not found:
            # 如果没找到，且不是反向查找，尝试从头开始
            # 如果是反向查找，尝试从尾部开始
            cursor = self.editor.textCursor()
            if self.backward_check.isChecked():
                cursor.movePosition(QTextCursor.End)
            else:
                cursor.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            
            # 再次尝试查找
            found = self.editor.find(text, flags)
            
            if not found:
                QMessageBox.information(self, "查找", f"找不到 \"{text}\"")
        
        return found

    def replace(self):
        # 检查当前选中的文本是否匹配查找内容
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()
        find_text = self.find_input.text()
        
        # 简单的匹配检查 (忽略大小写选项的复杂逻辑，依赖 find_next 定位)
        if not cursor.hasSelection() or (
            self.case_sensitive_check.isChecked() and selected_text != find_text
        ) or (
            not self.case_sensitive_check.isChecked() and selected_text.lower() != find_text.lower()
        ):
            # 如果当前没有选中或者选中的不是目标文本，先查找下一个
            if not self.find_next():
                return

        # 执行替换
        self.editor.textCursor().insertText(self.replace_input.text())
        # 查找下一个
        self.find_next()

    def replace_all(self):
        text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not text:
            return

        flags = self._get_find_flags()
        # 移除反向查找标志，全部替换通常从头到尾
        if flags & QTextDocument.FindBackward:
            flags &= ~QTextDocument.FindBackward

        # 移动光标到开始
        cursor = self.editor.textCursor()
        cursor.beginEditBlock() # 开启编辑块，用于撤销
        cursor.movePosition(QTextCursor.Start)
        self.editor.setTextCursor(cursor)

        count = 0
        while self.editor.find(text, flags):
            self.editor.textCursor().insertText(replace_text)
            count += 1
        
        cursor.endEditBlock()
        
        QMessageBox.information(self, "全部替换", f"已完成 {count} 处替换。")
