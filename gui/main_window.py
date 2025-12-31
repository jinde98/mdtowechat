import sys
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QTextEdit, QFileDialog, QSplitter, 
                             QMenu, QListWidget, QPushButton, QListWidgetItem, QFrame, QLabel, QAbstractItemView, QLineEdit)
from functools import partial
import os
import yaml
from PySide6.QtWebEngineWidgets import QWebEngineView
import logging
from PySide6.QtCore import Qt, QUrl, QSize, Slot, QTimer, QObject, QThread, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QColor, QFont, QIcon
from bs4 import BeautifulSoup

# 将项目根目录添加到sys.path，以便正确解析模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
from gui.rewrite_dialog import RewriteDialog
from PySide6.QtWidgets import QDialog, QMessageBox
from core.crawler import Crawler
from core.llm import LLMProcessor
from core.workers import CrawlWorker, ImageUploadWorker, PublishWorker, RewriteWorker

class MainWindow(QMainWindow):
    """
    应用程序的主窗口类。
    
    该类是整个应用的核心，负责：
    - 构建和管理主界面的所有UI组件（文章列表、编辑器、预览区等）。
    - 响应用户的各种操作（如新增/删除文章、保存、发布、切换主题等）。
    - 调度核心逻辑模块（如渲染器、解析器、API客户端）来完成具体任务。
    - 管理后台工作线程（Workers），以在不阻塞UI的情况下执行耗时操作。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("微信公众号Markdown渲染发布系统")
        
        # --- 窗口初始化 ---
        # 获取屏幕可用尺寸，并设置窗口为屏幕的80%，居中显示
        screen_rect = QApplication.primaryScreen().availableGeometry()
        width = int(screen_rect.width() * 0.8)
        height = int(screen_rect.height() * 0.8)
        x = int((screen_rect.width() - width) / 2)
        y = int((screen_rect.height() - height) / 2)
        self.setGeometry(x, y, width, height)
        self.log = logging.getLogger(__name__)

        # --- 核心服务实例化 ---
        self.renderer = MarkdownRenderer()
        self.parser = ContentParser()
        self.storage_manager = StorageManager()
        self.wechat_api = WeChatAPI()
        self.template_manager = TemplateManager()
        
        # --- 状态变量初始化 ---
        self.current_mode = "light"  # 当前UI模式: 'light' 或 'dark'
        self.use_template = True     # 是否在渲染时应用页眉/页脚模板
        
        self.articles = []  # 内存中存储所有文章数据的列表
        self.current_article_index = -1  # 当前选中的文章在列表中的索引
        
        # --- 标志位，用于防止UI事件重入或循环触发 ---
        self._is_switching_articles = False  # 正在切换文章的标志，防止在切换过程中触发内容保存
        self._is_syncing_scroll = False     # 正在同步滚动的标志，防止编辑器和预览区无限循环同步滚动

        # --- 后台任务相关状态 ---
        self.crawl_queue = []  # 网页抓取任务队列
        self.crawl_thread = None
        self.crawl_worker = None
        self.crawling_article_index = -1 # 记录当前正在被抓取任务更新的文章索引
        
        self.rewrite_thread = None
        self.rewrite_worker = None
        self.is_rewriting = False  # AI改写任务是否正在进行的标志

        # --- UI构建和初始化 ---
        self._init_ui()
        self._create_menu_bar()
        self._init_articles()
        self._apply_mode_styles() # 应用初始的UI样式

    def _init_ui(self):
        """
        初始化主窗口的用户界面布局。
        主界面是一个三栏式布局：左侧是文章和功能区，中间是Markdown编辑器，右侧是HTML实时预览。
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 左侧面板：功能区和文章列表 ---
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_pane.setFixedWidth(250)

        # 亮/暗模式切换
        mode_toggle_layout = QHBoxLayout()
        mode_toggle_layout.addWidget(QLabel("显示模式:"))
        self.mode_toggle_btn = QPushButton()
        self.mode_toggle_btn.setFixedSize(QSize(60, 28))
        self.mode_toggle_btn.setToolTip("点击切换亮色/暗黑模式")
        self.mode_toggle_btn.clicked.connect(self._toggle_mode)
        self._update_mode_toggle_button()
        mode_toggle_layout.addWidget(self.mode_toggle_btn)
        mode_toggle_layout.addStretch() # 使按钮居左
        left_layout.addLayout(mode_toggle_layout)

        # 新增/删除文章按钮
        article_action_layout = QHBoxLayout()
        add_article_btn = QPushButton(" 新增文章")
        add_article_btn.setIcon(QIcon.fromTheme("list-add"))
        add_article_btn.clicked.connect(self._add_article)
        remove_article_btn = QPushButton(" 删除文章")
        remove_article_btn.setIcon(QIcon.fromTheme("list-remove"))
        remove_article_btn.clicked.connect(self._remove_article)
        article_action_layout.addWidget(add_article_btn)
        article_action_layout.addWidget(remove_article_btn)
        left_layout.addLayout(article_action_layout)

        # 网页抓取和AI改写功能区
        ai_section_layout = QVBoxLayout()
        self.crawl_url_input = QLineEdit()
        self.crawl_url_input.setPlaceholderText("在此输入网页URL进行抓取")
        ai_section_layout.addWidget(self.crawl_url_input)
        crawl_article_btn = QPushButton(" 从网页抓取内容")
        crawl_article_btn.setIcon(QIcon.fromTheme("web-browser"))
        crawl_article_btn.clicked.connect(self._crawl_article)
        ai_section_layout.addWidget(crawl_article_btn)
        rewrite_article_btn = QPushButton(" AI改写当前文章")
        rewrite_article_btn.setIcon(QIcon.fromTheme("document-edit"))
        rewrite_article_btn.clicked.connect(self._rewrite_article)
        ai_section_layout.addWidget(rewrite_article_btn)
        left_layout.addLayout(ai_section_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator)

        # 文章列表
        self.article_list_widget = QListWidget()
        self.article_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection) # 允许多选删除
        self.article_list_widget.currentRowChanged.connect(self._select_article)
        self.article_list_widget.setContextMenuPolicy(Qt.CustomContextMenu) # 启用右键菜单
        self.article_list_widget.customContextMenuRequested.connect(self._show_article_list_context_menu)
        left_layout.addWidget(self.article_list_widget)
        
        # --- 中间和右侧面板：编辑器和预览区 ---
        editor_preview_splitter = QSplitter(Qt.Horizontal)

        # 中间面板: Markdown 编辑器
        self.markdown_editor = PastingImageEditor(wechat_api=self.wechat_api)
        self.markdown_editor.verticalScrollBar().valueChanged.connect(self._on_editor_scrolled)
        self.markdown_editor.setFontPointSize(14)
        self.markdown_editor.setPlaceholderText("在此输入Markdown内容...")
        self.markdown_editor.textChanged.connect(self._update_current_article_content)
        editor_preview_splitter.addWidget(self.markdown_editor)

        # 右侧面板: HTML 实时预览
        self.html_preview = CustomWebEngineView(self)
        editor_preview_splitter.addWidget(self.html_preview)
        editor_preview_splitter.setSizes([self.width() // 2, self.width() // 2]) # 均分宽度

        # --- 主分割器 ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_pane)
        main_splitter.addWidget(editor_preview_splitter)
        main_splitter.setSizes([250, self.width() - 250]) # 固定左侧面板宽度
        
        main_layout.addWidget(main_splitter)

    def _create_menu_bar(self):
        """
        创建并初始化顶部的菜单栏。
        """
        menu_bar = self.menuBar()

        # --- 文件菜单 ---
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("清空所有", self._clear_all_articles)
        file_menu.addAction("打开...", self._open_document)
        file_menu.addAction("保存", self._save_document)
        file_menu.addAction("全部保存", self._save_all_documents)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        # --- 编辑菜单 ---
        edit_menu = menu_bar.addMenu("编辑")
        undo_action = QAction("撤销", self, shortcut="Ctrl+Z", triggered=self.markdown_editor.undo)
        redo_action = QAction("重做", self, shortcut="Ctrl+Y", triggered=self.markdown_editor.redo)
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction("AI 改写文章...", self._rewrite_article)
        edit_menu.addSeparator()
        edit_menu.addAction("设置...", self._open_settings_dialog)

        # --- 主题菜单 ---
        theme_menu = menu_bar.addMenu("主题")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True) # 确保每次只能选择一个主题
        available_themes = self.renderer.get_available_themes()
        for theme_name in available_themes:
            display_name = theme_name.replace("_", " ").title()
            action = QAction(display_name, self, checkable=True)
            # 使用 functools.partial 来在点击时传递正确的主题名称
            action.triggered.connect(partial(self._change_theme, theme_name))
            self.theme_group.addAction(action)
            theme_menu.addAction(action)

        # --- 发布菜单 ---
        publish_menu = menu_bar.addMenu("发布")
        publish_menu.addAction("发布到微信公众号", self._publish_to_wechat)

        # --- 模板菜单 ---
        template_menu = menu_bar.addMenu("模板")
        template_menu.addAction("编辑模板...", self._open_template_editor)
        template_menu.addSeparator()
        self.use_template_action = QAction("使用模板", self, checkable=True)
        self.use_template_action.setChecked(self.use_template)
        self.use_template_action.triggered.connect(self._toggle_template_usage)
        template_menu.addAction(self.use_template_action)

        # --- 帮助菜单 ---
        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction("关于", self._show_about_dialog)

    def _init_articles(self):
        """
        初始化或重置文章列表和编辑器状态。
        """
        self.articles = []
        self.current_article_index = -1
        self._refresh_article_list()
        self.markdown_editor.clear()
        self.html_preview.set_html_content("")
        self.setWindowTitle("微信公众号Markdown渲染发布系统")

    def _refresh_article_list(self):
        """
        刷新左侧的文章列表UI。
        此方法会根据 self.articles 列表重新填充 QListWidget。
        """
        # 暂时阻塞信号，防止在重新填充列表时触发不必要的 currentRowChanged 信号
        self.article_list_widget.blockSignals(True)
        self.article_list_widget.clear()
        
        for i, article in enumerate(self.articles):
            # 每次刷新时，都尝试从Markdown内容中解析最新的标题
            parsed_title = self.parser.parse_markdown(article['content']).get('title', article['title'])
            self.articles[i]['title'] = parsed_title
            item = QListWidgetItem(f"{i+1}. {parsed_title}")
            self.article_list_widget.addItem(item)
        
        # 恢复之前选中的项目
        if 0 <= self.current_article_index < len(self.articles):
            self.article_list_widget.setCurrentRow(self.current_article_index)
        
        self.article_list_widget.blockSignals(False)

    def _add_article(self):
        """
        响应“新增文章”按钮，向列表中添加一篇新的空白文章。
        """
        self._update_current_article_content()  # 先保存对当前文章的修改
        
        new_article_num = len(self.articles) + 1
        new_article = {
            'title': f'未命名文章 {new_article_num}', 
            'content': f'# 未命名文章 {new_article_num}\n\n', 
            'theme': 'blue_glow'
        }
        self.articles.append(new_article)
        
        # 切换到这篇新文章
        self.current_article_index = len(self.articles) - 1
        self._refresh_article_list()
        self._load_article_content(self.current_article_index)

    def _crawl_article(self):
        """
        响应“从网页抓取”按钮，将一个抓取任务添加到队列中。
        """
        url = self.crawl_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "输入错误", "请输入有效的网页URL。")
            return

        # 从配置中加载用于抓取的 System Prompt
        system_prompt = self.wechat_api.config_manager.get('llm.system_prompt', '')
        if not system_prompt:
            QMessageBox.warning(self, "配置错误", "抓取文章处理提示词（System Prompt）为空，请先在“设置”中配置。")
            return

        # 在UI中创建一个占位符文章，告知用户任务已加入队列
        self._update_current_article_content()
        placeholder_title = f"排队中 - {url.split('/')[-1]}"
        placeholder_content = f"# 任务已加入队列\n\n等待抓取: {url}"
        new_article = {'title': placeholder_title, 'content': placeholder_content, 'theme': 'blue_glow'}
        
        self.articles.append(new_article)
        new_article_index = len(self.articles) - 1
        
        # 将任务（URL、Prompt、文章索引）添加到队列
        self.crawl_queue.append((url, system_prompt, new_article_index))
        self.log.info(f"已将URL加入抓取队列: {url}")

        # 切换到这个占位文章并清空输入框
        self.current_article_index = new_article_index
        self._refresh_article_list()
        self._load_article_content(self.current_article_index)
        self.crawl_url_input.clear()

        # 尝试处理队列中的任务
        self._process_crawl_queue()

    def _rewrite_article(self):
        """
        响应“AI改写”按钮，为当前文章启动一个后台改写任务。
        """
        if not (0 <= self.current_article_index < len(self.articles)):
            QMessageBox.warning(self, "操作失败", "没有可改写的文章。")
            return
            
        if self.is_rewriting:
            QMessageBox.warning(self, "操作繁忙", "已有改写任务在进行中，请稍后再试。")
            return

        current_content = self.markdown_editor.toPlainText()
        if not current_content.strip():
            QMessageBox.warning(self, "操作失败", "文章内容为空，无法改写。")
            return

        # 弹出对话框让用户输入自定义要求
        dialog = RewriteDialog(current_content, self)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        custom_prompt = dialog.get_data()
        # 获取用户可能在对话框中临时修改过的 System Prompt
        system_prompt = dialog.system_prompt_input.toPlainText()

        # 设置状态并启动后台Worker
        self.is_rewriting = True
        self.status_dialog = StatusDialog(title="AI改写中", parent=self)
        self.status_dialog.show()
        self.status_dialog.update_status("正在调用AI进行改写，请稍候...", is_finished=False)
        QApplication.processEvents() # 确保状态对话框能及时显示

        self.rewrite_thread = QThread()
        self.rewrite_worker = RewriteWorker(current_content, custom_prompt, system_prompt)
        self.rewrite_worker.moveToThread(self.rewrite_thread)
        self.rewrite_worker.finished.connect(self._on_rewrite_finished)
        self.rewrite_thread.started.connect(self.rewrite_worker.run)
        self.rewrite_thread.start()
        self.log.info("AI改写后台线程已启动。")

    def _process_crawl_queue(self):
        """
        处理抓取队列中的下一个任务。
        这是一个简单的FIFO（先进先出）队列处理器。
        """
        # 如果当前有任务正在运行，或者队列为空，则不执行任何操作
        if self.crawl_worker is not None or not self.crawl_queue:
            return

        url, system_prompt, article_index = self.crawl_queue.pop(0)
        self.crawling_article_index = article_index
        
        self.log.info(f"开始处理抓取任务: {url}")

        # 更新UI，告知用户哪个任务正在被处理
        article = self.articles[self.crawling_article_index]
        article['title'] = f"抓取中 - {url.split('/')[-1]}"
        article['content'] = f"# 正在抓取内容...\n\n从URL: {url}"
        self._refresh_article_list()
        if self.current_article_index == self.crawling_article_index:
            self._load_article_content(self.crawling_article_index)
        QApplication.processEvents()

        # 创建并启动后台Worker
        self.crawl_thread = QThread()
        self.crawl_worker = CrawlWorker(url, system_prompt)
        self.crawl_worker.moveToThread(self.crawl_thread)
        self.crawl_worker.progress.connect(self._on_crawl_progress)
        self.crawl_worker.finished.connect(self._on_crawl_finished)
        self.crawl_thread.started.connect(self.crawl_worker.run)
        self.crawl_thread.start()
        self.log.info("网页抓取后台线程已启动。")

    def _remove_article(self):
        """
        响应“删除文章”按钮，删除当前选中的一篇或多篇文章。
        """
        selected_items = self.article_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "操作失败", "请先在列表中选择要删除的文章。")
            return

        rows_to_delete = sorted([self.article_list_widget.row(item) for item in selected_items], reverse=True)
        
        # 弹出确认对话框
        confirm_message = (f"确定要删除文章 \"{self.articles[rows_to_delete[0]]['title']}\" 吗？" 
                           if len(rows_to_delete) == 1 
                           else f"确定要删除选中的 {len(rows_to_delete)} 篇文章吗？")
        reply = QMessageBox.question(self, '确认删除', f"{confirm_message}\n此操作不可撤销。",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 从后往前删除，避免索引因删除操作而错乱
        for row in rows_to_delete:
            del self.articles[row]

        # 重新计算并设置当前选中的文章索引
        if not self.articles:
            self.current_article_index = -1
        else:
            new_index = min(rows_to_delete[-1], len(self.articles) - 1)
            self.current_article_index = new_index

        self._refresh_article_list()

        if self.current_article_index == -1:
            self._init_articles() # 如果列表空了，则重置UI
        else:
            self._load_article_content(self.current_article_index)

    def _select_article(self, index):
        """
        当用户在左侧列表中点击切换文章时，由此槽函数处理。
        """
        # 使用 _is_switching_articles 标志防止重入，避免在程序性地切换时触发不必要的保存操作
        if self._is_switching_articles or index == self.current_article_index:
            return

        self._is_switching_articles = True
        try:
            # 核心逻辑：先将在编辑器中的修改保存到即将离开的文章数据中
            if self.current_article_index != -1:
                self._update_current_article_content(refresh_list=False)
            
            # 然后更新索引，并加载新选中文章的内容
            self.current_article_index = index
            self._load_article_content(index)
        finally:
            self._is_switching_articles = False

    def _load_article_content(self, index):
        """
        加载指定索引的文章内容到编辑器和预览区。
        """
        if 0 <= index < len(self.articles):
            # 暂时阻塞信号，防止 setPlainText 触发 textChanged 信号，导致循环更新
            self.markdown_editor.blockSignals(True)
            self.markdown_editor.setPlainText(self.articles[index]['content'])
            self.markdown_editor.blockSignals(False)
            
            self._update_preview()
            self._update_theme_menu_selection()

    def _update_current_article_content(self, refresh_list=True):
        """
        将编辑器中的当前文本内容，同步保存回 `self.articles` 列表中的对应项。
        """
        if 0 <= self.current_article_index < len(self.articles):
            self.articles[self.current_article_index]['content'] = self.markdown_editor.toPlainText()
            self._update_preview()
            # 只有在非文章切换时才刷新列表标题，避免不必要的UI重绘
            if refresh_list and not self._is_switching_articles:
                self._refresh_article_list()
            
    def _update_preview(self):
        """
        根据当前文章的内容和设置，重新渲染并更新右侧的HTML预览区。
        """
        if not (0 <= self.current_article_index < len(self.articles)):
            self.html_preview.set_html_content("")
            return

        current_article = self.articles[self.current_article_index]
        markdown_content = current_article['content']
        theme_name = current_article.get('theme', 'default')
        
        self.renderer.set_theme(theme_name)

        # 如果启用了模板，则将页眉和页脚内容拼接到文章内容前后
        if self.use_template:
            header, footer = self.template_manager.get_templates()
            full_markdown_content = f"{header}\n\n{markdown_content}\n\n{footer}"
        else:
            full_markdown_content = markdown_content
            
        html_content = self.renderer.render(full_markdown_content, mode=self.current_mode)
        self.html_preview.set_html_content(html_content)

    def _clear_all_articles(self):
        """
        响应“清空所有”菜单项，清空当前会话中的所有文章。
        """
        if not self.articles:
            return
        reply = QMessageBox.question(self, '确认操作', "此操作将清空所有已编辑的文章，确定要继续吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.log.info("用户选择清空所有文章。")
            self._init_articles() # 调用初始化方法重置所有状态

    def _open_document(self):
        """
        响应“打开”菜单项，允许用户打开一个或多个Markdown文件。
        """
        # 弹出文件选择对话框，允许多选
        file_paths, _ = QFileDialog.getOpenFileNames(self, "打开Markdown文件", "", "Markdown Files (*.md);;All Files (*)")
        
        if not file_paths:
            return

        opened_count = 0
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 将打开的文件作为一篇新文章添加到列表中
                title = self.parser.parse_markdown(content).get('title', os.path.basename(file_path))
                new_article = {
                    'title': title,
                    'content': content,
                    'theme': 'default',
                    'file_path': file_path  # 记录文件原始路径
                }
                self.articles.append(new_article)
                self.log.info(f"已打开文件并添加为新文章: {file_path}")
                opened_count += 1
            except Exception as e:
                self.log.error(f"打开文件 {file_path} 失败: {e}", exc_info=True)
                QMessageBox.warning(self, "打开失败", f"打开文件 {os.path.basename(file_path)} 失败: {e}")
        
        if opened_count > 0:
            # 自动切换到最后一个被导入的文章
            self.current_article_index = len(self.articles) - 1
            self._refresh_article_list()
            self._load_article_content(self.current_article_index)
            self.setWindowTitle(f"微信公众号Markdown渲染发布系统 - {os.path.basename(file_paths[-1])}")

    def _save_document(self):
        """
        响应“保存”菜单项，保存当前选中的文章。
        """
        if not (0 <= self.current_article_index < len(self.articles)):
            QMessageBox.warning(self, "保存失败", "没有可保存的文章。")
            return

        article = self.articles[self.current_article_index]
        filepath = article.get('file_path') # 获取文章关联的文件路径
        title = article['title']

        # 如果文章没有关联路径（是新建的），则弹出“另存为”对话框
        if not filepath:
            suggested_filename = self.storage_manager._generate_filename(title, ".md")
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"保存文章: {title}", suggested_filename, "Markdown Files (*.md);;All Files (*)"
            )
            if not filepath:
                self.log.info(f"用户取消了文章 '{title}' 的保存操作。")
                return

        self._save_single_article_to_path(self.current_article_index, filepath)

    def _save_all_documents(self):
        """
        响应“全部保存”菜单项，保存当前会话中的所有文章。
        """
        if not self.articles:
            QMessageBox.warning(self, "保存失败", "没有可保存的文章。")
            return

        self.log.info("开始执行“全部保存”操作。")
        
        # 找出所有新创建的（还没有文件路径的）文章
        new_articles_indices = [i for i, article in enumerate(self.articles) if not article.get('file_path')]
        
        save_directory = None
        if new_articles_indices:
            # 如果有新文章，则只弹窗一次，让用户选择一个统一的保存目录
            save_directory = QFileDialog.getExistingDirectory(self, "为新文章选择保存文件夹", os.getcwd())
            if not save_directory:
                self.log.info("用户未选择文件夹，取消“全部保存”操作。")
                QMessageBox.information(self, "操作取消", "未选择文件夹，全部保存操作已取消。")
                return

        saved_count = 0
        for i, article in enumerate(self.articles):
            filepath = article.get('file_path')
            
            # 如果是新文章，则在用户选择的目录中为其生成一个文件名
            if not filepath and save_directory:
                filename = self.storage_manager._generate_filename(article['title'], ".md")
                filepath = os.path.join(save_directory, filename)
            
            if filepath and self._save_single_article_to_path(i, filepath):
                saved_count += 1
        
        QMessageBox.information(self, "全部保存完成", f"成功保存 {saved_count} / {len(self.articles)} 篇文章。")
        self.log.info(f"“全部保存”操作完成。成功保存 {saved_count}/{len(self.articles)} 篇文章。")

    def _save_single_article_to_path(self, index, filepath):
        """
        将指定索引的文章内容保存到指定的文件路径。这是一个内部核心方法。
        
        :param index: 要保存的文章在 `self.articles` 列表中的索引。
        :param filepath: 目标文件路径。
        :return: 布尔值，表示保存是否成功。
        """
        if not (0 <= index < len(self.articles)):
            return False

        article = self.articles[index]
        title = article['title']
        
        # 如果要保存的是当前正在编辑的文章，需确保获取的是编辑器中的最新内容
        if index == self.current_article_index:
            markdown_content = self.markdown_editor.toPlainText()
            article['content'] = markdown_content
        else:
            markdown_content = article['content']

        # 不保存空内容
        if not markdown_content.strip():
            self.log.warning(f"文章 '{title}' 内容为空，跳过保存。")
            return True

        try:
            self.storage_manager.save_markdown_file(filepath, markdown_content)
            self.log.info(f"文章 '{title}' 已保存到: {filepath}")
            
            # 关键：保存成功后，更新文章数据结构中的文件路径，这样下次保存就不再需要“另存为”
            article['file_path'] = filepath
            
            # 如果保存的是当前文章，则更新窗口标题以显示文件名
            if index == self.current_article_index:
                 self.setWindowTitle(f"微信公众号Markdown渲染发布系统 - {os.path.basename(filepath)}")
            return True
        except Exception as e:
            self.log.error(f"保存文章 '{title}' 到 {filepath} 时失败: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存文章 \"{title}\" 到 \"{filepath}\" 失败: {e}")
            return False


    def _publish_to_wechat(self):
        """
        响应“发布到微信公众号”菜单项，启动发布流程。
        """
        self._update_current_article_content() # 确保当前编辑的内容已保存

        if not self.articles:
            QMessageBox.warning(self, "操作失败", "没有可发布的文章。")
            return
            
        if len(self.articles) > 8:
            QMessageBox.warning(self, "文章数量超限", "微信多图文消息最多支持8篇文章。")
            return

        # 步骤 1: 解析所有文章的元数据，为发布对话框准备数据
        self.log.info("正在解析所有文章以准备发布...")
        all_articles_data = []
        for article in self.articles:
            parsed_data = self.parser.parse_markdown(article['content'])
            parsed_data['markdown_content'] = article['content'] # 保留原始markdown内容
            parsed_data['theme'] = article.get('theme', 'default')
            if not parsed_data.get('author'):
                parsed_data['author'] = self.wechat_api.default_author
            all_articles_data.append(parsed_data)
        
        # 步骤 2: 弹出发布对话框，让用户最后确认和编辑元数据
        dialog = PublishDialog(all_articles_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self.log.info("发布对话框已确认。")
            final_articles_data = dialog.get_data()
            # 步骤 3: 如果用户确认，则启动后台发布任务
            self._execute_multi_article_publishing(final_articles_data)
        else:
            self.log.info("发布对话框已取消。")

    def _execute_multi_article_publishing(self, all_articles_data):
        """
        通过启动一个后台线程（PublishWorker）来执行耗时的多图文发布流程。
        """
        self.status_dialog = StatusDialog(title="发布到微信", parent=self)
        self.status_dialog.show()
        QApplication.processEvents()

        # 创建线程和Worker
        self.publish_thread = QThread()
        self.publish_worker = PublishWorker(
            all_articles_data,
            self.use_template,
            self.current_mode
        )
        self.publish_worker.moveToThread(self.publish_thread)

        # 连接Worker的信号到主线程的槽函数
        self.publish_worker.progress.connect(self._on_publish_progress)
        self.publish_worker.finished.connect(self._on_publish_finished)
        self.publish_thread.started.connect(self.publish_worker.run)
        
        # 启动线程
        self.publish_thread.start()
        self.log.info("发布文章的后台线程已启动。")

    # --- 后台任务回调槽函数 ---

    def _on_publish_progress(self, message):
        """
        槽函数：当PublishWorker发送进度更新时，更新状态对话框。
        """
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=False)

    def _on_publish_finished(self, success, message):
        """
        槽函数：当PublishWorker完成任务时，更新状态对话框并清理资源。
        """
        QApplication.beep() # 播放提示音
        if self.status_dialog:
            self.status_dialog.update_status(message, is_finished=True)
        
        # 安全地退出并清理线程和worker对象
        if self.publish_thread:
            self.publish_thread.quit()
            self.publish_thread.wait()
        self.log.info("发布后台线程已清理。")

    def _on_crawl_progress(self, message):
        """
        槽函数：当CrawlWorker发送进度更新时，更新UI。
        """
        if self.crawling_article_index != -1:
            article = self.articles[self.crawling_article_index]
            article['title'] = f"抓取中... {message[:10]}..."
            
            url = self.crawl_worker.url if self.crawl_worker else ""
            content = f"# 抓取中...\n\n从 {url}\n\n---\n\n{message}"
            article['content'] = content

            self._refresh_article_list()
            if self.current_article_index == self.crawling_article_index:
                self.markdown_editor.blockSignals(True)
                self.markdown_editor.setPlainText(content)
                self.markdown_editor.blockSignals(False)
            
            QApplication.processEvents()

    def _on_rewrite_finished(self, success, result):
        """
        槽函数：当RewriteWorker完成任务时，处理结果。
        """
        QApplication.beep()
        if success:
            self.markdown_editor.setPlainText(result)
            self._update_current_article_content()
            final_message = "文章改写成功！"
            self.log.info("AI改写成功。")
        else:
            final_message = f"改写失败: {result}"
            self.log.error(f"AI改写失败: {result}")
        
        if self.status_dialog:
            self.status_dialog.update_status(final_message, is_finished=True)

        # 清理资源
        if self.rewrite_thread:
            self.rewrite_thread.quit()
            self.rewrite_thread.wait()
        self.is_rewriting = False
        self.log.info("AI改写后台线程已清理。")

    def _on_crawl_finished(self, success, result):
        """
        槽函数：当CrawlWorker完成任务时，处理结果并启动下一个队列任务。
        """
        QApplication.beep()
        
        if self.crawling_article_index == -1:
            self.log.error("抓取完成，但没有找到对应的文章索引。")
            return

        article = self.articles[self.crawling_article_index]
        url = self.crawl_worker.url if self.crawl_worker else "未知URL"

        if success:
            # 成功时，result 是一个包含 'title' 和 'content' 的 article_data 字典
            article['title'] = result.get('title', '无标题')
            article['content'] = result.get('content', '')
            self.log.info(f"成功抓取和处理了URL: {url}")
        else:
            # 失败时，result 是一个错误信息字符串
            error_message = result
            title = "抓取失败"
            final_content = f"# {title}\n\n从 {url} 抓取时发生错误。\n\n**错误详情:**\n```\n{error_message}\n```\n"
            article['title'] = title
            article['content'] = final_content
            self.log.error(f"抓取URL失败: {url}, 错误: {error_message}")

        # 更新UI
        self._refresh_article_list()
        if self.current_article_index == self.crawling_article_index:
            self._load_article_content(self.crawling_article_index)

        # 清理当前worker
        if self.crawl_thread:
            self.crawl_thread.quit()
            self.crawl_thread.wait()
        self.crawl_worker = None
        self.crawl_thread = None
        self.crawling_article_index = -1
        self.log.info("抓取Worker已清理。")

        # 尝试处理队列中的下一个任务
        self._process_crawl_queue()

    # --- 辅助方法和槽函数 ---

    # --- 辅助方法和槽函数 ---

    def _show_article_list_context_menu(self, position):
        """
        响应文章列表的右键点击，显示上下文菜单（上移/下移/删除）。
        """
        item = self.article_list_widget.itemAt(position)
        if not item:
            return

        row = self.article_list_widget.row(item)
        menu = QMenu()
        move_up_action = QAction("向上移动", self)
        move_down_action = QAction("向下移动", self)
        delete_action = QAction("删除", self)

        # 根据项的位置决定是否禁用“上移”或“下移”
        move_up_action.setEnabled(row > 0)
        move_down_action.setEnabled(row < self.article_list_widget.count() - 1)

        move_up_action.triggered.connect(lambda: self._move_article_up(row))
        move_down_action.triggered.connect(lambda: self._move_article_down(row))
        delete_action.triggered.connect(self._remove_article)

        menu.addAction(move_up_action)
        menu.addAction(move_down_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.exec_(self.article_list_widget.mapToGlobal(position))

    def _move_article_up(self, row):
        """
        将指定索引的文章在列表中向上移动一位。
        """
        if row > 0:
            self.articles.insert(row - 1, self.articles.pop(row))
            self.current_article_index = row - 1
            self._refresh_article_list()

    def _move_article_down(self, row):
        """
        将指定索引的文章在列表中向下移动一位。
        """
        if row < len(self.articles) - 1:
            self.articles.insert(row + 1, self.articles.pop(row))
            self.current_article_index = row + 1
            self._refresh_article_list()

    def _show_about_dialog(self):
        """
        显示“关于”对话框。
        """
        self.log.info("显示“关于”对话框。")
        QMessageBox.about(self, "关于", "微信公众号Markdown渲染发布系统 v1.0\n\n一个简化微信公众号文章发布的桌面工具。")

    def _open_template_editor(self):
        """
        打开模板编辑器对话框。
        """
        dialog = TemplateEditorDialog(self)
        dialog.exec_()
        # 对话框关闭后，如果“使用模板”是激活的，则刷新预览以反映可能的变化
        if self.use_template:
            self._update_preview()

    def _toggle_template_usage(self, checked):
        """
        切换是否在渲染时使用页眉/页脚模板。
        """
        self.use_template = checked
        self.log.info(f"模板使用状态切换为: {self.use_template}")
        self._update_preview()

    def _change_theme(self, theme_name):
        """
        切换当前文章的渲染主题。
        """
        if 0 <= self.current_article_index < len(self.articles):
            current_article = self.articles[self.current_article_index]
            if current_article.get('theme') != theme_name:
                current_article['theme'] = theme_name
                self._update_preview()
                self.log.info(f"文章 '{current_article['title']}' 的主题已切换为: {theme_name}")

    def _update_theme_menu_selection(self):
        """
        根据当前文章的主题，自动更新顶部“主题”菜单的选中状态。
        """
        if not (0 <= self.current_article_index < len(self.articles)):
            return

        theme_name = self.articles[self.current_article_index].get('theme', 'default')
        for action in self.theme_group.actions():
            # 从Action的文本反向推断出主题名称
            action_theme_name = action.text().replace(" ", "_").lower()
            if action_theme_name == theme_name:
                action.setChecked(True)
                break

    def _open_settings_dialog(self):
        """
        打开设置对话框。
        """
        dialog = SettingsDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            # 如果用户保存了设置，则重新实例化API客户端以加载新配置
            self.wechat_api.reload_config()
            # LLMProcessor也需要重新加载
            # (这个逻辑可以在未来重构，通过一个统一的配置服务来通知所有模块更新)
            self.log.info("设置已保存，相关服务配置已重新加载。")

    # --- 编辑器与预览区同步滚动 ---

    def _on_editor_scrolled(self, value):
        """
        槽函数：当编辑器滚动时，按比例同步滚动预览区。
        """
        if self._is_syncing_scroll: return
        
        editor_scrollbar = self.markdown_editor.verticalScrollBar()
        if editor_scrollbar.maximum() == 0: return # 避免在内容很少时除以零
            
        scroll_percentage = value / editor_scrollbar.maximum()
        
        # 通过执行JavaScript来滚动Web视图
        js_code = f"window.scrollTo(0, document.body.scrollHeight * {scroll_percentage});"
        
        self._is_syncing_scroll = True
        self.html_preview.page().runJavaScript(js_code, lambda: setattr(self, '_is_syncing_scroll', False))

    @Slot(float)
    def on_preview_scrolled(self, percentage):
        """
        槽函数：当预览区滚动时（由注入的JS代码通过QWebChannel调用），按比例同步滚动编辑器。
        """
        if self._is_syncing_scroll: return
            
        editor_scrollbar = self.markdown_editor.verticalScrollBar()
        
        self._is_syncing_scroll = True
        editor_scrollbar.setValue(int(editor_scrollbar.maximum() * percentage))
        # 使用定时器在短暂延迟后重置标志，以避免两个方向的滚动事件互相锁定
        QTimer.singleShot(50, lambda: setattr(self, '_is_syncing_scroll', False))

    # --- 亮/暗模式切换 ---

    def _toggle_mode(self):
        """
        切换亮色/暗黑模式。
        """
        self.current_mode = "dark" if self.current_mode == "light" else "light"
        self._apply_mode_styles()
        self._update_preview()
        self._update_mode_toggle_button()
        self.log.info(f"显示模式已切换为: {self.current_mode}")

    def _update_mode_toggle_button(self):
        """
        更新模式切换按钮的文本和样式。
        """
        if self.current_mode == "dark":
            self.mode_toggle_btn.setText("暗黑")
            self.mode_toggle_btn.setStyleSheet("QPushButton { background-color: #555; color: white; }")
        else:
            self.mode_toggle_btn.setText("明亮")
            self.mode_toggle_btn.setStyleSheet("QPushButton { background-color: #eee; color: black; }")

    def _apply_mode_styles(self):
        """
        应用当前模式的QSS样式到主窗口和相关控件。
        """
        is_dark = self.current_mode == "dark"
        bg_color = "#2e2e2e" if is_dark else "#f0f0f0"
        text_color = "#f0f0f0" if is_dark else "#333"
        base_bg = "#3e3e3e" if is_dark else "white"
        selected_bg = "#555" if is_dark else "#e0e0e0"
        border_color = "#555" if is_dark else "#ccc"

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {bg_color}; color: {text_color}; }}
            QSplitter::handle {{ background-color: {border_color}; }}
            QListWidget {{ background-color: {base_bg}; color: {text_color}; border: 1px solid {border_color}; }}
            QListWidget::item:selected {{ background-color: {selected_bg}; }}
            QPushButton {{ background-color: #444; border: 1px solid #666; padding: 5px; }}
            QPushButton:hover {{ background-color: #555; }}
            QLabel {{ color: {text_color}; }}
            QMenuBar, QMenu {{ background-color: {bg_color}; color: {text_color}; }}
            QMenuBar::item:selected, QMenu::item:selected {{ background-color: {selected_bg}; }}
        """)
        self.markdown_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {base_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
        """)


class CustomWebEngineView(QWebEngineView):
    """
    一个自定义的 QWebEngineView，增加了右键菜单和与Python交互的能力。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.html_content = ""
        # 设置页面背景为透明，以便让父级(body)的背景色显示出来
        self.page().setBackgroundColor(QColor("transparent"))
        
        # 设置 QWebChannel，这是实现JS与Python双向通信的关键
        self.channel = QWebChannel(self.page())
        self.page().setWebChannel(self.channel)
        # 将父窗口(MainWindow)注册到channel中，并命名为'scroll_handler'，这样JS就可以通过这个名字调用它
        self.channel.registerObject("scroll_handler", parent)

    def set_html_content(self, html):
        """
        设置并显示HTML内容。
        """
        self.html_content = html
        
        # 注入一个 <script> 标签到HTML中，用于加载 qwebchannel.js 并设置滚动事件监听器
        js_to_inject = """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    // 将Python中注册的'scroll_handler'对象暴露给JS的window对象
                    window.scroll_handler = channel.objects.scroll_handler;
                    
                    // 监听滚动事件
                    window.addEventListener('scroll', function() {
                        if (window.scroll_handler) {
                            const scrollableHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                            if (scrollableHeight > 0) {
                                let percentage = window.scrollY / scrollableHeight;
                                // 当滚动发生时，调用Python中的 on_preview_scrolled 方法，并传递滚动百分比
                                window.scroll_handler.on_preview_scrolled(percentage);
                            }
                        }
                    });
                });
            });
        </script>
        """
        full_html = js_to_inject + html
        # 加载最终的HTML。baseUrl是必需的，以确保相对路径（如图片）能被正确解析。
        self.setHtml(full_html, baseUrl=QUrl.fromLocalFile(os.path.abspath(".")))

    def contextMenuEvent(self, event):
        """
        重写右键上下文菜单事件。
        """
        menu = self.page().createStandardContextMenu()
        
        # 在标准菜单的顶部添加我们自己的操作
        menu.insertSeparator(menu.actions()[0])
        show_source_action = QAction("显示源代码", self)
        show_source_action.triggered.connect(self.show_source)
        menu.insertAction(menu.actions()[0], show_source_action)
        
        copy_html_action = QAction("复制渲染后的HTML", self)
        copy_html_action.triggered.connect(self.copy_html_content)
        menu.insertAction(menu.actions()[0], copy_html_action)

        menu.exec_(event.globalPos())

    def copy_html_content(self):
        """
        将当前渲染的HTML内容复制到系统剪贴板。
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(self.html_content)
        logging.getLogger("MdToWeChat").info("渲染后的HTML内容已复制到剪贴板。")

    def show_source(self):
        """
        弹出一个对话框来显示HTML源代码。
        """
        dialog = SourceDialog(self.html_content, self)
        dialog.exec_()
