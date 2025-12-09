import os, logging
import datetime
import shutil
import re

class StorageManager:
    """
    负责管理文件的存储和清理，包括用户手动保存的Markdown文件和系统自动生成的HTML存档。
    """
    def __init__(self, base_dir="data"):
        """
        初始化存储管理器。
        
        :param base_dir: 用于存放所有数据和存档的根目录。
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.log = logging.getLogger(__name__)

    def _get_daily_archive_dir(self):
        """
        获取或创建用于存放当日HTML存档的目录路径。
        目录结构为 `base_dir/YYYY-MM-DD/`。
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        daily_dir = os.path.join(self.base_dir, today_str)
        os.makedirs(daily_dir, exist_ok=True)
        return daily_dir

    def _generate_filename(self, title, extension):
        """
        根据文章标题和当前时间戳生成一个对文件系统安全的文件名。
        
        命名规则: `[清理后的标题前20个字符]_[HHMMSS].[extension]`
        
        :param title: 文章标题。
        :param extension: 文件扩展名（例如 ".md" 或 ".html"）。
        :return: 生成的文件名字符串。
        """
        # 移除Windows和Markdown文件名中的非法字符
        safe_title = re.sub(r'[\\/:*?"<>|#\[\]()`]', '', title)
        safe_title = safe_title.strip() or "untitled"
        # 截取前20个字符以避免文件名过长
        safe_title = safe_title[:20]
        
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        return f"{safe_title}_{timestamp}{extension}"

    def save_markdown_file(self, filepath, markdown_content):
        """
        将Markdown内容保存到用户指定的任意文件路径。
        此方法用于响应用户的“保存”或“另存为”操作。
        
        :param filepath: 完整的目标文件路径。
        :param markdown_content: 要保存的Markdown文本内容。
        :return: 保存成功后的文件路径。
        """
        try:
            # 确保目标文件的父目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            self.log.info(f"Markdown文件已成功保存到: {filepath}")
            return filepath
        except Exception as e:
            self.log.error(f"保存Markdown文件到 '{filepath}' 时失败: {e}", exc_info=True)
            raise

    def save_html_archive(self, title, html_content):
        """
        将渲染后的HTML内容作为存档，保存到当日的归档目录中。
        此方法用于系统内部备份，而非用户直接调用。
        
        :param title: 文章标题，用于生成文件名。
        :param html_content: 要保存的HTML文本内容。
        :return: 保存成功后的HTML文件路径。
        """
        try:
            daily_dir = self._get_daily_archive_dir()
            html_filename = self._generate_filename(title, ".html")
            html_filepath = os.path.join(daily_dir, html_filename)
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.log.info(f"HTML存档已成功保存到: {html_filepath}")
            return html_filepath
        except Exception as e:
            self.log.error(f"保存HTML存档时失败: {e}", exc_info=True)
            raise

    def clean_old_archives(self, days_to_keep=30):
        """
        清理指定天数之前的旧HTML归档文件夹。
        
        :param days_to_keep: 要保留的最近天数。
        """
        if days_to_keep <= 0:
            self.log.info("清理周期设置为0天或更少，将不会清理任何旧存档。")
            return
            
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days_to_keep)
        self.log.info(f"开始清理 {cutoff_date} 之前的旧存档...")
        
        deleted_count = 0
        for entry in os.listdir(self.base_dir):
            full_path = os.path.join(self.base_dir, entry)
            if os.path.isdir(full_path):
                try:
                    # 检查目录名是否是 "YYYY-MM-DD" 格式
                    dir_date = datetime.datetime.strptime(entry, "%Y-%m-%d").date()
                    if dir_date < cutoff_date:
                        shutil.rmtree(full_path)
                        self.log.info(f"已删除旧的存档目录: {full_path}")
                        deleted_count += 1
                except (ValueError, OSError) as e:
                    # 忽略不符合日期格式的目录或删除时发生错误
                    self.log.debug(f"跳过或删除失败: {full_path}。原因: {e}")
                    pass
        
        self.log.info(f"旧存档清理完成。共删除了 {deleted_count} 个目录。")
