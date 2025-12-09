# gui/publish_dialog.py
import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QPushButton,
                             QDialogButtonBox, QSizePolicy, QSpacerItem,
                             QListWidget, QListWidgetItem, QWidget, QFileDialog)
from PyQt5.QtCore import Qt

class PublishDialog(QDialog):
    """
    一个用于发布前最后编辑和确认多图文消息元数据的对话框。
    """
    def __init__(self, all_articles_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("发布到微信公众号 (多图文)")
        self.setMinimumSize(800, 600)

        # 这是从主窗口传递过来的、包含所有待发布文章信息的列表
        self.all_articles_data = all_articles_data
        # 记录左侧列表当前选中的行号
        self.current_index = -1
        
        self._init_ui()
        self._populate_article_list()
        
        # 对话框打开时，默认选中第一篇文章
        if self.all_articles_data:
            self.article_list_widget.setCurrentRow(0)

    def _init_ui(self):
        """
        初始化对话框的用户界面布局。
        """
        main_layout = QHBoxLayout(self)

        # --- 左侧面板：文章列表 ---
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("文章列表："))
        self.article_list_widget = QListWidget()
        # 核心信号：当用户点击切换列表项时，自动触发 _on_selection_changed
        self.article_list_widget.currentRowChanged.connect(self._on_selection_changed)
        left_panel_layout.addWidget(self.article_list_widget)
        main_layout.addLayout(left_panel_layout, 1) # 占据 1/4 宽度

        # --- 右侧面板：编辑区域 ---
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        
        # 创建所有编辑控件
        self.title_edit = QLineEdit()
        self.author_edit = QLineEdit()
        self.cover_edit = QLineEdit()
        self.cover_button = QPushButton("选择文件")
        self.digest_edit = QTextEdit()
        self.source_url_edit = QLineEdit()

        self.cover_button.clicked.connect(self._select_cover_image)
        
        # 使用布局来组织右侧面板
        right_panel_layout.setSpacing(15)

        # 标题行
        title_layout = QHBoxLayout()
        title_label = QLabel("标题:")
        title_label.setFixedWidth(60)
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        right_panel_layout.addLayout(title_layout)

        # 作者行
        author_layout = QHBoxLayout()
        author_label = QLabel("作者:")
        author_label.setFixedWidth(60)
        author_layout.addWidget(author_label)
        author_layout.addWidget(self.author_edit)
        right_panel_layout.addLayout(author_layout)

        # 封面图行
        cover_layout = QHBoxLayout()
        cover_label = QLabel("封面图:")
        cover_label.setFixedWidth(60)
        cover_layout.addWidget(cover_label)
        cover_layout.addWidget(self.cover_edit)
        cover_layout.addWidget(self.cover_button)
        right_panel_layout.addLayout(cover_layout)

        # 摘要区域
        digest_layout = QVBoxLayout()
        digest_layout.setSpacing(5)
        digest_layout.addWidget(QLabel("摘要 (100字以内):"))
        self.digest_edit.setPlaceholderText("自动从正文第一段提取，或在此手动填写")
        self.digest_edit.setFixedHeight(80)
        digest_layout.addWidget(self.digest_edit)
        right_panel_layout.addLayout(digest_layout)

        # 原文链接行
        source_url_layout = QHBoxLayout()
        source_url_label = QLabel("原文链接:")
        source_url_label.setFixedWidth(60)
        source_url_layout.addWidget(source_url_label)
        self.source_url_edit.setPlaceholderText("选填，文章的“阅读原文”链接")
        source_url_layout.addWidget(self.source_url_edit)
        right_panel_layout.addLayout(source_url_layout)

        right_panel_layout.addStretch(1)
        
        # --- 底部按钮和信息 ---
        info_label = QLabel("提示：此功能将调用微信官方接口创建一篇新的草稿，不会直接群发。")
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px; color: #666;")
        info_label.setWordWrap(True)
        
        # 使用标准的按钮盒子，能确保在不同操作系统下有统一的外观
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        publish_btn = button_box.button(QDialogButtonBox.Ok)
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        
        publish_btn.setText("创建草稿")
        cancel_btn.setText("取消")

        # 增大按钮字体，使其更易点击
        font = publish_btn.font()
        font.setPointSize(font.pointSize() + 2)
        publish_btn.setFont(font)
        cancel_btn.setFont(font)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        right_panel_layout.addWidget(info_label)
        right_panel_layout.addWidget(button_box)

        main_layout.addWidget(right_panel_widget, 3) # 占据 3/4 宽度

    def _populate_article_list(self):
        """
        根据传入的文章数据，填充左侧的文章列表。
        """
        self.article_list_widget.clear()
        for i, article_data in enumerate(self.all_articles_data):
            list_item = QListWidgetItem(f"{i+1}. {article_data.get('title', '无标题')}")
            self.article_list_widget.addItem(list_item)

    def _on_selection_changed(self, index):
        """
        当左侧列表的选中项改变时触发的核心槽函数。
        它实现了“先保存，后加载”的逻辑，确保数据同步。
        """
        # 步骤 1: 如果之前有选中的项，先将在右侧面板的修改保存回数据列表
        if self.current_index != -1:
            self._save_current_details()

        # 步骤 2: 更新当前选中的索引，并加载新选中项的数据到右侧面板
        self.current_index = index
        if index != -1:
            self._load_article_details(index)

    def _save_current_details(self):
        """
        将右侧编辑控件中的内容，保存回 `self.all_articles_data` 中对应的文章字典。
        """
        if self.current_index == -1:
            return
        
        data = self.all_articles_data[self.current_index]
        data['title'] = self.title_edit.text()
        data['author'] = self.author_edit.text()
        data['cover_image'] = self.cover_edit.text()
        data['digest'] = self.digest_edit.toPlainText()
        data['content_source_url'] = self.source_url_edit.text()
        
        # 如果标题被修改，同步更新左侧列表的显示文本
        self.article_list_widget.item(self.current_index).setText(f"{self.current_index+1}. {data['title']}")

    def _load_article_details(self, index):
        """
        从 `self.all_articles_data` 中加载指定索引的文章数据，并填充到右侧的编辑控件中。
        """
        data = self.all_articles_data[index]
        
        self.title_edit.setText(data.get('title', '无标题'))
        self.author_edit.setText(data.get('author', ''))
        self.cover_edit.setText(data.get('cover_image', ''))
        self.digest_edit.setPlainText(data.get('digest', ''))
        self.source_url_edit.setText(data.get('content_source_url', ''))

    def _select_cover_image(self):
        """
        响应“选择文件”按钮的点击事件，打开一个文件对话框来选择封面图片。
        """
        if self.current_index == -1:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "选择封面图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif)")
        if file_path:
            self.cover_edit.setText(file_path)

    def get_data(self):
        """
        这是对话框向外部返回数据的公共接口。
        在对话框被接受（点击“发布”）时，主窗口会调用此方法来获取最终确认的数据。
        """
        # 在退出前，确保对当前选中项的最后一次修改也被保存
        self._save_current_details()
        return self.all_articles_data

    def accept(self):
        """
        重写 accept 方法，在对话框关闭前可以添加额外的校验逻辑。
        目前只是调用父类的实现。
        """
        # 在这里可以添加校验，例如检查所有文章是否都有标题等
        super().accept()
