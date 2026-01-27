from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import QRegExp

class MarkdownHighlighter(QSyntaxHighlighter):
    """
    Markdown 语法高亮器。
    为编辑器提供基础的 Markdown 语法着色，提升纯文本编辑体验。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        # 1. 标题 (#, ##, ...) - 蓝色
        headerFormat = QTextCharFormat()
        headerFormat.setForeground(QColor("#2980B9")) 
        headerFormat.setFontWeight(QFont.Bold)
        self.highlightingRules.append((QRegExp("^#+.*"), headerFormat))

        # 2. 粗体 (**bold**) - 深紫色
        boldFormat = QTextCharFormat()
        boldFormat.setFontWeight(QFont.Bold)
        boldFormat.setForeground(QColor("#8E44AD"))
        self.highlightingRules.append((QRegExp(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1"), boldFormat))

        # 3. 斜体 (*italic*) - 紫色
        italicFormat = QTextCharFormat()
        italicFormat.setFontItalic(True)
        italicFormat.setForeground(QColor("#9B59B6"))
        self.highlightingRules.append((QRegExp(r"(\*|_)(?=\S)(.+?)(?<=\S)\1"), italicFormat))

        # 4. 链接 ([text](url)) - 绿色
        linkFormat = QTextCharFormat()
        linkFormat.setForeground(QColor("#27AE60"))
        # linkFormat.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        self.highlightingRules.append((QRegExp(r"\[.+\]\(.+\)"), linkFormat))

        # 5. 图片 (![text](url)) - 橙色
        imageFormat = QTextCharFormat()
        imageFormat.setForeground(QColor("#D35400"))
        self.highlightingRules.append((QRegExp(r"!\[.+\]\(.+\)"), imageFormat))

        # 6. 行内代码 (`code`) - 红色
        codeFormat = QTextCharFormat()
        codeFormat.setForeground(QColor("#C0392B"))
        codeFormat.setFontFamily("Consolas")
        self.highlightingRules.append((QRegExp("`.+`"), codeFormat))
        
        # 7. 引用 (> quote) - 灰色
        quoteFormat = QTextCharFormat()
        quoteFormat.setForeground(QColor("#7F8C8D"))
        self.highlightingRules.append((QRegExp("^>.*"), quoteFormat))

        # 8. 列表 (- item, * item, 1. item) - 深红色
        listFormat = QTextCharFormat()
        listFormat.setForeground(QColor("#C0392B"))
        self.highlightingRules.append((QRegExp(r"^\s*([\*\-\+]|\d+\.)\s"), listFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
