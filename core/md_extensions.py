from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
import re

class MetadataExtractor(Treeprocessor):
    """
    一个Markdown AST树处理器，用于提取文章的元数据。
    """
    def __init__(self, md):
        super().__init__(md)
        self.metadata = {
            'title': None,
            'author': None,
            'description': None,
            'cover_image': None,
            'all_image_urls': []
        }

    def run(self, root):
        # 在每次运行时重置元数据，以防止前一次运行的数据残留
        self.metadata = {
            'title': None, 'author': None, 'description': None,
            'cover_image': None, 'all_image_urls': []
        }
        
        # 提取所有图片
        self.metadata['all_image_urls'] = [img.get('src') for img in root.iter('img') if img.get('src')]
        if self.metadata['all_image_urls']:
            self.metadata['cover_image'] = self.metadata['all_image_urls'][0]

        # 遍历所有顶级元素来提取标题、作者和描述
        title_found = False
        for i, el in enumerate(list(root)):
            # 提取标题 (第一个任何级别的标题)
            if el.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and not title_found:
                self.metadata['title'] = ''.join(el.itertext()).strip()
                title_found = True
                # 注意：这里不移除标题元素，因为它仍然是内容的一部分。
                # 只在提取作者和摘要等非内容元数据时才考虑移除。

            # 提取作者 (第一个以 "作者" 开头的 blockquote)
            if el.tag == 'blockquote' and not self.metadata['author']:
                p_tags = el.findall('p')
                if p_tags:
                    text = ''.join(p_tags[0].itertext()).strip()
                    match = re.match(r'^(作者|author)[:：\s]*(.*)', text, re.IGNORECASE)
                    if match:
                        self.metadata['author'] = match.group(2).strip()
                        # 作者信息是元数据，不应在渲染中显示，所以这里可以考虑移除
                        # 但为了保持一致性，暂时不移除，交由渲染器决定
                        # root.remove(el) 
                        continue

            # 提取描述 (第一个非空段落)
            if el.tag == 'p' and not self.metadata['description']:
                text = ''.join(el.itertext()).strip()
                # 确保段落有足够的内容
                if len(text) > 10:
                    self.metadata['description'] = text[:120].strip()
                    # 找到后即可停止，因为我们只需要第一段
                    break
        
        # 将收集到的元数据附加到markdown实例上
        self.md.extracted_metadata = self.metadata

class MetadataExtension(Extension):
    """
    将MetadataExtractor注册为Markdown扩展的工厂类。
    """
    def extendMarkdown(self, md):
        # 优先级 > 官方的 'inline' 处理器，以确保在它之前运行
        md.treeprocessors.register(MetadataExtractor(md), 'metadata_extractor', 20)
