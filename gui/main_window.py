import sys
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QTextEdit, QAction, QFileDialog, QSplitter, QActionGroup, 
                             QMenu, QListWidget, QPushButton, QListWidgetItem, QFrame, QLabel) # Added QLabel
from functools import partial
import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
import logging
from PyQt5.QtCore import Qt, QUrl, QSize, pyqtSlot, QTimer, QObject, QThread, pyqtSignal
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QColor, QFont, QIcon
from bs4 import BeautifulSoup

from core.renderer import MarkdownRenderer
from gui.editor import PastingImageEditor
from gui.source_dialog import SourceDialog
from core.parser import ContentParser
from core.storage import StorageManager
from core.wechat_api import WeChatAPI
from gui.publish_dialog import PublishDialog
from gui.template_editor import TemplateEditorDialog
from core.template_manager import TemplateManager
from gui.status_dialog import StatusDialog
from gui.settings_dialog import SettingsDialog
from gui.crawl_dialog import CrawlDialog
from PyQt5.QtWidgets import QDialog, QMessageBox
from core.crawler import Crawler
from core.llm import LLMProcessor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("微信公众号Markdown渲染发布系统")
        # 获取可用屏幕尺寸，并设置窗口为屏幕的80%大小，居中显示
        screen_rect = QApplication.desktop().availableGeometry()
        width = int(screen_rect.width() * 0.8)
        height = int(screen_rect.height() * 0.8)
        x = int((screen_rect.width() - width) / 2)
        y = int((screen_rect.height() - height) / 2)
        self.setGeometry(x, y, width, height)
        self.log = logging.getLogger("MdToWeChat")

        self.renderer = MarkdownRenderer()
        self.parser = ContentParser()
        self.storage_manager = StorageManager()
        self.wechat_api = WeChatAPI()
        self.template_manager = TemplateManager()
        self.current_mode = "light" # 默认模式为亮色
        self.use_template = True # 默认使用模板
        
        self.articles = []
        self.current_article_index = -1
        self._is_switching_articles = False # 添加一个标志来防止重入
        self._is_syncing_scroll = False # 添加标志以防止滚动同步循环

        self._init_ui()
        self._create_menu_bar()
        self._init_articles()
        self._apply_mode_styles() # 初始化应用模式样式

    def _init_ui(self):
        """初始化用户界面布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Pane: Article List ---
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(10, 10, 10, 10) # Add some padding
        left_pane.setFixedWidth(250) # Increase width slightly

        # Display Mode Toggle Section
        mode_toggle_container_layout = QHBoxLayout() # Container for centering
        mode_toggle_layout = QHBoxLayout() # For label and button
        mode_toggle_layout.addWidget(QLabel("显示模式:"))
        self.mode_toggle_btn = QPushButton()
        self.mode_toggle_btn.setFixedSize(QSize(60, 28)) # Fixed size for text
        self.mode_toggle_btn.setToolTip("点击切换亮色/暗黑模式")
        self.mode_toggle_btn.clicked.connect(self._toggle_mode)
        self._update_mode_toggle_button() # Set initial text/style
        mode_toggle_layout.addWidget(self.mode_toggle_btn)
        
        mode_toggle_container_layout.addStretch() # Left stretch for centering
        mode_toggle_container_layout.addLayout(mode_toggle_layout)
        mode_toggle_container_layout.addStretch() # Right stretch for centering
        left_layout.addLayout(mode_toggle_container_layout)

        # Action Buttons
        article_action_layout = QHBoxLayout()
        add_article_btn = QPushButton(" 新增文章")
        add_article_btn.setIcon(QIcon.fromTheme("list-add"))
        add_article_btn.setFixedSize(QSize(100, 35)) # Adjusted size
        add_article_btn.setToolTip("新增一篇文章")
        add_article_btn.clicked.connect(self._add_article)
        
        remove_article_btn = QPushButton(" 删除文章")
        remove_article_btn.setIcon(QIcon.fromTheme("list-remove"))
        remove_article_btn.setFixedSize(QSize(100, 35)) # Adjusted size
        remove_article_btn.setToolTip("删除当前文章")
        remove_article_btn.clicked.connect(self._remove_article)

        article_action_layout.addWidget(add_article_btn)
        article_action_layout.addWidget(remove_article_btn)
        left_layout.addLayout(article_action_layout)

        # Crawl Button - new centered layout
        crawl_layout = QHBoxLayout()
        crawl_article_btn = QPushButton(" 从网页地址抓取内容")
        crawl_article_btn.setIcon(QIcon.fromTheme("web-browser"))
        crawl_article_btn.setFixedHeight(35) # Match height
        crawl_article_btn.setToolTip("从网页抓取内容并由AI生成文章")
        crawl_article_btn.clicked.connect(self._crawl_article)
        crawl_layout.addStretch()
        crawl_layout.addWidget(crawl_article_btn)
        crawl_layout.addStretch()
        left_layout.addLayout(crawl_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator)

        # Article List
        self.article_list_widget = QListWidget()
        self.article_list_widget.currentRowChanged.connect(self._select_article)
        self.article_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.article_list_widget.customContextMenuRequested.connect(self._show_article_list_context_menu)
        # Increase font size for article titles
        font = QFont()
        font.setPointSize(11) 
        self.article_list_widget.setFont(font)
        self.article_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }") # Add padding to items
        left_layout.addWidget(self.article_list_widget)
        
        # --- Middle and Right Panes (Editor and Preview) ---
        editor_preview_splitter = QSplitter(Qt.Horizontal)

        # Middle pane: Markdown Editor (customized to handle image pasting)
        self.markdown_editor = PastingImageEditor(wechat_api=self.wechat_api)
        self.markdown_editor.verticalScrollBar().valueChanged.connect(self._on_editor_scrolled)
        self.markdown_editor.setFontPointSize(14)
        self.markdown_editor.setStyleSheet("font-family: 'Consolas', 'Monaco', 'Courier New', monospace; line-height: 1.5;")
        self.markdown_editor.setPlaceholderText(
            "在此输入Markdown内容...\n\n"
            "支持的格式：\n"
            "标题: # H1, ## H2, ### H3\n"
            "列表: - 无序列表项, 1. 有序列表项\n"
            "加粗: **文字** 或 __文字__\n"
            "斜体: *文字* 或 _文字_\n"
            "链接: [链接文本](URL)\n"
            "图片: ![图片描述](图片URL)\n"
            "代码块: ```python\nprint('Hello')\n```\n"
            "行内代码: `print()`"
        )
        self.markdown_editor.textChanged.connect(self._update_current_article_content)
        editor_preview_splitter.addWidget(self.markdown_editor)

        # Right pane: HTML Preview
        self.html_preview = CustomWebEngineView(self)
        editor_preview_splitter.addWidget(self.html_preview)
        
        editor_preview_splitter.setSizes([self.width() // 2, self.width() // 2])

        # --- Main Splitter ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_pane)
        main_splitter.addWidget(editor_preview_splitter)
        main_splitter.setSizes([200, self.width() - 200])
        
        main_layout.addWidget(main_splitter)

    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件")

        new_action = QAction("新建", self)
        new_action.triggered.connect(self._new_document)
        file_menu.addAction(new_action)

        open_action = QAction("打开...", self)
        open_action.triggered.connect(self._open_document)
        file_menu.addAction(open_action)

        save_action = QAction("保存", self)
        save_action.triggered.connect(self._save_document)
        file_menu.addAction(save_action)
        
        save_all_action = QAction("全部保存", self)
        save_all_action.triggered.connect(self._save_all_documents)
        file_menu.addAction(save_all_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑")
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.markdown_editor.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.markdown_editor.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        settings_action = QAction("设置...", self)
        settings_action.triggered.connect(self._open_settings_dialog)
        edit_menu.addAction(settings_action)

        # 主题菜单
        theme_menu = menu_bar.addMenu("主题")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        # 从renderer获取可用主题
        available_themes = self.renderer.get_available_themes()
        for theme_name in available_themes:
            # 将下划线替换为空格并大写首字母以获得更友好的显示名称
            display_name = theme_name.replace("_", " ").title()
            action = QAction(display_name, self, checkable=True)

            # 使用 functools.partial 来传递主题名称
            action.triggered.connect(partial(self._change_theme, theme_name))

            self.theme_group.addAction(action)
            theme_menu.addAction(action)


        # 发布菜单
        publish_menu = menu_bar.addMenu("发布")
        publish_wechat_action = QAction("发布到微信公众号", self)
        publish_wechat_action.triggered.connect(self._publish_to_wechat)
        publish_menu.addAction(publish_wechat_action)

        # 模板菜单 (新增)
        template_menu = menu_bar.addMenu("模板")
        
        edit_template_action = QAction("编辑模板...", self)
        edit_template_action.triggered.connect(self._open_template_editor)
        template_menu.addAction(edit_template_action)

        template_menu.addSeparator()

        self.use_template_action = QAction("使用模板", self, checkable=True)
        self.use_template_action.setChecked(self.use_template)
        self.use_template_action.triggered.connect(self._toggle_template_usage)
        template_menu.addAction(self.use_template_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _init_articles(self):
        """初始化文章列表，默认创建一篇新文章。"""
        self.articles = [{'title': '未命名文章 1', 'content': '# 未命名文章 1\n\n', 'theme': 'blue_glow'}]
        self.current_article_index = 0
        self._refresh_article_list()
        self._load_article_content(self.current_article_index)

    def _refresh_article_list(self):
        """刷新左侧的文章列表UI。"""
        self.article_list_widget.blockSignals(True)
        self.article_list_widget.clear()
        for i, article in enumerate(self.articles):
            # 尝试从内容中解析标题
            parsed_title = self.parser.parse_markdown(article['content']).get('title', article['title'])
            self.articles[i]['title'] = parsed_title
            item = QListWidgetItem(f"{i+1}. {parsed_title}")
            self.article_list_widget.addItem(item)
        
        # 在信号解锁前恢复选中项，避免触发不必要的currentRowChanged信号导致切换问题
        if self.current_article_index >= 0:
            self.article_list_widget.setCurrentRow(self.current_article_index)
        self.article_list_widget.blockSignals(False)

    def _add_article(self):
        """新增一篇文章。"""
        self._update_current_article_content() # 保存当前文章
        new_article_num = len(self.articles) + 1
        new_article = {'title': f'未命名文章 {new_article_num}', 'content': f'# 未命名文章 {new_article_num}\n\n', 'theme': 'default'}
        self.articles.append(new_article)
        self.current_article_index = len(self.articles) - 1
        self._refresh_article_list()
        self._load_article_content(self.current_article_index)

    def _crawl_article(self):
        """从网页抓取内容并生成新文章（异步）。"""
        dialog = CrawlDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        url, system_prompt = dialog.get_data()
        self.log.info(f"Starting crawl for url: {url}")

        self.status_dialog = StatusDialog(title="文章生成中", parent=self)
        self.status_dialog.show()
        QApplication.processEvents()

        # 1. 创建线程和Worker
        self.crawl_thread = QThread()
        self.crawl_worker = CrawlWorker(url, system_prompt)
        self.crawl_worker.moveToThread(self.crawl_thread)

        # 2. 连接信号和槽
        self.crawl_worker.progress_updated.connect(self._on_crawl_progress)
        self.crawl_worker.finished.connect(self._on_crawl_finished)
        self.crawl_thread.started.connect(self.crawl_worker.run)

        # 3. 启动线程
        self.crawl_thread.start()
        self.log.info("Crawl thread started.")


    def _remove_article(self):
        """删除当前选中的文章。"""
        if len(self.articles) <= 1:
            QMessageBox.warning(self, "操作失败", "至少需要保留一篇文章。")
            return
            
        row = self.article_list_widget.currentRow()
        if row >= 0:
            reply = QMessageBox.question(self, '确认删除', f"确定要删除文章 \"{self.articles[row]['title']}\" ?\n此操作不可撤销。",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.articles[row]
                if self.current_article_index >= row:
                    self.current_article_index = max(0, self.current_article_index - 1)
                
                self._refresh_article_list()
                self._load_article_content(self.current_article_index)

    def _select_article(self, index):
        """当用户在列表中选择不同文章时触发。"""
        if self._is_switching_articles or index == self.current_article_index:
            return

        self._is_switching_articles = True
        try:
            if self.current_article_index != -1:
                self._update_current_article_content(refresh_list=False) # 保存时禁止刷新列表
            
            self.current_article_index = index
            self._load_article_content(index)
        finally:
            self._is_switching_articles = False

    def _load_article_content(self, index):
        """加载指定索引的文章内容到编辑器。"""
        if 0 <= index < len(self.articles):
            self.markdown_editor.blockSignals(True)
            self.markdown_editor.setPlainText(self.articles[index]['content'])
            self.markdown_editor.blockSignals(False)
            self._update_preview()
            self._update_theme_menu_selection()

    def _update_current_article_content(self, refresh_list=True):
        """将编辑器内容保存到当前文章的数据结构中，并触发预览更新。"""
        if 0 <= self.current_article_index < len(self.articles):
            self.articles[self.current_article_index]['content'] = self.markdown_editor.toPlainText()
            self._update_preview()
            # 实时更新列表中的标题，但在切换文章时应禁止
            if refresh_list and not self._is_switching_articles:
                self._refresh_article_list()
            
    def _update_preview(self):
        """根据当前选中文章的内容更新HTML预览。"""
        if not (0 <= self.current_article_index < len(self.articles)):
            return

        current_article = self.articles[self.current_article_index]
        markdown_content = current_article['content']
        theme_name = current_article.get('theme', 'default')
        self.renderer.set_theme(theme_name)

        if self.use_template:
            header, footer = self.template_manager.get_templates()
            full_markdown_content = f"{header}\n\n{markdown_content}\n\n{footer}"
        else:
            full_markdown_content = markdown_content
            
        html_content = self.renderer.render(full_markdown_content, mode=self.current_mode)
        self.html_preview.set_html_content(html_content)

    def _new_document(self):
        """清空所有文章，重置为一个新的文档。"""
        reply = QMessageBox.question(self, '确认操作', "此操作将清空所有已编辑的文章，确定要新建吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.articles = []
            self.current_article_index = -1
            self._init_articles()
            self.setWindowTitle("微信公众号Markdown渲染发布系统 - 未命名")
            self.log.info("New document created, all articles cleared.")

    def _open_document(self):
        """打开一个或多个Markdown文件，并将它们作为新文章添加到列表中。"""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "打开Markdown文件", "", "Markdown Files (*.md);;All Files (*)")
        
        if not file_paths:
            return

        opened_count = 0
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                title = self.parser.parse_markdown(content).get('title', os.path.basename(file_path))
                
                new_article = {
                    'title': title,
                    'content': content,
                    'theme': 'default',
                    'file_path': file_path
                }
                
                self.articles.append(new_article)
                self.log.info(f"Opened {file_path} as a new article.")
                opened_count += 1

            except Exception as e:
                self.log.error(f"Failed to open file {file_path} as new article: {e}", exc_info=True)
                QMessageBox.warning(self, "打开失败", f"打开文件 {os.path.basename(file_path)} 失败: {e}")
        
        if opened_count > 0:
            # 切换到最后一个被导入的文章
            self.current_article_index = len(self.articles) - 1
            
            # 刷新UI
            self._refresh_article_list()
            self._load_article_content(self.current_article_index)
            
            # 更新窗口标题
            self.setWindowTitle(f"微信公众号Markdown渲染发布系统 - {os.path.basename(file_paths[-1])}")

    def _save_document(self):
        """保存当前选中的文章。"""
        if not (0 <= self.current_article_index < len(self.articles)):
            QMessageBox.warning(self, "保存失败", "没有可保存的文章。")
            return

        article = self.articles[self.current_article_index]
        filepath = article.get('file_path')
        title = article['title']

        if not filepath:
            suggested_filename = self.storage_manager._generate_filename(title, ".md")
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"保存文章: {title}", suggested_filename, "Markdown Files (*.md);;All Files (*)"
            )
            if not filepath:
                self.log.info(f"Save operation cancelled by user for article '{title}'.")
                return

        self._save_single_article_to_path(self.current_article_index, filepath)

    def _save_all_documents(self):
        """保存所有打开的文章。"""
        if not self.articles:
            QMessageBox.warning(self, "保存失败", "没有可保存的文章。")
            return

        self.log.info("Attempting to save all articles.")
        
        # 检查是否有新文章（未保存过）
        new_articles_indices = [i for i, article in enumerate(self.articles) if not article.get('file_path')]
        
        save_directory = None
        if new_articles_indices:
            # 如果有新文章，则弹窗一次让用户选择文件夹
            save_directory = QFileDialog.getExistingDirectory(self, "选择新文章的保存文件夹", os.getcwd())
            if not save_directory:
                self.log.info("Save All operation cancelled by user because no directory was selected.")
                QMessageBox.information(self, "操作取消", "未选择文件夹，全部保存操作已取消。")
                return

        saved_count = 0
        for i, article in enumerate(self.articles):
            filepath = article.get('file_path')
            
            if not filepath:
                # 这是新文章，使用选择的文件夹和默认文件名
                if save_directory:
                    filename = self.storage_manager._generate_filename(article['title'], ".md")
                    filepath = os.path.join(save_directory, filename)
                else:
                    # 理论上不应该发生，因为我们已经检查过
                    continue
            
            # 执行保存
            if self._save_single_article_to_path(i, filepath):
                saved_count += 1
        
        QMessageBox.information(self, "全部保存完成", f"成功保存 {saved_count} / {len(self.articles)} 篇文章。")
        self.log.info(f"Finished saving all articles. Saved {saved_count}/{len(self.articles)}.")

    def _save_single_article_to_path(self, index, filepath):
        """
        将指定索引的文章内容保存到指定的文件路径。
        这是实际执行保存的核心函数。
        返回 True 表示成功, False 表示失败。
        """
        if not (0 <= index < len(self.articles)):
            return False

        article = self.articles[index]
        title = article['title']
        
        # 确保内容是最新的（如果正在编辑的就是这篇）
        if index == self.current_article_index:
            markdown_content = self.markdown_editor.toPlainText()
            article['content'] = markdown_content
        else:
            markdown_content = article['content']

        if not markdown_content.strip():
            self.log.warning(f"Save cancelled for article '{title}' because content is empty.")
            return True # 认为“空文章”这个状态已经被处理，不计为失败

        try:
            self.storage_manager.save_markdown_file(filepath, markdown_content)
            self.log.info(f"Article '{title}' saved to: {filepath}")
            
            # 关键：保存成功后，更新文章数据中的文件路径
            article['file_path'] = filepath
            
            if index == self.current_article_index:
                 self.setWindowTitle(f"微信公众号Markdown渲染发布系统 - {os.path.basename(filepath)}")
            return True
        except Exception as e:
            self.log.error(f"Failed to save article '{title}' to {filepath}: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存文章 \"{title}\" 到 \"{filepath}\" 失败: {e}")
            return False


    def _publish_to_wechat(self):
        """显示多图文发布对话框并处理发布流程"""
        self._update_current_article_content()

        if not self.articles:
            QMessageBox.warning(self, "操作失败", "没有可发布的文章。")
            return
            
        if len(self.articles) > 8:
            QMessageBox.warning(self, "文章数量超限", "微信多图文消息最多支持8篇文章。")
            return

        # 1. 解析所有文章内容
        self.log.info("Parsing all articles for multi-article publishing.")
        all_articles_data = []
        for article in self.articles:
            parsed_data = self.parser.parse_markdown(article['content'])
            parsed_data['markdown_content'] = article['content'] # 保留原始markdown
            parsed_data['theme'] = article.get('theme', 'default')
            
            # 如果作者为空，则填充默认作者
            if not parsed_data.get('author'):
                parsed_data['author'] = self.wechat_api.default_author
            
            all_articles_data.append(parsed_data)
        
        # 2. 弹出发布对话框
        dialog = PublishDialog(all_articles_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self.log.info("Multi-article publish dialog accepted.")
            final_articles_data = dialog.get_data()
            self._execute_multi_article_publishing(final_articles_data)
        else:
            self.log.info("Multi-article publish dialog cancelled by user.")

    def _execute_multi_article_publishing(self, all_articles_data):
        """通过启动后台线程来执行多图文的上传和发布草稿逻辑"""
        self.status_dialog = StatusDialog(title="发布到微信", parent=self)
        self.status_dialog.show()
        QApplication.processEvents()

        # 1. 创建线程和Worker
        self.publish_thread = QThread()
        self.publish_worker = PublishWorker(
            articles_data=all_articles_data,
            wechat_api=self.wechat_api,
            renderer=self.renderer,
            template_manager=self.template_manager,
            storage_manager=self.storage_manager,
            use_template=self.use_template,
            current_mode=self.current_mode
        )
        self.publish_worker.moveToThread(self.publish_thread)

        # 2. 连接信号和槽
        self.publish_worker.progress_updated.connect(self._on_publish_progress)
        self.publish_worker.finished.connect(self._on_publish_finished)
        self.publish_thread.started.connect(self.publish_worker.run)
        
        # 3. 启动线程
        self.publish_thread.start()
        self.log.info("Publishing thread started.")

    def _on_publish_progress(self, message):
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=False)

    def _on_publish_finished(self, success, message):
        QApplication.beep()
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=True)
        
        # 清理线程和worker
        self.publish_thread.quit()
        self.publish_thread.wait()
        self.publish_worker.deleteLater()
        self.publish_thread.deleteLater()
        self.log.info("Publish thread and worker cleaned up.")

    def _on_crawl_progress(self, message):
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=False)

    def _on_crawl_finished(self, success, result):
        QApplication.beep()
        if self.status_dialog:
            if success:
                # result 是一个包含新文章数据的字典
                title = self.parser.parse_markdown(result['content']).get('title', os.path.basename(result['url']))
                new_article = {
                    'title': title,
                    'content': result['content'],
                    'theme': 'default'
                }
                self.articles.append(new_article)
                self.current_article_index = len(self.articles) - 1
                self._refresh_article_list()
                self._load_article_content(self.current_article_index)
                
                final_message = "文章生成成功！"
                self.log.info(f"Successfully crawled and processed article from {result['url']}")
            else:
                # result 是错误信息字符串
                final_message = f"操作失败: {result}"
                self.log.error(f"Failed to crawl and process article: {result}")
            
            self.status_dialog.update_status(final_message, is_finished=True)

        # 清理线程和worker
        self.crawl_thread.quit()
        self.crawl_thread.wait()
        self.crawl_worker.deleteLater()
        self.crawl_thread.deleteLater()
        self.log.info("Crawl thread and worker cleaned up.")

    def _show_article_list_context_menu(self, position):
        """显示文章列表的右键上下文菜单。"""
        item = self.article_list_widget.itemAt(position)
        if not item:
            return

        row = self.article_list_widget.row(item)

        menu = QMenu()
        move_up_action = QAction("向上移动", self)
        move_down_action = QAction("向下移动", self)
        delete_action = QAction("删除文章", self)

        # 根据位置决定是否禁用操作
        if row == 0:
            move_up_action.setEnabled(False)
        if row == self.article_list_widget.count() - 1:
            move_down_action.setEnabled(False)

        move_up_action.triggered.connect(lambda: self._move_article_up(row))
        move_down_action.triggered.connect(lambda: self._move_article_down(row))
        delete_action.triggered.connect(self._remove_article)

        menu.addAction(move_up_action)
        menu.addAction(move_down_action)
        menu.addSeparator()
        menu.addAction(delete_action)

        menu.exec_(self.article_list_widget.mapToGlobal(position))

    def _move_article_up(self, row):
        """将指定索引的文章向上移动一位。"""
        if row > 0:
            # 交换数据
            self.articles[row], self.articles[row - 1] = self.articles[row - 1], self.articles[row]
            # 更新当前选中的索引
            self.current_article_index = row - 1
            # 刷新UI
            self._refresh_article_list()

    def _move_article_down(self, row):
        """将指定索引的文章向下移动一位。"""
        if row < len(self.articles) - 1:
            # 交换数据
            self.articles[row], self.articles[row + 1] = self.articles[row + 1], self.articles[row]
            # 更新当前选中的索引
            self.current_article_index = row + 1
            # 刷新UI
            self._refresh_article_list()

    def _show_about_dialog(self):
        """显示关于对话框"""
        # 可以使用 QMessageBox 显示关于信息
        self.log.info("Showing 'About' dialog.")
        # 使用QMessageBox更友好
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, "关于", "微信公众号Markdown渲染发布系统 v1.0\n\n一个简化微信公众号文章发布的桌面工具。")

    def _open_template_editor(self):
        """打开模板编辑器对话框。"""
        dialog = TemplateEditorDialog(self)
        # exec_()会阻塞，直到对话框关闭。如果用户点击了保存，模板文件会被更新。
        # 对话框关闭后，我们刷新预览以反映可能的变化（如果“使用模板”是激活的）。
        dialog.exec_()
        if self.use_template:
            self._update_preview()

    def _toggle_template_usage(self, checked):
        """切换是否使用模板。"""
        self.use_template = checked
        self.log.info(f"Template usage set to: {self.use_template}")
        self._update_preview()

    def _change_theme(self, theme_name):
        """切换当前文章的渲染主题并更新预览"""
        if 0 <= self.current_article_index < len(self.articles):
            current_article = self.articles[self.current_article_index]
            if current_article.get('theme') != theme_name:
                current_article['theme'] = theme_name
                self._update_preview()
                self.log.info(f"Theme for article '{current_article['title']}' changed to: {theme_name}")

    def _update_theme_menu_selection(self):
        """根据当前文章的主题更新主题菜单的选中状态。"""
        if not (0 <= self.current_article_index < len(self.articles)):
            return

        theme_name = self.articles[self.current_article_index].get('theme', 'default')
        for action in self.theme_group.actions():
            action_theme_name = action.text().replace(" ", "_").lower()
            if action_theme_name == theme_name:
                action.setChecked(True)
                break

    def _open_settings_dialog(self):
        """打开设置对话框。"""
        dialog = SettingsDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            # 重新实例化API类以加载新配置
            self.wechat_api = WeChatAPI()
            self.log.info("Settings saved and configuration reloaded.")

    # --- Scroll Synchronization Methods ---

    def _on_editor_scrolled(self, value):
        """当编辑器滚动时，同步预览区。"""
        if self._is_syncing_scroll:
            return
            
        editor_scrollbar = self.markdown_editor.verticalScrollBar()
        # 避免在没有滚动条时（如内容很少）进行计算
        if editor_scrollbar.maximum() == 0:
            return
            
        # 计算滚动百分比
        scroll_percentage = value / editor_scrollbar.maximum()
        
        # 构建并执行JS代码来滚动预览区
        js_code = f"window.scrollTo(0, document.body.scrollHeight * {scroll_percentage});"
        
        self._is_syncing_scroll = True
        self.html_preview.page().runJavaScript(js_code)
        # 使用定时器在短暂延迟后重置标志，以允许反向同步
        QTimer.singleShot(100, lambda: setattr(self, '_is_syncing_scroll', False))

    @pyqtSlot(float)
    def on_preview_scrolled(self, percentage):
        """当预览区滚动时（由JS调用），同步编辑器。"""
        if self._is_syncing_scroll:
            return
            
        editor_scrollbar = self.markdown_editor.verticalScrollBar()
        max_val = editor_scrollbar.maximum()
        
        self._is_syncing_scroll = True
        editor_scrollbar.setValue(int(max_val * percentage))
        # 使用定时器在短暂延迟后重置标志，以允许反向同步
        QTimer.singleShot(100, lambda: setattr(self, '_is_syncing_scroll', False))

    def _toggle_mode(self):
        """切换亮色/暗黑模式。"""
        if self.current_mode == "light":
            self.current_mode = "dark"
        else:
            self.current_mode = "light"
        
        self._apply_mode_styles()
        self._update_preview()
        self._update_mode_toggle_button()
        self.log.info(f"Mode changed to: {self.current_mode}")

    def _update_mode_toggle_button(self):
        """更新模式切换按钮的文本和样式。"""
        if self.current_mode == "dark":
            self.mode_toggle_btn.setText("暗黑")
            self.mode_toggle_btn.setStyleSheet("QPushButton { background-color: #555; color: white; border: 1px solid #777; border-radius: 5px; }"
                                               "QPushButton:hover { background-color: #666; }")
        else:
            self.mode_toggle_btn.setText("明亮")
            self.mode_toggle_btn.setStyleSheet("QPushButton { background-color: #eee; color: black; border: 1px solid #ccc; border-radius: 5px; }"
                                               "QPushButton:hover { background-color: #ddd; }")

    def _apply_mode_styles(self):
        """应用当前模式的样式到主窗口和Markdown编辑器，并美化整体布局。"""
        if self.current_mode == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2e2e2e;
                    color: #f0f0f0;
                }
                QSplitter::handle {
                    background-color: #555;
                }
                QListWidget {
                    background-color: #3e3e3e;
                    color: #f0f0f0;
                    border: 1px solid #555;
                    border-radius: 5px; /* Subtle rounded corners */
                }
                QListWidget::item:selected {
                    background-color: #555;
                    color: white;
                }
                QPushButton {
                    background-color: #444;
                    color: #f0f0f0;
                    border: 1px solid #666;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QLabel {
                    color: #f0f0f0;
                }
                QMenuBar {
                    background-color: #2e2e2e;
                    color: #f0f0f0;
                }
                QMenuBar::item:selected {
                    background-color: #555;
                }
                QMenu {
                    background-color: #2e2e2e;
                    color: #f0f0f0;
                    border: 1px solid #555;
                }
                QMenu::item:selected {
                    background-color: #555;
                }
            """)
            self.markdown_editor.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    line-height: 1.5;
                    background-color: #3e3e3e;
                    color: #f0f0f0;
                    border: 1px solid #555;
                }
            """)
        else: # light mode
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                    color: #333;
                }
                QSplitter::handle {
                    background-color: #ccc;
                }
                QListWidget {
                    background-color: white;
                    color: #333;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
                QListWidget::item:selected {
                    background-color: #e0e0e0;
                    color: black;
                }
                QPushButton {
                    background-color: #f5f5f5;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #e5e5e5;
                }
                QLabel {
                    color: #333;
                }
                QMenuBar {
                    background-color: #f0f0f0;
                    color: #333;
                }
                QMenuBar::item:selected {
                    background-color: #ddd;
                }
                QMenu {
                    background-color: #f0f0f0;
                    color: #333;
                    border: 1px solid #ccc;
                }
                QMenu::item:selected {
                    background-color: #ddd;
                }
            """)
            self.markdown_editor.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    line-height: 1.5;
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                }
            """)

# --- 异步发布 Worker ---
class PublishWorker(QObject):
    progress_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, articles_data, wechat_api, renderer, template_manager, storage_manager, use_template, current_mode):
        super().__init__()
        self.articles_data = articles_data
        self.wechat_api = wechat_api
        self.renderer = renderer
        self.template_manager = template_manager
        self.storage_manager = storage_manager
        self.use_template = use_template
        self.current_mode = current_mode
        self.log = logging.getLogger("PublishWorker")

    def run(self):
        """执行多图文的上传和发布草稿逻辑"""
        try:
            final_articles_for_wechat_api = []
            uploaded_images_cache = {}

            for i, article_data in enumerate(self.articles_data):
                title = article_data.get('title', '无标题')
                progress_message = f"正在处理文章 {i+1}/{len(self.articles_data)}: \"{title}\""
                self.log.info(progress_message)
                self.progress_updated.emit(progress_message)

                markdown_content = article_data['markdown_content']
                if self.use_template:
                    header, footer = self.template_manager.get_templates()
                    full_markdown_content = f"{header}\n\n{markdown_content}\n\n{footer}"
                else:
                    full_markdown_content = markdown_content
                
                article_theme = article_data.get('theme', 'default')
                self.renderer.set_theme(article_theme)
                html_content = self.renderer.render(full_markdown_content, mode=self.current_mode)

                digest = article_data.get('digest', '')
                if not digest:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    first_p = soup.find('p')
                    if first_p:
                        digest = first_p.get_text()
                digest = digest[:100]

                self.progress_updated.emit(f"正在上传 \"{title}\" 的封面图...")
                cover_image_path = article_data.get('cover_image', '')
                thumb_media_id, cover_url = self.wechat_api.get_thumb_media_id_and_url(cover_image_path)

                if not thumb_media_id:
                    raise Exception(f"文章 \"{title}\" 获取封面图失败。")

                if cover_image_path and cover_url:
                    uploaded_images_cache[cover_image_path] = cover_url

                self.progress_updated.emit(f"正在上传 \"{title}\" 的正文图片...")
                final_html_content = self.wechat_api.process_content_images(html_content, uploaded_images_cache)

                api_article_data = {
                    'title': title[:64],
                    'author': article_data.get('author', self.wechat_api.default_author),
                    'digest': digest,
                    'content': final_html_content,
                    'thumb_media_id': thumb_media_id,
                    'content_source_url': article_data.get('content_source_url', ''),
                    'need_open_comment': 1,
                    'show_cover_pic': 1
                }
                final_articles_for_wechat_api.append(api_article_data)

            self.progress_updated.emit("所有文章处理完毕，正在创建草稿...")
            self.log.info("All articles processed. Attempting to create multi-article draft.")
            media_id, error_message = self.wechat_api.create_draft(articles=final_articles_for_wechat_api)

            if media_id:
                success_msg = f"包含 {len(final_articles_for_wechat_api)} 篇文章的草稿已成功发布！\nMedia ID: {media_id}"
                self.log.info(success_msg)
                
                self.progress_updated.emit("发布成功！正在本地存档HTML文件...")
                for i, article_data in enumerate(self.articles_data):
                    title = final_articles_for_wechat_api[i]['title']
                    final_html_content = final_articles_for_wechat_api[i]['content']
                    self.storage_manager.save_html_archive(title, final_html_content)
                
                self.finished.emit(True, success_msg + "\n\n所有文章的HTML内容均已在本地存档。")
            else:
                raise Exception(f"多图文草稿发布失败: {error_message}")

        except Exception as e:
            error_msg = f"发布过程中出现错误: {e}"
            self.log.error(error_msg, exc_info=True)
            self.finished.emit(False, error_msg)

class CrawlWorker(QObject):
    progress_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, object) # bool: success, object: result dict or error string

    def __init__(self, url, system_prompt):
        super().__init__()
        self.url = url
        self.system_prompt = system_prompt
        self.log = logging.getLogger("CrawlWorker")

    def run(self):
        try:
            # 1. 抓取内容
            self.progress_updated.emit("正在从网页抓取内容...")
            crawler = Crawler()
            markdown_content, error = crawler.fetch(self.url)
            if error:
                raise Exception(f"抓取失败: {error}")

            # 2. 调用LLM处理
            self.progress_updated.emit("正在由AI处理内容...")
            llm_processor = LLMProcessor()
            processed_content, error = llm_processor.process_content(markdown_content, self.system_prompt)
            if error:
                raise Exception(f"AI处理失败: {error}")

            # 3. 成功，发送结果
            result = {
                'url': self.url,
                'content': processed_content
            }
            self.finished.emit(True, result)

        except Exception as e:
            self.log.error(f"Failed to crawl and process article: {e}", exc_info=True)
            self.finished.emit(False, str(e))


class CustomWebEngineView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.html_content = ""
        # 设置页面背景为透明，以便HTML中的body背景色可以显示出来
        self.page().setBackgroundColor(QColor("transparent"))
        
        # 为滚动同步设置WebChannel
        self.channel = QWebChannel(self.page())
        self.page().setWebChannel(self.channel)
        # 将父窗口（MainWindow）注册为可从JS调用的对象
        self.channel.registerObject("scroll_handler", parent)

    def set_html_content(self, html):
        self.html_content = html
        
        # 注入用于滚动同步的JavaScript代码
        js_to_inject = """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    // 将Python注册的对象暴露给JS
                    window.scroll_handler = channel.objects.scroll_handler;
                    
                    // 监听滚动事件
                    window.addEventListener('scroll', function() {
                        if (window.scroll_handler) {
                            const scrollableHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                            if (scrollableHeight > 0) {
                                let percentage = window.scrollY / scrollableHeight;
                                // 将滚动百分比发送回Python
                                window.scroll_handler.on_preview_scrolled(percentage);
                            }
                        }
                    });
                });
            });
        </script>
        """
        full_html = js_to_inject + html
        self.setHtml(full_html, baseUrl=QUrl.fromLocalFile(os.path.abspath(".")))

    def contextMenuEvent(self, event):
        # 创建一个标准的Web视图右键菜单
        menu = self.page().createStandardContextMenu()
        
        # --- 在菜单顶部添加自定义操作 ---
        
        # 1. 复制HTML内容
        copy_html_action = QAction("复制渲染后的HTML", self)
        copy_html_action.triggered.connect(self.copy_html_content)
        menu.insertAction(menu.actions()[0], copy_html_action) # 插入到最前面

        # 2. 显示源代码
        show_source_action = QAction("显示源代码", self)
        show_source_action.triggered.connect(self.show_source)
        menu.insertAction(menu.actions()[1], show_source_action) # 插入到第二个

        # 3. 添加分隔符
        menu.insertSeparator(menu.actions()[2])

        # 执行菜单
        menu.exec_(event.globalPos())

    def copy_html_content(self):
        """将渲染后的HTML内容复制到剪贴板。"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.html_content)
        # 可选：可以添加一个状态栏提示
        # self.parent().statusBar().showMessage("HTML内容已复制到剪贴板", 2000)
        logging.getLogger("MdToWeChat").info("Rendered HTML content copied to clipboard.")

    def show_source(self):
        dialog = SourceDialog(self.html_content, self)
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
