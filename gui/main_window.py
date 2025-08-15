import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QTextEdit, QAction, QFileDialog, QSplitter, QActionGroup, 
                             QMenu, QListWidget, QPushButton, QListWidgetItem, QFrame, QLabel)
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
        self.current_mode = "light"
        self.use_template = True
        
        self.articles = []
        self.current_article_index = -1
        self._is_switching_articles = False
        self._is_syncing_scroll = False

        self._init_ui()
        self._create_menu_bar()
        self._init_articles()
        self._apply_mode_styles()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_pane.setFixedWidth(250)

        mode_toggle_container_layout = QHBoxLayout()
        mode_toggle_layout = QHBoxLayout()
        mode_toggle_layout.addWidget(QLabel("显示模式:"))
        self.mode_toggle_btn = QPushButton()
        self.mode_toggle_btn.setFixedSize(QSize(60, 28))
        self.mode_toggle_btn.setToolTip("点击切换亮色/暗黑模式")
        self.mode_toggle_btn.clicked.connect(self._toggle_mode)
        self._update_mode_toggle_button()
        mode_toggle_layout.addWidget(self.mode_toggle_btn)
        
        mode_toggle_container_layout.addStretch()
        mode_toggle_container_layout.addLayout(mode_toggle_layout)
        mode_toggle_container_layout.addStretch()
        left_layout.addLayout(mode_toggle_container_layout)

        article_action_layout = QHBoxLayout()
        add_article_btn = QPushButton(" 新增文章")
        add_article_btn.setIcon(QIcon.fromTheme("list-add"))
        add_article_btn.setFixedSize(QSize(100, 35))
        add_article_btn.setToolTip("新增一篇文章")
        add_article_btn.clicked.connect(self._add_article)
        
        remove_article_btn = QPushButton(" 删除文章")
        remove_article_btn.setIcon(QIcon.fromTheme("list-remove"))
        remove_article_btn.setFixedSize(QSize(100, 35))
        remove_article_btn.setToolTip("删除当前文章")
        remove_article_btn.clicked.connect(self._remove_article)

        article_action_layout.addWidget(add_article_btn)
        article_action_layout.addWidget(remove_article_btn)
        left_layout.addLayout(article_action_layout)

        crawl_layout = QHBoxLayout()
        crawl_article_btn = QPushButton(" 从网页地址抓取内容")
        crawl_article_btn.setIcon(QIcon.fromTheme("web-browser"))
        crawl_article_btn.setFixedHeight(35)
        crawl_article_btn.setToolTip("从网页抓取内容并由AI生成文章")
        crawl_article_btn.clicked.connect(self._crawl_article)
        crawl_layout.addStretch()
        crawl_layout.addWidget(crawl_article_btn)
        crawl_layout.addStretch()
        left_layout.addLayout(crawl_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator)

        self.article_list_widget = QListWidget()
        self.article_list_widget.currentRowChanged.connect(self._select_article)
        self.article_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.article_list_widget.customContextMenuRequested.connect(self._show_article_list_context_menu)
        font = QFont()
        font.setPointSize(11) 
        self.article_list_widget.setFont(font)
        self.article_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }")
        left_layout.addWidget(self.article_list_widget)
        
        editor_preview_splitter = QSplitter(Qt.Horizontal)

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

        self.html_preview = CustomWebEngineView(self)
        editor_preview_splitter.addWidget(self.html_preview)
        
        editor_preview_splitter.setSizes([self.width() // 2, self.width() // 2])

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_pane)
        main_splitter.addWidget(editor_preview_splitter)
        main_splitter.setSizes([200, self.width() - 200])
        
        main_layout.addWidget(main_splitter)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

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

        theme_menu = menu_bar.addMenu("主题")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        available_themes = self.renderer.get_available_themes()
        for theme_name in available_themes:
            display_name = theme_name.replace("_", " ").title()
            action = QAction(display_name, self, checkable=True)

            action.triggered.connect(partial(self._change_theme, theme_name))

            self.theme_group.addAction(action)
            theme_menu.addAction(action)

        publish_menu = menu_bar.addMenu("发布")
        publish_wechat_action = QAction("发布到微信公众号", self)
        publish_wechat_action.triggered.connect(self._publish_to_wechat)
        publish_menu.addAction(publish_wechat_action)

        template_menu = menu_bar.addMenu("模板")
        
        edit_template_action = QAction("编辑模板...", self)
        edit_template_action.triggered.connect(self._open_template_editor)
        template_menu.addAction(edit_template_action)

        template_menu.addSeparator()

        self.use_template_action = QAction("使用模板", self, checkable=True)
        self.use_template_action.setChecked(self.use_template)
        self.use_template_action.triggered.connect(self._toggle_template_usage)
        template_menu.addAction(self.use_template_action)

        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _init_articles(self):
        self.articles = [{'title': '未命名文章 1', 'content': '# 未命名文章 1\n\n', 'theme': 'blue_glow'}]
        self.current_article_index = 0
        self._refresh_article_list()
        self._load_article_content(self.current_article_index)

    def _refresh_article_list(self):
        self.article_list_widget.blockSignals(True)
        self.article_list_widget.clear()
        for i, article in enumerate(self.articles):
            parsed_title = self.parser.parse_markdown(article['content']).get('title', article['title'])
            self.articles[i]['title'] = parsed_title
            item = QListWidgetItem(f"{i+1}. {parsed_title}")
            self.article_list_widget.addItem(item)
        
        if self.current_article_index >= 0:
            self.article_list_widget.setCurrentRow(self.current_article_index)
        self.article_list_widget.blockSignals(False)

    def _add_article(self):
        self._update_current_article_content()
        new_article_num = len(self.articles) + 1
        new_article = {'title': f'未命名文章 {new_article_num}', 'content': f'# 未命名文章 {new_article_num}\n\n', 'theme': 'default'}
        self.articles.append(new_article)
        self.current_article_index = len(self.articles) - 1
        self._refresh_article_list()
        self._load_article_content(self.current_article_index)

    def _crawl_article(self):
        dialog = CrawlDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        url, system_prompt = dialog.get_data()
        self.log.info(f"Starting crawl for url: {url}")

        self.status_dialog = StatusDialog(title="文章生成中", parent=self)
        self.status_dialog.show()
        QApplication.processEvents()

        self.crawl_thread = QThread()
        self.crawl_worker = CrawlWorker(url, system_prompt)
        self.crawl_worker.moveToThread(self.crawl_thread)

        self.crawl_worker.progress_updated.connect(self._on_crawl_progress)
        self.crawl_worker.finished.connect(self._on_crawl_finished)
        self.crawl_thread.started.connect(self.crawl_worker.run)

        self.crawl_thread.start()
        self.log.info("Crawl thread started.")

    def _remove_article(self):
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
        if self._is_switching_articles or index == self.current_article_index:
            return

        self._is_switching_articles = True
        try:
            if self.current_article_index != -1:
                self._update_current_article_content(refresh_list=False)
            
            self.current_article_index = index
            self._load_article_content(index)
        finally:
            self._is_switching_articles = False

    def _load_article_content(self, index):
        if 0 <= index < len(self.articles):
            self.markdown_editor.blockSignals(True)
            self.markdown_editor.setPlainText(self.articles[index]['content'])
            self.markdown_editor.blockSignals(False)
            self._update_preview()
            self._update_theme_menu_selection()

    def _update_current_article_content(self, refresh_list=True):
        if 0 <= self.current_article_index < len(self.articles):
            self.articles[self.current_article_index]['content'] = self.markdown_editor.toPlainText()
            self._update_preview()
            if refresh_list and not self._is_switching_articles:
                self._refresh_article_list()
            
    def _update_preview(self):
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
        reply = QMessageBox.question(self, '确认操作', "此操作将清空所有已编辑的文章，确定要新建吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.articles = []
            self.current_article_index = -1
            self._init_articles()
            self.setWindowTitle("微信公众号Markdown渲染发布系统 - 未命名")
            self.log.info("New document created, all articles cleared.")

    def _open_document(self):
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
            self.current_article_index = len(self.articles) - 1
            self._refresh_article_list()
            self._load_article_content(self.current_article_index)
            self.setWindowTitle(f"微信公众号Markdown渲染发布系统 - {os.path.basename(file_paths[-1])}")

    def _save_document(self):
        if not (0 <= self.current_article_index < len(self.articles)):
            QMessageBox.warning(self, "保存失败", "没有可保存的文章。")
            return
        self._save_single_article(self.current_article_index)

    def _save_all_documents(self):
        if not self.articles:
            QMessageBox.warning(self, "保存失败", "没有可保存的文章。")
            return
        
        self.log.info("Attempting to save all articles.")
        saved_count = 0
        for i in range(len(self.articles)):
            if self._save_single_article(i):
                saved_count += 1
        
        QMessageBox.information(self, "全部保存完成", f"成功保存 {saved_count} / {len(self.articles)} 篇文章。")
        self.log.info(f"Finished saving all articles. Saved {saved_count}/{len(self.articles)}.")

    def _save_single_article(self, index):
        if not (0 <= index < len(self.articles)):
            return False

        article = self.articles[index]
        if index == self.current_article_index:
            markdown_content = self.markdown_editor.toPlainText()
            article['content'] = markdown_content
        else:
            markdown_content = article['content']
            
        title = article['title']
        original_filepath = article.get('file_path')

        if not markdown_content.strip():
            self.log.warning(f"Save cancelled for article '{title}': content is empty.")
            return True

        filepath_to_save = original_filepath
        if not filepath_to_save:
            suggested_filename = self.storage_manager._generate_filename(title, ".md")
            filepath_to_save, _ = QFileDialog.getSaveFileName(
                self, f"保存文章: {title}", suggested_filename, "Markdown Files (*.md);;All Files (*)"
            )
            if not filepath_to_save:
                self.log.info(f"Save operation cancelled by user for article '{title}'.")
                return False
            article['file_path'] = filepath_to_save

        try:
            self.storage_manager.save_markdown_file(filepath_to_save, markdown_content)
            self.log.info(f"Article '{title}' saved to: {filepath_to_save}")
            if index == self.current_article_index:
                 self.setWindowTitle(f"微信公众号Markdown渲染发布系统 - {os.path.basename(filepath_to_save)}")
            return True
        except Exception as e:
            self.log.error(f"Failed to save article '{title}' to {filepath_to_save}: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存文章 \"{title}\" 失败: {e}")
            return False

    def _publish_to_wechat(self):
        self._update_current_article_content()

        if not self.articles:
            QMessageBox.warning(self, "操作失败", "没有可发布的文章。")
            return
            
        if len(self.articles) > 8:
            QMessageBox.warning(self, "文章数量超限", "微信多图文消息最多支持8篇文章。")
            return

        self.log.info("Parsing all articles for multi-article publishing.")
        all_articles_data = []
        for article in self.articles:
            parsed_data = self.parser.parse_markdown(article['content'])
            parsed_data['markdown_content'] = article['content']
            parsed_data['theme'] = article.get('theme', 'default')
            
            if not parsed_data.get('author'):
                parsed_data['author'] = self.wechat_api.default_author
            
            all_articles_data.append(parsed_data)
        
        dialog = PublishDialog(all_articles_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self.log.info("Multi-article publish dialog accepted.")
            final_articles_data = dialog.get_data()
            self._execute_multi_article_publishing(final_articles_data)
        else:
            self.log.info("Multi-article publish dialog cancelled by user.")

    def _execute_multi_article_publishing(self, all_articles_data):
        self.status_dialog = StatusDialog(title="发布到微信", parent=self)
        self.status_dialog.show()
        QApplication.processEvents()

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

        self.publish_worker.progress_updated.connect(self._on_publish_progress)
        self.publish_worker.finished.connect(self._on_publish_finished)
        self.publish_thread.started.connect(self.publish_worker.run)
        
        self.publish_thread.start()
        self.log.info("Publishing thread started.")

    def _on_publish_progress(self, message):
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=False)

    def _on_publish_finished(self, success, message):
        QApplication.beep()
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=True)
        
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
                final_message = f"操作失败: {result}"
                self.log.error(f"Failed to crawl and process article: {result}")
            
            self.status_dialog.update_status(final_message, is_finished=True)

        self.crawl_thread.quit()
        self.crawl_thread.wait()
        self.crawl_worker.deleteLater()
        self.crawl_thread.deleteLater()
        self.log.info("Crawl thread and worker cleaned up.")

    def _show_article_list_context_menu(self, position):
        item = self.article_list_widget.itemAt(position)
        if not item:
            return

        row = self.article_list_widget.row(item)

        menu = QMenu()
        move_up_action = QAction("向上移动", self)
        move_down_action = QAction("向下移动", self)
        delete_action = QAction("删除文章", self)

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
        if row > 0:
            self.articles[row], self.articles[row - 1] = self.articles[row - 1], self.articles[row]
            self.current_article_index = row - 1
            self._refresh_article_list()

    def _move_article_down(self, row):
        if row < len(self.articles) - 1:
            self.articles[row], self.articles[row + 1] = self.articles[row + 1], self.articles[row]
            self.current_article_index = row + 1
            self._refresh_article_list()

    def _show_about_dialog(self):
        self.log.info("Showing 'About' dialog.")
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, "关于", "微信公众号Markdown渲染发布系统 v1.0\n\n一个简化微信公众号文章发布的桌面工具。")

    def _open_template_editor(self):
        dialog = TemplateEditorDialog(self)
        dialog.exec_()
        if self.use_template:
            self._update_preview()

    def _toggle_template_usage(self, checked):
        self.use_template = checked
        self.log.info(f"Template usage set to: {self.use_template}")
        self._update_preview()

    def _change_theme(self, theme_name):
        if 0 <= self.current_article_index < len(self.articles):
            current_article = self.articles[self.current_article_index]
            if current_article.get('theme') != theme_name:
                current_article['theme'] = theme_name
                self._update_preview()
                self.log.info(f"Theme for article '{current_article['title']}' changed to: {theme_name}")

    def _update_theme_menu_selection(self):
        if not (0 <= self.current_article_index < len(self.articles)):
            return

        theme_name = self.articles[self.current_article_index].get('theme', 'default')
        for action in self.theme_group.actions():
            action_theme_name = action.text().replace(" ", "_").lower()
            if action_theme_name == theme_name:
                action.setChecked(True)
                break

    def _open_settings_dialog(self):
        dialog = SettingsDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.wechat_api = WeChatAPI()
            self.log.info("Settings saved and configuration reloaded.")

    def _on_editor_scrolled(self, value):
        if self._is_syncing_scroll:
            return
            
        editor_scrollbar = self.markdown_editor.verticalScrollBar()
        if editor_scrollbar.maximum() == 0:
            return
            
        scroll_percentage = value / editor_scrollbar.maximum()
        
        js_code = f"window.scrollTo(0, document.body.scrollHeight * {scroll_percentage});"
        
        self._is_syncing_scroll = True
        self.html_preview.page().runJavaScript(js_code)
        QTimer.singleShot(100, lambda: setattr(self, '_is_syncing_scroll', False))

    @pyqtSlot(float)
    def on_preview_scrolled(self, percentage):
        if self._is_syncing_scroll:
            return
            
        editor_scrollbar = self.markdown_editor.verticalScrollBar()
        max_val = editor_scrollbar.maximum()
        
        self._is_syncing_scroll = True
        editor_scrollbar.setValue(int(max_val * percentage))
        QTimer.singleShot(100, lambda: setattr(self, '_is_syncing_scroll', False))

    def _toggle_mode(self):
        if self.current_mode == "light":
            self.current_mode = "dark"
        else:
            self.current_mode = "light"
        
        self._apply_mode_styles()
        self._update_preview()
        self._update_mode_toggle_button()
        self.log.info(f"Mode changed to: {self.current_mode}")

    def _update_mode_toggle_button(self):
        if self.current_mode == "dark":
            self.mode_toggle_btn.setText("暗黑")
            self.mode_toggle_btn.setStyleSheet("QPushButton { background-color: #555; color: white; border: 1px solid #777; border-radius: 5px; }"
                                               "QPushButton:hover { background-color: #666; }")
        else:
            self.mode_toggle_btn.setText("明亮")
            self.mode_toggle_btn.setStyleSheet("QPushButton { background-color: #eee; color: black; border: 1px solid #ccc; border-radius: 5px; }"
                                               "QPushButton:hover { background-color: #ddd; }")

    def _apply_mode_styles(self):
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
                    border-radius: 5px;
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
        else:
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
    finished = pyqtSignal(bool, object)

    def __init__(self, url, system_prompt):
        super().__init__()
        self.url = url
        self.system_prompt = system_prompt
        self.log = logging.getLogger("CrawlWorker")

    def run(self):
        try:
            self.progress_updated.emit("正在从网页抓取内容...")
            crawler = Crawler()
            markdown_content, error = crawler.fetch(self.url)
            if error:
                raise Exception(f"抓取失败: {error}")

            self.progress_updated.emit("正在由AI处理内容...")
            llm_processor = LLMProcessor()
            processed_content, error = llm_processor.process_content(markdown_content, self.system_prompt)
            if error:
                raise Exception(f"AI处理失败: {error}")

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
        self.page().setBackgroundColor(QColor("transparent"))
        
        self.channel = QWebChannel(self.page())
        self.page().setWebChannel(self.channel)
        self.channel.registerObject("scroll_handler", parent)

    def set_html_content(self, html):
        self.html_content = html
        
        js_to_inject = """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.scroll_handler = channel.objects.scroll_handler;
                    
                    window.addEventListener('scroll', function() {
                        if (window.scroll_handler) {
                            const scrollableHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                            if (scrollableHeight > 0) {
                                let percentage = window.scrollY / scrollableHeight;
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
        menu = QMenu(self)
        
        show_source_action = QAction("显示源代码", self)
        show_source_action.triggered.connect(self.show_source)
        menu.addAction(show_source_action)
        
        menu.exec_(event.globalPos())

    def show_source(self):
        dialog = SourceDialog(self.html_content, self)
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
