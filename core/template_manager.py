import os

class TemplateManager:
    """负责管理Markdown模板文件（头部和尾部）。"""
    def __init__(self, template_dir="templates"): # 初始化模板管理器，设置模板文件路径。
        self.template_dir = template_dir
        self.header_path = os.path.join(self.template_dir, "header.md")
        self.footer_path = os.path.join(self.template_dir, "footer.md")
        self._ensure_template_files_exist()

    def _ensure_template_files_exist(self):
        """确保模板目录和默认的空模板文件存在。"""
        os.makedirs(self.template_dir, exist_ok=True)
        if not os.path.exists(self.header_path):
            with open(self.header_path, "w", encoding="utf-8") as f:
                f.write("<!-- 这是头部模板，在这里编辑你的内容 -->")
        if not os.path.exists(self.footer_path):
            with open(self.footer_path, "w", encoding="utf-8") as f:
                f.write("<!-- 这是尾部模板，在这里编辑你的内容 -->")

    def get_templates(self):
        """
        读取并返回头部和尾部模板的内容。
        :return: (header_content, footer_content)
        """
        try:
            with open(self.header_path, "r", encoding="utf-8") as f:
                header_content = f.read()
            with open(self.footer_path, "r", encoding="utf-8") as f:
                footer_content = f.read()
            return header_content, footer_content
        except Exception as e:
            print(f"Error reading template files: {e}") # 打印读取模板文件时的错误信息。
            return "", ""

    def save_templates(self, header_content, footer_content):
        """
        保存头部和尾部模板的内容。
        :param header_content: 头部模板的Markdown内容
        :param footer_content: 尾部模板的Markdown内容
        :return: (success, error_message)
        """
        try:
            with open(self.header_path, "w", encoding="utf-8") as f:
                f.write(header_content)
            with open(self.footer_path, "w", encoding="utf-8") as f:
                f.write(footer_content)
            return True, None
        except Exception as e:
            print(f"Error saving template files: {e}") # 打印保存模板文件时的错误信息。
            return False, str(e)

if __name__ == '__main__':
    # 示例用法
    tm = TemplateManager()
    
    # 保存模板
    header = "# 这是我的文章头部\n\n---\n"
    footer = "\n\n---\n\n> 感谢阅读！欢迎关注我的公众号！"
    success, err = tm.save_templates(header, footer)
    if success:
        print("Templates saved successfully.")
    else:
        print(f"Failed to save templates: {err}")

    # 读取模板
    h, f = tm.get_templates()
    print("\n--- Header Template ---")
    print(h)
    print("\n--- Footer Template ---")
    print(f)
