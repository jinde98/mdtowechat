from PyQt5.QtCore import QObject, pyqtSignal
from bs4 import BeautifulSoup
from core.crawler import Crawler
from core.llm import LLMProcessor
from core.parser import ContentParser
from core.renderer import MarkdownRenderer
from core.wechat_api import WeChatAPI
from core.storage import StorageManager
from core.template_manager import TemplateManager
import os

class CrawlWorker(QObject):
    """
    一个在后台线程中执行网页抓取和AI处理任务的Worker。
    """
    # 信号定义
    # finished(bool: success, dict: article_data or error_message)
    finished = pyqtSignal(bool, object) 
    # progress(str: message)
    progress = pyqtSignal(str)

    def __init__(self, url, system_prompt):
        super().__init__()
        self.url = url
        self.system_prompt = system_prompt
        self.parser = ContentParser()

    def run(self):
        """
        执行抓取和处理的核心逻辑。
        """
        try:
            # 1. 抓取内容
            self.progress.emit("正在从网页抓取内容...")
            crawler = Crawler()
            markdown_content, error = crawler.fetch(self.url)
            if error:
                raise Exception(f"抓取失败: {error}")

            # 2. 调用LLM处理
            self.progress.emit("正在由AI处理内容...")
            llm_processor = LLMProcessor()
            processed_content, error = llm_processor.process_content(markdown_content, self.system_prompt)
            if error:
                raise Exception(f"AI处理失败: {error}")

            # 3. 解析标题并创建文章数据
            title = self.parser.parse_markdown(processed_content).get('title') or os.path.basename(self.url)
            article_data = {
                'title': title,
                'content': processed_content,
                'theme': 'default'
            }
            
            self.progress.emit("文章生成成功！")
            self.finished.emit(True, article_data)

        except Exception as e:
            error_msg = f"操作失败: {e}"
            self.progress.emit(error_msg)
            self.finished.emit(False, error_msg)


class PublishWorker(QObject):
    """
    一个在后台线程中执行发布到微信任务的Worker。
    """
    finished = pyqtSignal(bool, str) # success, message
    progress = pyqtSignal(str)

    def __init__(self, all_articles_data, use_template, current_mode):
        super().__init__()
        self.all_articles_data = all_articles_data
        self.use_template = use_template
        self.current_mode = current_mode
        # 这些类不应跨线程共享，所以在worker线程中重新创建
        self.wechat_api = WeChatAPI()
        self.renderer = MarkdownRenderer()
        self.storage_manager = StorageManager()
        self.template_manager = TemplateManager()

    def run(self):
        try:
            final_articles_for_wechat_api = []
            total_articles = len(self.all_articles_data)

            for i, article_data in enumerate(self.all_articles_data):
                title = article_data.get('title', '无标题')
                self.progress.emit(f"({i+1}/{total_articles}) 正在处理文章: \"{title}\"")

                if self.use_template:
                    header, footer = self.template_manager.get_templates()
                    full_markdown_content = f"{header}\n\n{article_data['markdown_content']}\n\n{footer}"
                else:
                    full_markdown_content = article_data['markdown_content']

                self.renderer.set_theme(article_data.get('theme', 'default'))
                html_content = self.renderer.render(full_markdown_content, mode=self.current_mode)
                
                digest = article_data.get('digest', '')
                if not digest:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    first_p = soup.find('p')
                    digest = first_p.get_text() if first_p else ''
                digest = digest[:100]

                self.progress.emit(f"({i+1}/{total_articles}) 正在上传封面图...")
                cover_image_path = article_data.get('cover_image', '')
                thumb_media_id, _ = self.wechat_api.get_thumb_media_id_and_url(cover_image_path)
                
                if not thumb_media_id:
                    raise Exception(f"文章 \"{title}\" 获取封面图失败")

                self.progress.emit(f"({i+1}/{total_articles}) 正在上传内容中的图片...")
                final_html_content = self.wechat_api.process_content_images(html_content)
                
                api_article_data = {
                    'title': title[:64],
                    'author': article_data.get('author', self.wechat_api.default_author),
                    'digest': digest,
                    'content': final_html_content,
                    'thumb_media_id': thumb_media_id,
                    'content_source_url': article_data.get('content_source_url', ''),
                    'need_open_comment' : 1,
                    'show_cover_pic': 1
                }
                final_articles_for_wechat_api.append(api_article_data)

            self.progress.emit("所有文章处理完毕，正在创建草稿...")
            media_id, error_message = self.wechat_api.create_draft(articles=final_articles_for_wechat_api)
            
            if media_id:
                success_msg = f"包含 {total_articles} 篇文章的草稿已成功发布！\nMedia ID: {media_id}"
                self.progress.emit("正在本地存档HTML内容...")
                for i, article_data in enumerate(final_articles_for_wechat_api):
                    self.storage_manager.save_html_archive(article_data['title'], article_data['content'])
                self.finished.emit(True, success_msg + "\n\n所有文章的HTML内容均已在本地存档。")
            else:
                raise Exception(f"创建草稿失败: {error_message}")

        except Exception as e:
            self.finished.emit(False, f"发布失败: {e}")
