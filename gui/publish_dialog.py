# gui/publish_dialog.py
import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QPushButton,
                             QDialogButtonBox, QSizePolicy, QSpacerItem,
                             QListWidget, QListWidgetItem, QStackedWidget, QWidget, QFileDialog)
from PyQt5.QtCore import Qt

class PublishDialog(QDialog):
    def __init__(self, all_articles_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("发布到微信公众号 (多图文)")
        self.setMinimumSize(800, 600)

        self.all_articles_data = all_articles_data
        self.current_article_index = -1
        
        self._init_ui()
        self._populate_article_list()
        if self.all_articles_data:
            self._select_article_in_dialog(0)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("文章列表："))
        self.article_list_widget = QListWidget()
        self.article_list_widget.currentRowChanged.connect(self._select_article_in_dialog)
        left_panel_layout.addWidget(self.article_list_widget)
        main_layout.addLayout(left_panel_layout, 1)

        right_panel_layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()
        right_panel_layout.addWidget(self.stacked_widget)

        info_label = QLabel("此功能直接调用微信官方接口进行发布。")
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px; color: #666;")
        info_label.setWordWrap(True)
        right_panel_layout.addWidget(info_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        publish_btn = button_box.button(QDialogButtonBox.Ok)
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        
        publish_btn.setText("发布")
        cancel_btn.setText("取消")

        # 增大按钮尺寸
        publish_btn.setFixedSize(100, 40)
        cancel_btn.setFixedSize(100, 40)

        # 调整字体大小，使其在增大尺寸后依然美观
        font = publish_btn.font()
        font.setPointSize(font.pointSize() + 2) # 增大2个点
        publish_btn.setFont(font)
        cancel_btn.setFont(font)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        right_panel_layout.addWidget(button_box)

        main_layout.addLayout(right_panel_layout, 3)
        self.setLayout(main_layout)

    def _populate_article_list(self):
        self.article_list_widget.blockSignals(True)
        self.article_list_widget.clear()
        for i, article_data in enumerate(self.all_articles_data):
            list_item = QListWidgetItem(f"{i+1}. {article_data.get('title', '无标题')}")
            self.article_list_widget.addItem(list_item)
            self._create_article_detail_page(article_data, i)
        self.article_list_widget.blockSignals(False)

    def _create_article_detail_page(self, article_data, index):
        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)

        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        title_edit = QLineEdit(article_data.get("title", "无标题"))
        title_edit.textChanged.connect(lambda text, idx=index: self._update_article_data(idx, 'title', text))
        title_layout.addWidget(title_edit)
        page_layout.addLayout(title_layout)

        # Author
        author_layout = QHBoxLayout()
        author_layout.addWidget(QLabel("作者:"))
        author_edit = QLineEdit(article_data.get("author", "匿名"))
        author_edit.textChanged.connect(lambda text, idx=index: self._update_article_data(idx, 'author', text))
        author_layout.addWidget(author_edit)
        page_layout.addLayout(author_layout)

        # Cover Image
        cover_layout = QHBoxLayout()
        cover_layout.addWidget(QLabel("封面图:"))
        cover_edit = QLineEdit(article_data.get("cover_image", "未找到图片，将使用默认封面"))
        cover_layout.addWidget(cover_edit)
        cover_button = QPushButton("选择文件")
        # Pass both index and the QLineEdit to the slot
        cover_button.clicked.connect(lambda _, idx=index, edit=cover_edit: self._select_cover_image(idx, edit))
        cover_layout.addWidget(cover_button)
        page_layout.addLayout(cover_layout)

        # Digest (formerly description)
        digest_layout = QVBoxLayout()
        digest_layout.addWidget(QLabel("摘要 (100字以内):"))
        digest_edit = QTextEdit(article_data.get("description", ""))
        digest_edit.setPlaceholderText("自动从正文第一段提取，或手动填写")
        digest_edit.textChanged.connect(lambda idx=index: self._update_article_data(idx, 'digest', digest_edit.toPlainText()))
        digest_layout.addWidget(digest_edit)
        page_layout.addLayout(digest_layout)

        # Content Source URL
        source_url_layout = QHBoxLayout()
        source_url_layout.addWidget(QLabel("原文链接:"))
        source_url_edit = QLineEdit(article_data.get("content_source_url", ""))
        source_url_edit.setPlaceholderText("选填，文章的“阅读原文”链接")
        source_url_edit.textChanged.connect(lambda text, idx=index: self._update_article_data(idx, 'content_source_url', text))
        source_url_layout.addWidget(source_url_edit)
        page_layout.addLayout(source_url_layout)

        page_layout.addStretch(1)
        self.stacked_widget.addWidget(page_widget)

    def _update_article_data(self, index, key, value):
        if 0 <= index < len(self.all_articles_data):
            self.all_articles_data[index][key] = value
            if key == 'title': # Also update the list widget item
                self.article_list_widget.item(index).setText(f"{index+1}. {value}")


    def _select_cover_image(self, index, cover_edit_widget):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择封面图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif)")
        if file_path:
            cover_edit_widget.setText(file_path)
            self._update_article_data(index, 'cover_image', file_path)

    def _select_article_in_dialog(self, index):
        if 0 <= index < self.stacked_widget.count():
            self.current_article_index = index
            self.stacked_widget.setCurrentIndex(index)

    def get_data(self):
        return self.all_articles_data

    def accept(self):
        super().accept()
