# gui/publish_dialog.py
import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QPushButton,
                             QDialogButtonBox, QSizePolicy, QSpacerItem,
                             QListWidget, QListWidgetItem, QWidget, QFileDialog)
from PyQt5.QtCore import Qt

class PublishDialog(QDialog):
    def __init__(self, all_articles_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("发布到微信公众号 (多图文)")
        self.setMinimumSize(800, 600)

        self.all_articles_data = all_articles_data
        self.current_index = -1
        
        self._init_ui()
        self._populate_article_list()
        if self.all_articles_data:
            self.article_list_widget.setCurrentRow(0)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # --- Left Panel ---
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("文章列表："))
        self.article_list_widget = QListWidget()
        self.article_list_widget.currentRowChanged.connect(self._on_selection_changed)
        left_panel_layout.addWidget(self.article_list_widget)
        main_layout.addLayout(left_panel_layout, 1)

        # --- Right Panel ---
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        
        # Create shared controls
        self.title_edit = QLineEdit()
        self.author_edit = QLineEdit()
        self.cover_edit = QLineEdit()
        self.cover_button = QPushButton("选择文件")
        self.digest_edit = QTextEdit()
        self.source_url_edit = QLineEdit()

        # Connect cover button
        self.cover_button.clicked.connect(self._select_cover_image)
        
        # Layout for right panel
        right_panel_layout.setSpacing(15) # 增加控件组之间的垂直间距

        title_layout = QHBoxLayout()
        title_label = QLabel("标题:")
        title_label.setFixedWidth(60)
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        right_panel_layout.addLayout(title_layout)

        author_layout = QHBoxLayout()
        author_label = QLabel("作者:")
        author_label.setFixedWidth(60)
        author_layout.addWidget(author_label)
        author_layout.addWidget(self.author_edit)
        right_panel_layout.addLayout(author_layout)

        cover_layout = QHBoxLayout()
        cover_label = QLabel("封面图:")
        cover_label.setFixedWidth(60)
        cover_layout.addWidget(cover_label)
        cover_layout.addWidget(self.cover_edit)
        cover_layout.addWidget(self.cover_button)
        right_panel_layout.addLayout(cover_layout)

        digest_layout = QVBoxLayout()
        digest_layout.setSpacing(5)
        digest_layout.addWidget(QLabel("摘要 (100字以内):"))
        self.digest_edit.setPlaceholderText("自动从正文第一段提取，或手动填写")
        self.digest_edit.setFixedHeight(80) # 设置一个合适的高度
        digest_layout.addWidget(self.digest_edit)
        right_panel_layout.addLayout(digest_layout)

        source_url_layout = QHBoxLayout()
        source_url_label = QLabel("原文链接:")
        source_url_label.setFixedWidth(60)
        source_url_layout.addWidget(source_url_label)
        self.source_url_edit.setPlaceholderText("选填，文章的“阅读原文”链接")
        source_url_layout.addWidget(self.source_url_edit)
        right_panel_layout.addLayout(source_url_layout)

        right_panel_layout.addStretch(1)
        
        # --- Bottom Controls ---
        info_label = QLabel("此功能直接调用微信官方接口进行发布。")
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px; color: #666;")
        info_label.setWordWrap(True)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        publish_btn = button_box.button(QDialogButtonBox.Ok)
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        
        publish_btn.setText("发布")
        cancel_btn.setText("取消")

        font = publish_btn.font()
        font.setPointSize(font.pointSize() + 2)
        publish_btn.setFont(font)
        cancel_btn.setFont(font)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add controls to the right panel's layout
        right_panel_layout.addWidget(info_label)
        right_panel_layout.addWidget(button_box)

        main_layout.addWidget(right_panel_widget, 3)

    def _populate_article_list(self):
        self.article_list_widget.clear()
        for i, article_data in enumerate(self.all_articles_data):
            list_item = QListWidgetItem(f"{i+1}. {article_data.get('title', '无标题')}")
            self.article_list_widget.addItem(list_item)

    def _on_selection_changed(self, index):
        # 1. Save the details of the previously selected article (if any)
        if self.current_index != -1:
            self._save_current_details()

        # 2. Load the details of the newly selected article
        self.current_index = index
        if index != -1:
            self._load_article_details(index)

    def _save_current_details(self):
        if self.current_index == -1:
            return
        
        data = self.all_articles_data[self.current_index]
        data['title'] = self.title_edit.text()
        data['author'] = self.author_edit.text()
        data['cover_image'] = self.cover_edit.text()
        data['digest'] = self.digest_edit.toPlainText()
        data['content_source_url'] = self.source_url_edit.text()
        
        # Update list item text if title changed
        self.article_list_widget.item(self.current_index).setText(f"{self.current_index+1}. {data['title']}")

    def _load_article_details(self, index):
        data = self.all_articles_data[index]
        
        self.title_edit.setText(data.get('title', '无标题'))
        self.author_edit.setText(data.get('author', '匿名'))
        self.cover_edit.setText(data.get('cover_image', ''))
        self.digest_edit.setPlainText(data.get('digest', ''))
        self.source_url_edit.setText(data.get('content_source_url', ''))

    def _select_cover_image(self):
        if self.current_index == -1:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "选择封面图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif)")
        if file_path:
            self.cover_edit.setText(file_path)

    def get_data(self):
        # Make sure the very last changes are saved before exiting
        self._save_current_details()
        return self.all_articles_data

    def accept(self):
        super().accept()
