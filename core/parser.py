import markdown
from .md_extensions import MetadataExtension

class ContentParser:
    """
    Markdown内容解析器。

    本类的核心职责是解析Markdown文本，并利用自定义的 `MetadataExtension` 扩展
    来提取结构化的元数据（如标题、作者、封面图等）。

    它作为一个更高层次的封装，简化了元数据提取的调用过程。
    """
    def __init__(self):
        """
        初始化解析器。
        在内部，它会创建一个加载了 `MetadataExtension` 的 `markdown.Markdown` 实例。
        这个实例在 `ContentParser` 的生命周期内可以被复用。
        """
        self.md = markdown.Markdown(extensions=[MetadataExtension()])

    def parse_markdown(self, markdown_content):
        """
        解析给定的Markdown文本，并返回提取出的元数据字典。

        工作流程：
        1. 调用 `self.md.convert()`。这一步的**主要目的不是为了获取HTML**，
           而是为了**触发**注册在 `markdown` 处理管道中的 `MetadataExtractor` 树处理器。
        2. `MetadataExtractor` 在执行时，会将其提取到的元数据附加到 `self.md` 实例上。
        3. 从 `self.md` 实例中安全地获取这个元数据。
        4. 调用 `self.md.reset()` 清理实例状态，确保下次解析不受影响。

        :param markdown_content: 需要解析的Markdown文本字符串。
        :return: 一个包含元数据的字典。如果未提取到任何数据，则为空字典。
        """
        # 我们调用 convert() 主要是为了触发树处理器（Treeprocessor）的 run() 方法。
        # 其返回的HTML在这里是不需要的。
        self.md.convert(markdown_content)
        
        # `MetadataExtractor` 会将结果存储在 `md.extracted_metadata` 属性中。
        # 使用 getattr 提供一个默认值，以防扩展因某种原因未能成功附加属性。
        metadata = getattr(self.md, 'extracted_metadata', {})
        
        # `markdown` 实例是有状态的。调用 reset() 是一个好习惯，可以清空内部状态，
        # 避免上一次解析的数据（如脚注等）影响到下一次。
        self.md.reset()
        
        return metadata

if __name__ == '__main__':
    # 示例用法
    markdown_test_content = """
# 我的文章标题

> 作者: 张三

这是一个段落，用作描述。包含一张本地图片：![本地图片1](assets/images/pic1.jpg)。
还有一张图片在其他文件夹：![本地图片2](../uploads/another.png)。

一些其他内容。

![网络图片](https://example.com/remote.jpg)

![本地图片3](./images/test.gif)
"""

    parser = ContentParser()
    parsed_data = parser.parse_markdown(markdown_test_content)

    print("--- 包含元数据的测试 ---")
    print(f"标题: {parsed_data.get('title')}")
    print(f"作者: {parsed_data.get('author')}")
    print(f"描述: {parsed_data.get('description')}")
    print(f"封面图片: {parsed_data.get('cover_image')}")
    print(f"所有图片URL: {parsed_data.get('all_image_urls')}")

    markdown_no_metadata = """
## 这是一个H2标题

这是一个没有明确元数据的文档。
![无元数据图片](local_img.jpg)
"""
    parsed_no_metadata = parser.parse_markdown(markdown_no_metadata)
    print("\n--- 不包含元数据的测试 ---")
    print(f"标题: {parsed_no_metadata.get('title')}") # 应该为 None
    print(f"作者: {parsed_no_metadata.get('author')}") # 应该为 None
    print(f"描述: {parsed_no_metadata.get('description')}") # 应该是 "这是一个没有明确元数据的文档。"
    print(f"封面图片: {parsed_no_metadata.get('cover_image')}") # 应该是 "local_img.jpg"
    print(f"所有图片URL: {parsed_no_metadata.get('all_image_urls')}")
