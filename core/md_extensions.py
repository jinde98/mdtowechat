from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
import re

class MetadataExtractor(Treeprocessor):
    """
    一个自定义的Markdown树处理器（Treeprocessor），用于在Markdown解析过程中
    遍历其生成的元素树（AST），并从中提取文章的元数据。

    这种方法比用正则表达式解析原始文本更健壮和准确。
    """
    def __init__(self, md):
        super().__init__(md)
        # 初始化一个空的元数据字典结构
        self.metadata = {}

    def run(self, root):
        """
        这是树处理器的核心方法，在每次Markdown解析时被调用。
        :param root: Markdown文档解析后生成的元素树的根节点。
        """
        # 关键：在每次运行时重置元数据，以防止处理多篇文章时数据发生污染。
        self.metadata = {
            'title': None,
            'author': None,
            'description': None,
            'cover_image': None,
            'all_image_urls': []
        }
        
        # 1. 提取所有图片URL
        # 遍历树中所有的 'img' 标签，并收集其 'src' 属性。
        self.metadata['all_image_urls'] = [img.get('src') for img in root.iter('img') if img.get('src')]
        # 将找到的第一张图片作为默认的封面图。
        if self.metadata['all_image_urls']:
            self.metadata['cover_image'] = self.metadata['all_image_urls'][0]

        # 2. 遍历所有顶级子元素来提取标题、作者和描述
        title_found = False
        description_found = False
        for el in list(root):
            # 提取标题：将遇到的第一个标题（h1-h6）作为文章标题。
            if el.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and not title_found:
                self.metadata['title'] = ''.join(el.itertext()).strip()
                title_found = True
                # 标题是内容的一部分，不能移除。

            # 提取作者：寻找第一个以 "作者" 或 "author" 开头的引用块（blockquote）。
            # 格式约定: `> 作者：张三`
            if el.tag == 'blockquote' and not self.metadata['author']:
                p_tags = el.findall('p')
                if p_tags:
                    text = ''.join(p_tags[0].itertext()).strip()
                    # 使用正则表达式进行不区分大小写的匹配
                    match = re.match(r'^(作者|author)[:：\s]*(.*)', text, re.IGNORECASE)
                    if match:
                        self.metadata['author'] = match.group(2).strip()
                        # 作者信息是纯元数据，理论上可以从最终渲染中移除。
                        # 但为了保持逻辑分离，这里不执行移除操作（root.remove(el)），
                        # 而是交由上层逻辑决定如何处理。

            # 提取描述：将遇到的第一个足够长的非空段落（p）作为文章描述。
            if el.tag == 'p' and not description_found:
                text = ''.join(el.itertext()).strip()
                # 确保段落有实际内容（长度大于10），避免抓取到无意义的短文本。
                if len(text) > 10:
                    self.metadata['description'] = text[:120].strip()  # 截取前120个字符作为摘要
                    description_found = True
        
        # 3. 将收集到的元数据附加到markdown实例上
        # 这是将数据传递出去的关键步骤。外部代码可以通过访问 `md.extracted_metadata` 来获取结果。
        self.md.extracted_metadata = self.metadata

class MetadataExtension(Extension):
    """
    一个工厂类，用于将 `MetadataExtractor` 注册为 `markdown` 库的正式扩展。
    """
    def extendMarkdown(self, md):
        """
        这是 `markdown` 库扩展的标准入口点。
        :param md: 当前的 `markdown` 实例。
        """
        # 注册我们的树处理器。
        # 'metadata_extractor' 是为这个处理器起的名字。
        # 20 是处理器的优先级。一个较高的优先级（>15）可以确保它在
        # `markdown` 库内置的 `inline` 处理器（负责处理 `<img>` 等）之后运行，
        # 从而能够访问到已经被解析出来的 `<img>` 标签。
        md.treeprocessors.register(MetadataExtractor(md), 'metadata_extractor', 20)
