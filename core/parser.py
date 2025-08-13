import markdown
from .md_extensions import MetadataExtension

class ContentParser:
    """
    负责使用Markdown AST来解析内容，提取文章元数据。
    """
    def __init__(self):
        """初始化一个带有元数据提取扩展的Markdown实例。"""
        self.md = markdown.Markdown(extensions=[MetadataExtension()])

    def parse_markdown(self, markdown_content):
        """
        通过处理Markdown文本来解析元数据。
        """
        # 我们需要调用convert来触发treeprocessor，但我们不关心其HTML输出。
        self.md.convert(markdown_content)
        
        # 从实例中获取由我们的扩展提取的元数据
        metadata = getattr(self.md, 'extracted_metadata', {})
        
        # 重置以供下次使用
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
