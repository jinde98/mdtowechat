import os
import datetime
import shutil
import re

class StorageManager:
    """负责管理文件的存储和清理，包括Markdown文件、HTML存档和临时图片。"""
    def __init__(self, base_dir="data"): # 初始化存储管理器，创建基础目录。
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_daily_dir(self):
        """
        获取当日的存储目录路径，如果不存在则创建。
        格式为 `base_dir/YYYY-MM-DD/`
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        daily_dir = os.path.join(self.base_dir, today_str)
        os.makedirs(daily_dir, exist_ok=True)
        return daily_dir

    def _generate_filename(self, title, extension=".md"):
        """
        根据标题和当前时间戳生成文件名。
        文件名规则：`标题前20字符_时间戳.extension`
        对标题进行清理，移除特殊字符
        """
        # 移除Markdown特殊字符和文件名非法字符
        safe_title = re.sub(r'[\\/:*?"<>|#\[\]()`]', '', title)
        safe_title = safe_title.strip()
        safe_title = safe_title[:20].strip() if safe_title else "untitled"
        
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        return f"{safe_title}_{timestamp}{extension}"

    def save_markdown_file(self, filepath, markdown_content):
        """
        保存Markdown内容到指定文件路径。
        :param filepath: 完整的Markdown文件路径
        :param markdown_content: Markdown字符串内容
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return filepath

    def save_html_archive(self, title, html_content):
        """
        将HTML内容保存到当日的存档目录。
        文件名根据标题生成。
        :param title: 文章标题
        :param html_content: HTML字符串内容
        :return: 保存的HTML文件路径
        """
        daily_dir = self._get_daily_dir()
        html_filename = self._generate_filename(title, ".html")
        html_filepath = os.path.join(daily_dir, html_filename)
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return html_filepath

    def clean_old_articles(self, days_to_keep=30):
        """
        清理指定天数之前的旧文章文件夹。
        """
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days_to_keep)
        for entry in os.listdir(self.base_dir):
            full_path = os.path.join(self.base_dir, entry)
            if os.path.isdir(full_path):
                try:
                    dir_date = datetime.datetime.strptime(entry, "%Y-%m-%d").date()
                    if dir_date < cutoff_date:
                        print(f"Deleting old directory: {full_path}")
                        shutil.rmtree(full_path)
                except ValueError:
                    # 忽略不符合日期格式的目录。
                    pass

# 移除旧的 save_article 方法，或将其重命名为 save_full_article_archive
# 如果需要保留其功能，可以这样定义：
# def save_full_article_archive(self, title, markdown_content, html_content, local_image_paths=None):
#     """
#     旧的保存方法，保存原始Markdown内容、渲染后的HTML内容以及关联的本地图片。
#     """
#     daily_dir = self._get_daily_dir()
#     md_filename = self._generate_filename(title, ".md")
#     html_filename = self._generate_filename(title, ".html")
#     md_filepath = os.path.join(daily_dir, md_filename)
#     html_filepath = os.path.join(daily_dir, html_filename)
#     with open(md_filepath, "w", encoding="utf-8") as f:
#         f.write(markdown_content)
#     with open(html_filepath, "w", encoding="utf-8") as f:
#         f.write(html_content)
#     # 复制本地图片逻辑...
#     return md_filepath, html_filepath, []


if __name__ == '__main__':
    # 示例用法
    storage_manager = StorageManager(base_dir="test_data")

    # 测试 save_markdown_file
    md_test_path = "test_data/my_document.md"
    storage_manager.save_markdown_file(md_test_path, "# Hello World\n\nThis is a test markdown.")
    print(f"Markdown saved to: {md_test_path}")

    # 测试 save_html_archive
    html_test_path = storage_manager.save_html_archive("测试HTML文章", "<h1>Hello HTML</h1><p>This is test HTML.</p>")
    print(f"HTML archive saved to: {html_test_path}")

    # 清理旧文章示例
    # storage_manager.clean_old_articles(days_to_keep=0)
