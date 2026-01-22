
class Themes:
    LIGHT = """
    /* Global Styles */
    QMainWindow, QDialog, QWidget {
        background-color: #F8FAFC;
        color: #1E293B;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }

    /* Buttons */
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 6px 16px;
        color: #1E293B;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #F1F5F9;
        border-color: #CBD5E1;
    }
    QPushButton:pressed {
        background-color: #E2E8F0;
    }
    QPushButton:checked {
        background-color: #3B82F6;
        color: white;
        border-color: #3B82F6;
    }
    QPushButton#primary {
        background-color: #3B82F6;
        color: white;
        border: none;
    }
    QPushButton#primary:hover {
        background-color: #2563EB;
    }

    /* Input Fields */
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 8px;
        selection-background-color: #3B82F6;
        selection-color: white;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #3B82F6;
        outline: none;
    }

    /* Lists and Trees */
    QListWidget, QTreeWidget {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        outline: none;
    }
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #F1F5F9;
    }
    QListWidget::item:selected {
        background-color: #EFF6FF; /* Blue-50 */
        color: #1E40AF; /* Blue-800 */
        border-left: 3px solid #3B82F6;
    }
    QListWidget::item:hover {
        background-color: #F8FAFC;
    }

    /* Splitter */
    QSplitter::handle {
        background-color: #E2E8F0;
        width: 1px;
    }

    /* Menu Bar */
    QMenuBar {
        background-color: #FFFFFF;
        border-bottom: 1px solid #E2E8F0;
    }
    QMenuBar::item {
        padding: 8px 12px;
        background: transparent;
    }
    QMenuBar::item:selected {
        background-color: #F1F5F9;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: #F8FAFC;
        width: 10px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #CBD5E1;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #94A3B8;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    /* Labels */
    QLabel {
        color: #1E293B;
    }
    QLabel#title {
        font-size: 16px;
        font-weight: bold;
    }
    """

    DARK = """
    /* Global Styles */
    QMainWindow, QDialog, QWidget {
        background-color: #0F172A;
        color: #F1F5F9;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }

    /* Buttons */
    QPushButton {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 6px 16px;
        color: #F1F5F9;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #334155;
        border-color: #475569;
    }
    QPushButton:pressed {
        background-color: #0F172A;
    }
    QPushButton:checked {
        background-color: #3B82F6;
        color: white;
        border-color: #3B82F6;
    }

    /* Input Fields */
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px;
        color: #F1F5F9;
        selection-background-color: #3B82F6;
        selection-color: white;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #3B82F6;
    }

    /* Lists and Trees */
    QListWidget, QTreeWidget {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 6px;
        outline: none;
    }
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #334155;
        color: #F1F5F9;
    }
    QListWidget::item:selected {
        background-color: #1E3A8A; /* Blue-900 */
        color: #60A5FA; /* Blue-400 */
        border-left: 3px solid #3B82F6;
    }
    QListWidget::item:hover {
        background-color: #334155;
    }

    /* Splitter */
    QSplitter::handle {
        background-color: #334155;
        width: 1px;
    }

    /* Menu Bar */
    QMenuBar {
        background-color: #1E293B;
        border-bottom: 1px solid #334155;
    }
    QMenuBar::item {
        padding: 8px 12px;
        background: transparent;
        color: #F1F5F9;
    }
    QMenuBar::item:selected {
        background-color: #334155;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: #0F172A;
        width: 10px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #475569;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #64748B;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    /* Labels */
    QLabel {
        color: #F1F5F9;
    }
    """
