import os, logging

class TemplateManager:
    """
    负责管理文章的页眉（Header）和页脚（Footer）Markdown模板文件。
    """
    def __init__(self, template_dir="templates"):
        """
        初始化模板管理器。
        
        :param template_dir: 存放模板文件的目录路径。
        """
        self.template_dir = template_dir
        self.header_path = os.path.join(self.template_dir, "header.md")
        self.footer_path = os.path.join(self.template_dir, "footer.md")
        self.log = logging.getLogger(__name__)
        self._ensure_template_files_exist()

    def _ensure_template_files_exist(self):
        """
        确保模板目录和默认的模板文件存在。
        如果不存在，则会自动创建它们，并填入默认的提示内容。
        """
        try:
            os.makedirs(self.template_dir, exist_ok=True)
            if not os.path.exists(self.header_path):
                with open(self.header_path, "w", encoding="utf-8") as f:
                    f.write("<!-- 这是页眉模板，你可以在此编辑通用头部内容 -->")
                self.log.info(f"已创建默认页眉模板: {self.header_path}")
            if not os.path.exists(self.footer_path):
                with open(self.footer_path, "w", encoding="utf-8") as f:
                    f.write("<!-- 这是页脚模板，你可以在此编辑通用尾部内容，如引导关注、版权声明等 -->")
                self.log.info(f"已创建默认页脚模板: {self.footer_path}")
        except Exception as e:
            self.log.error(f"创建模板文件或目录时出错: {e}", exc_info=True)

    def get_templates(self):
        """
        读取并返回页眉和页脚模板的内容。
        
        :return: 一个元组 (header_content, footer_content)。如果读取失败，则返回空字符串。
        """
        try:
            with open(self.header_path, "r", encoding="utf-8") as f:
                header_content = f.read()
            with open(self.footer_path, "r", encoding="utf-8") as f:
                footer_content = f.read()
            return header_content, footer_content
        except Exception as e:
            self.log.error(f"读取模板文件时出错: {e}", exc_info=True)
            return "", ""

    def save_templates(self, header_content, footer_content):
        """
        将新的内容保存到页眉和页脚模板文件中。
        
        :param header_content: 新的页眉Markdown内容。
        :param footer_content: 新的页脚Markdown内容。
        :return: 一个元组 (success, error_message)。
                 如果成功，success为True，error_message为None。
                 如果失败，success为False，error_message为错误信息的字符串。
        """
        try:
            with open(self.header_path, "w", encoding="utf-8") as f:
                f.write(header_content)
            with open(self.footer_path, "w", encoding="utf-8") as f:
                f.write(footer_content)
            self.log.info("页眉和页脚模板已成功保存。")
            return True, None
        except Exception as e:
            self.log.error(f"保存模板文件时出错: {e}", exc_info=True)
            return False, str(e)
