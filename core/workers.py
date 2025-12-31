from PySide6.QtCore import QObject, Signal
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
    一个在后台线程中执行网页抓取和AI处理的Worker。
    继承自 QObject 以便能够使用信号和槽机制。
    """
    # 定义信号：
    # finished 信号在任务完成时发射，携带一个布尔值表示成功与否，以及一个包含结果或错误信息的对象。
    finished = Signal(bool, object) 
    # progress 信号在任务执行过程中发射，用于向UI线程报告进度更新。
    progress = Signal(str)

    def __init__(self, url, system_prompt):
        super().__init__()
        self.url = url
        self.system_prompt = system_prompt
        self.parser = ContentParser()

    def run(self):
        """
        这是Worker的核心执行方法。它将在一个单独的线程中被调用。
        """
        try:
            # 步骤 1: 抓取网页内容
            self.progress.emit("正在从网页抓取内容...")
            crawler = Crawler()
            markdown_content, error = crawler.fetch(self.url)
            if error:
                raise Exception(f"抓取失败: {error}")

            # 步骤 2: 调用大语言模型（LLM）处理内容
            self.progress.emit("抓取成功，正在由AI处理内容...")
            llm_processor = LLMProcessor()
            processed_content, error = llm_processor.process_content(markdown_content, self.system_prompt)
            if error:
                raise Exception(f"AI处理失败: {error}")

            # 步骤 3: 解析处理后的内容以获取标题，并准备最终的文章数据
            title = self.parser.parse_markdown(processed_content).get('title') or os.path.basename(self.url)
            article_data = {
                'title': title,
                'content': processed_content,
                'theme': 'default'  # 使用默认主题
            }
            
            self.progress.emit("文章生成成功！")
            # 发射 finished 信号，通知UI线程任务成功完成
            self.finished.emit(True, article_data)

        except Exception as e:
            # 如果任何步骤出错，则捕获异常
            error_msg = f"操作失败: {e}"
            self.progress.emit(error_msg)
            # 发射 finished 信号，通知UI线程任务失败
            self.finished.emit(False, error_msg)


class PublishWorker(QObject):
    """
    一个在后台线程中执行完整发布流程的Worker。
    """
    # success: 成功或失败, message: 最终显示给用户的消息
    finished = Signal(bool, str) 
    progress = Signal(str)

    def __init__(self, all_articles_data, use_template, current_mode):
        super().__init__()
        self.all_articles_data = all_articles_data
        self.use_template = use_template
        self.current_mode = current_mode
        # 关键：所有需要进行I/O或网络操作的类都应该在Worker自己的线程中创建，
        # 而不是从主线程传递过来，以避免跨线程问题。
        self.wechat_api = WeChatAPI()
        self.renderer = MarkdownRenderer()
        self.storage_manager = StorageManager()
        self.template_manager = TemplateManager()

    def run(self):
        """
        执行完整的发布流程，包括渲染、图片上传和创建草稿。
        """
        try:
            final_articles_for_wechat_api = []
            total_articles = len(self.all_articles_data)

            # 遍历待发布的每一篇文章
            for i, article_data in enumerate(self.all_articles_data):
                title = article_data.get('title', '无标题')
                self.progress.emit(f"({i+1}/{total_articles}) 正在处理文章: \"{title}\"")

                # 步骤 1: 应用页眉和页脚模板
                if self.use_template:
                    header, footer = self.template_manager.get_templates()
                    full_markdown_content = f"{header}\n\n{article_data['markdown_content']}\n\n{footer}"
                else:
                    full_markdown_content = article_data['markdown_content']

                # 步骤 2: 渲染Markdown为HTML
                self.renderer.set_theme(article_data.get('theme', 'default'))
                html_content = self.renderer.render(full_markdown_content, mode=self.current_mode)
                
                # 步骤 3: 生成文章摘要
                digest = article_data.get('digest', '')
                if not digest:  # 如果用户没有在发布对话框中指定，则自动从正文第一段生成
                    soup = BeautifulSoup(html_content, 'html.parser')
                    first_p = soup.find('p')
                    digest = first_p.get_text(strip=True) if first_p else ''
                digest = digest[:100]  # 截取最多100个字符

                # 步骤 4: 上传封面图，获取 thumb_media_id
                self.progress.emit(f"({i+1}/{total_articles}) 正在上传封面图...")
                cover_image_path = article_data.get('cover_image', '')
                thumb_media_id, _ = self.wechat_api.get_thumb_media_id_and_url(cover_image_path)
                if not thumb_media_id:
                    raise Exception(f"文章 \"{title}\" 的封面图上传失败或未指定默认封面。")

                # 步骤 5: 上传正文中的所有图片，并替换URL
                self.progress.emit(f"({i+1}/{total_articles}) 正在上传内容中的图片...")
                final_html_content = self.wechat_api.process_content_images(html_content)
                
                # 步骤 6: 组装成符合微信API格式的单篇文章数据
                api_article_data = {
                    'title': title[:64],  # 标题限制64字符
                    'author': article_data.get('author', self.wechat_api.default_author),
                    'digest': digest,
                    'content': final_html_content,
                    'thumb_media_id': thumb_media_id,
                    'content_source_url': article_data.get('content_source_url', ''),
                    'need_open_comment' : 1, # 默认打开评论
                    'show_cover_pic': 1     # 在正文中显示封面图
                }
                final_articles_for_wechat_api.append(api_article_data)

            # 步骤 7: 所有文章处理完毕后，调用API创建草稿
            self.progress.emit("所有文章处理完毕，正在创建微信草稿...")
            media_id, error_message = self.wechat_api.create_draft(articles=final_articles_for_wechat_api)
            
            if media_id:
                # 步骤 8: 成功后，进行本地HTML存档
                success_msg = f"包含 {total_articles} 篇文章的草稿已成功创建！\nMedia ID: {media_id}"
                self.progress.emit("正在本地存档HTML内容...")
                for article in final_articles_for_wechat_api:
                    self.storage_manager.save_html_archive(article['title'], article['content'])
                self.finished.emit(True, success_msg + "\n\n所有文章的HTML内容均已在本地存档。")
            else:
                raise Exception(f"创建草稿失败: {error_message}")

        except Exception as e:
            self.finished.emit(False, f"发布失败: {e}")


class RewriteWorker(QObject):
    """
    一个在后台线程中执行AI改写任务的Worker。
    """
    # success: 成功或失败, str: 改写后的内容或错误信息
    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, original_content, custom_prompt, system_prompt):
        super().__init__()
        self.original_content = original_content
        self.custom_prompt = custom_prompt
        self.system_prompt = system_prompt

    def run(self):
        """
        执行AI改写的核心逻辑。
        """
        try:
            self.progress.emit("正在准备AI改写任务, 请稍候...")
            
            # 结合system prompt和用户自定义prompt
            full_prompt = f"{self.system_prompt}\n\n用户的具体要求是：'{self.custom_prompt}'"

            llm_processor = LLMProcessor()
            processed_content, error = llm_processor.process_content(
                self.original_content, 
                full_prompt
            )
            
            if error:
                raise Exception(f"AI处理失败: {error}")

            self.progress.emit("改写成功！")
            self.finished.emit(True, processed_content)

        except Exception as e:
            error_msg = f"改写失败: {e}"
            self.progress.emit(error_msg)
            self.finished.emit(False, error_msg)


class ImageUploadWorker(QObject):
    """
    一个在后台线程中执行单个图片上传任务的Worker。
    """
    # success: 成功或失败, original_path: 原始路径, result: 上传后的URL或错误信息
    finished = Signal(bool, str, str)

    def __init__(self, image_path, wechat_api):
        super().__init__()
        self.image_path = image_path
        # 直接传递 wechat_api 实例，而不是在worker中创建
        self.wechat_api = wechat_api

    def run(self):
        """
        执行图片上传的核心逻辑。
        """
        try:
            wechat_url, error_msg = self.wechat_api.upload_image_for_content(self.image_path)
            if error_msg:
                raise Exception(error_msg)
            self.finished.emit(True, self.image_path, wechat_url)
        except Exception as e:
            self.finished.emit(False, self.image_path, str(e))
