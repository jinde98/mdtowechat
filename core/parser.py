import re
import os

class ContentParser:
    """
    负责解析Markdown内容，提取文章元数据（如标题、作者、图片等）。
    """
    def __init__(self):
        pass

    def parse_markdown(self, markdown_content):
        """
        解析Markdown内容，提取标题、作者和本地图片路径。
        """
        title = self._extract_title(markdown_content)
        author = self._extract_author(markdown_content)
        all_image_urls = self._extract_all_image_urls(markdown_content)
        
        description = self._extract_description(markdown_content)
        cover_image = self._extract_cover_image(all_image_urls) # 封面图从所有图片中取第一个

        # 区分本地图片和微信图片，方便后续处理
        local_image_paths = [url for url in all_image_urls if not url.startswith('http')]
        wechat_image_urls = [url for url in all_image_urls if url.startswith('mmbiz.qpic.cn')]

        return {
            "title": title,
            "author": author,
            "description": description,
            "cover_image": cover_image, # 可能是本地路径或mmbiz URL
            "local_image_paths": local_image_paths, # 仅本地路径
            "wechat_image_urls": wechat_image_urls, # 仅mmbiz URL
            "all_image_urls": all_image_urls # 所有图片URL
        }

    def _extract_title(self, markdown_content):
        """
        从Markdown内容中提取标题。
        优先从 `#+ 标题` 提取，如果没有则返回None。
        """
        # 匹配一个或多个#号开头的标题
        match = re.search(r'^#+\s*(.+)', markdown_content, re.MULTILINE)
        if match:
            # 移除标题内容中可能存在的Markdown格式
            clean_title = self._remove_markdown_formatting(match.group(1))
            # clean_title = self._remove_emoji(clean_title) # 暂时注释掉，测试是否影响中文字符
            return clean_title.strip()
        return None

    def _extract_author(self, markdown_content):
        """
        从Markdown内容中提取作者。
        优先从 `> 作者` 提取，如果没有则返回None。
        """
        match = re.search(r'^>\s*作者\s*(.+)', markdown_content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_all_image_urls(self, markdown_content):
        """
        从Markdown内容中提取所有图片URL，包括本地路径和远程URL。
        匹配格式: `![alt text](path/to/image.jpg)` 或 `![alt text](http://example.com/image.png)`
        """
        matches = re.findall(r'!\[.*?\]\((.*?)\)', markdown_content)
        return [path.strip() for path in matches if path.strip()]

    def _extract_description(self, markdown_content, length=120):
        """
        从Markdown内容中提取第一段非空、非标题、非引用的文本作为描述。
        并移除所有Markdown格式。
        """
        lines = markdown_content.split('\n')
        for line in lines:
            line = line.strip()
            # 忽略标题、引用、代码块、水平线、列表项
            if line and not line.startswith(('#', '>', '```', '---', '|', '-', '*')):
                # 移除所有Markdown格式
                clean_line = self._remove_markdown_formatting(line)
                if len(clean_line) > 10: # 确保不是零碎的字符
                    return clean_line[:length].strip()
        return ""

    def _remove_markdown_formatting(self, text):
        """
        移除文本中的常见Markdown格式。
        """
        # 移除图片和链接的Markdown语法
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text) # 图片
        text = re.sub(r'\[.*?\]\(.*?\)', '', text) # 链接
        
        # 移除加粗、斜体、删除线、行内代码
        text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text) # **bold** or __bold__
        text = re.sub(r'(\*|_)(.*?)\1', r'\2', text) # *italic* or _italic_
        text = re.sub(r'~~(.*?)~~', r'\1', text) # ~~strike~~
        text = re.sub(r'`(.*?)`', r'\1', text) # `inline code`
        
        # 移除ATX标题的#号（虽然通常在提取前就处理了，这里作为二次保险）
        text = re.sub(r'^#+\s*', '', text) 
        
        # 移除引用块的>
        text = re.sub(r'^>\s*', '', text)
        
        # 移除列表符号 (-、*、+、数字.)
        text = re.sub(r'^[-\*\+]\s+', '', text) # 无序列表
        text = re.sub(r'^\d+\.\s+', '', text) # 有序列表
        
        return text.strip()

    def _extract_cover_image(self, image_urls):
        """
        从图片URL列表中提取封面图片（第一张）。
        """
        if image_urls and len(image_urls) > 0:
            return image_urls[0]
        return None

    def _remove_emoji(self, text):
        """
        从文本中移除Emoji字符。
        """
        if not text: # 如果文本为空，直接返回空字符串。
            return ""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 表情符号
            "\U0001F300-\U0001F5FF"  # 符号和象形文字
            "\U0001F680-\U0001F6FF"  # 交通和地图符号
            "\U0001F1E0-\U0001F1FF"  # 旗帜 (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

if __name__ == '__main__':
    # 示例用法
    markdown_test_content = """
# 我的文章标题

> 作者 张三

这是一个段落，包含一张本地图片：![本地图片1](assets/images/pic1.jpg)。
还有一张图片在其他文件夹：![本地图片2](../uploads/another.png)。

一些其他内容。

![网络图片](https://example.com/remote.jpg)

![本地图片3](./images/test.gif)
"""

    parser = ContentParser()
    parsed_data = parser.parse_markdown(markdown_test_content)

    print(f"标题: {parsed_data['title']}") # 打印提取到的标题
    print(f"作者: {parsed_data['author']}") # 打印提取到的作者
    print(f"描述: {parsed_data['description']}") # 打印提取到的描述
    print(f"封面图片: {parsed_data['cover_image']}") # 打印提取到的封面图片
    print(f"所有图片URL: {parsed_data['all_image_urls']}") # 打印所有图片URL
    print(f"本地图片路径: {parsed_data['local_image_paths']}") # 打印本地图片路径
    print(f"微信图片URL: {parsed_data['wechat_image_urls']}") # 打印微信图片URL

    markdown_no_metadata = """
## 另一个文章

这是一个没有明确标题和作者的文档。
![无元数据图片](local_img.jpg)
"""
    parsed_no_metadata = parser.parse_markdown(markdown_no_metadata)
    print(f"\n无元数据标题: {parsed_no_metadata['title']}") # 打印无元数据文章的标题
    print(f"无元数据作者: {parsed_no_metadata['author']}") # 打印无元数据文章的作者
    print(f"无元数据本地图片路径: {parsed_no_metadata['local_image_paths']}") # 打印无元数据文章的本地图片路径
    print(f"无元数据所有图片URL: {parsed_no_metadata['all_image_urls']}") # 打印无元数据文章的所有图片URL
