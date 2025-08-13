import markdown
import re
from bs4 import BeautifulSoup
import os
import uuid
from .cleaner import WeChatHTMLCleaner

# 样式目录，相对于当前文件
STYLES_DIR = os.path.join(os.path.dirname(__file__), '..', 'styles')


class MarkdownRenderer:
    """负责将Markdown渲染为微信公众号兼容的HTML，并应用主题样式。"""
    def __init__(self, theme_name="default"):
        self.theme = self._load_theme(theme_name)
        self.cleaner = WeChatHTMLCleaner()
        self.md = markdown.Markdown(
            extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.footnotes',
                'markdown.extensions.attr_list',
                'markdown.extensions.def_list',
                'markdown.extensions.sane_lists',  # 确保列表解析正确
                'markdown.extensions.codehilite',
                'markdown.extensions.tables',
                'markdown.extensions.toc',
            ],
            extension_configs={
                'markdown.extensions.codehilite': {
                    'css_class': 'codehilite',
                    'pygments_style': 'monokai',  # 指定高亮样式
                    'noclasses': True, # 使用内联样式
                },
                'markdown.extensions.toc': {
                    'toc_depth': '2-3',  # 仅包含二级和三级标题
                }
            },
            tab_length=2,
        )
        # 禁用Tab键/4个空格缩进的代码块功能
        # 从块处理器列表中注销'indent'处理器
        self.md.parser.blockprocessors.deregister('indent')

    def set_theme(self, theme_name):
        """设置新的主题。"""
        self.theme = self._load_theme(theme_name)

    def get_available_themes(self):
        """获取所有可用主题的名称。"""
        try:
            files = os.listdir(STYLES_DIR)
            themes = [f.replace('.css', '') for f in files if f.endswith('.css')]
            return themes
        except FileNotFoundError:
            print(f"Warning: Styles directory not found at {STYLES_DIR}")
            return []

    def _parse_css(self, css_content):
        """一个简单的CSS解析器，将CSS文本转换为样式字典。"""
        style_dict = {}
        # 移除CSS注释
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        # 匹配选择器和其规则
        pattern = re.compile(r'([^{]+)\s*\{\s*([^}]+)\s*\}')
        matches = pattern.finditer(css_content)
        
        for match in matches:
            selectors = [s.strip() for s in match.group(1).strip().split(',')]
            rules = match.group(2).strip()
            for selector in selectors:
                if selector:
                    style_dict[selector] = rules
        return style_dict

    def _load_theme(self, theme_name):
        """从 .css 文件加载并解析指定主题的样式。"""
        theme_path = os.path.join(STYLES_DIR, f"{theme_name}.css")
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            return self._parse_css(css_content)
        except FileNotFoundError:
            print(f"Warning: Theme file '{theme_name}.css' not found in {STYLES_DIR}. Using empty theme.")
            return {}

    def render(self, markdown_text, mode="light"):
        """
        将Markdown文本渲染为微信公众号兼容的HTML。
        :param markdown_text: Markdown文本内容
        :param mode: 当前模式（"light"或"dark"）
        """
        # 预处理文本，以修复常见问题并防止解析器崩溃
        # 1. 修复用户可能意外输入的 `<[...](...)` 或 `<![...](...)` 格式
        processed_text = re.sub(r'<!?(\[.*?\]\(.*?\))', r'\1', markdown_text)
        # 2. 在相邻的不同类型列表之间添加换行符
        processed_text = re.sub(r'([ \t]*[\-\*\+]\s.*\n)(?=[ \t]*\d+\.\s)', r'\1\n', processed_text)
        processed_text = re.sub(r'([ \t]*\d+\.\s.*\n)(?=[ \t]*[\-\*\+]\s)', r'\1\n', processed_text)

        # 1. 将Markdown转换为HTML片段
        html_fragment = self.md.convert(processed_text)

        # 2. 创建一个完整的HTML文档结构
        doc = BeautifulSoup(
            '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>Preview</title></head><body></body></html>',
            'html.parser'
        )
        
        # 3. 将HTML片段解析并附加到主文档的body中
        fragment_soup = BeautifulSoup(html_fragment, 'html.parser')
        doc.body.extend(fragment_soup.contents)

        # 4. 应用主题样式
        self._apply_theme_styles(doc, mode)

        # 5. 使用Cleaner清理HTML以兼容微信
        cleaned_soup = self.cleaner.clean(doc)
 
        # 6. 返回body内的HTML内容
        return cleaned_soup.body.decode_contents()
 
    def _apply_theme_styles(self, soup, mode):
        """
        根据当前主题和模式应用CSS样式到HTML元素。
        :param soup: BeautifulSoup对象
        :param mode: 当前模式（"light"或"dark"）
        """
        # 应用body和wrapper样式
        body_bg_color = "#ffffff" if mode == "light" else "#2e2e2e"
        body_text_color = "#333333" if mode == "light" else "#f0f0f0"
        
        # 获取主题中body的原始样式
        original_body_style = self.theme.get('body', '')
        
        # 强制设置body的背景和字体颜色，并保留原始样式
        soup.body['style'] = f"background-color: {body_bg_color}; color: {body_text_color}; {original_body_style}".strip()

        if 'wrapper' in self.theme:
            wrapper_div = soup.new_tag('div')
            wrapper_div['style'] = self.theme['wrapper']
            for child in list(soup.body.children):
                wrapper_div.append(child)
            soup.body.append(wrapper_div)
 
        # 遍历所有元素并应用样式
        for tag_name, style in self.theme.items():
            # 列表由_process_lists处理，跳过
            # img标签的颜色通常不应受模式影响，代码块颜色已在styles.py中明确设置
            if tag_name in ['body', 'wrapper', 'section', 'ul', 'ol', 'li', 'img', 'pre', 'code_block', 'code_inline']:
                continue
 
            for elem in soup.find_all(tag_name):
                existing_style = elem.get('style', '')
                # 强制覆盖颜色，确保模式切换生效
                elem['style'] = f"color: {body_text_color}; {style}; {existing_style}".strip()

        # 显式处理 img 标签的样式，确保其 max-width 等属性被应用
        if 'img' in self.theme:
            img_style = self.theme['img']
            for img_elem in soup.find_all('img'):
                existing_style = img_elem.get('style', '')
                # 将主题中定义的 img 样式应用到元素上
                img_elem['style'] = f"{img_style}; {existing_style}".strip()

        # 对所有顶级块元素应用section样式
        body_content = soup.body.find('div') if 'wrapper' in self.theme else soup.body
        if 'section' in self.theme:
            for child in list(body_content.children):
                if child.name and child.name not in ['style', 'script']:
                    section_tag = soup.new_tag('section')
                    section_tag['style'] = self.theme['section']
                    child.wrap(section_tag)
        
        # 强制应用表格样式以确保微信兼容性
        table_style = "width: 100%; border-collapse: collapse; margin: 20px 0;"
        th_td_style = "border: 1px solid #ddd; padding: 8px; text-align: left;"
        th_style = "background-color: #f2f2f2;"

        for table_elem in soup.find_all('table'):
            existing_style = table_elem.get('style', '')
            table_elem['style'] = f"{table_style} {existing_style}".strip()

        for th_elem in soup.find_all('th'):
            existing_style = th_elem.get('style', '')
            th_elem['style'] = f"{th_td_style} {th_style} {existing_style}".strip()

        for td_elem in soup.find_all('td'):
            existing_style = td_elem.get('style', '')
            td_elem['style'] = f"{th_td_style} {existing_style}".strip()
        
        # 应用代码块的macOS样式
        self._apply_mac_style_to_code_blocks(soup)

    def _apply_mac_style_to_code_blocks(self, soup):
        """为所有<pre>代码块应用macOS窗口样式，并显示编程语言（如果可用）。"""
        for pre_tag in soup.find_all('pre'):
            # 尝试从内部的 <code> 标签获取语言信息
            code_tag = pre_tag.find('code')
            language = ''
            if code_tag and code_tag.get('class'):
                # class 通常是 ['language-python']
                lang_class = code_tag.get('class')[0]
                if lang_class.startswith('language-'):
                    language = lang_class.replace('language-', '').strip()

            # 1. 创建macOS窗口容器
            container = soup.new_tag('div')
            container['style'] = (
                "background: #2d2d2d; "
                "border-radius: 8px; "
                "box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23); "
                "margin-bottom: 1.5em; "
                "overflow: hidden;"
            )

            # 2. 创建标题栏
            title_bar = soup.new_tag('div')
            title_bar['style'] = (
                "height: 28px; "
                "background: #e0e0e0; "
                "display: flex; "
                "align-items: center; "
                "padding: 0 10px;" # 调整内边距
            )

            # 3. 创建红绿灯按钮
            button_wrapper = soup.new_tag('div')
            colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
            for color in colors:
                dot = soup.new_tag('span')
                dot['style'] = (
                    f"height: 12px; "
                    f"width: 12px; "
                    f"background-color: {color}; "
                    f"border-radius: 50%; "
                    "display: inline-block; "
                    "margin-right: 8px;"
                )
                button_wrapper.append(dot)
            title_bar.append(button_wrapper)
            
            # 4. 如果有语言信息，则显示它
            if language:
                lang_span = soup.new_tag('span')
                lang_span.string = language
                lang_span['style'] = (
                    "color: #555; "
                    "font-size: 12px; "
                    "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; "
                    "flex-grow: 1; "
                    "text-align: center;"
                )
                title_bar.append(lang_span)
                # 为了让语言居中，给红绿灯按钮添加一个等宽的占位符
                placeholder = soup.new_tag('div')
                placeholder.append(button_wrapper.decode_contents()) # 复制按钮内容
                placeholder['style'] = "visibility: hidden;" # 但使其不可见
                title_bar.append(placeholder)


            # 5. 创建代码内容区域
            content_area = soup.new_tag('div')
            content_area['style'] = "padding: 15px; overflow-x: auto;"
            
            # 6. 在文档中，用新容器替换掉旧的<pre>标签
            pre_tag.replace_with(container)
            
            # 7. 将原始的、完整的<pre>标签移动到新容器的内容区
            content_area.append(pre_tag)
            
            # 8. 组装窗口
            container.append(title_bar)
            container.append(content_area)

if __name__ == '__main__':
    # 示例用法
    markdown_content = """
- 无序列表项 1
  1. 嵌套有序列表项 1.1
  2. 嵌套有序列表项 1.2
- 无序列表项 2

1. 有序列表项 1
2. 有序列表项 2
   - 嵌套无序列表项 2.1
   - 嵌套无序列表项 2.2
"""
    
    renderer = MarkdownRenderer(theme_name="blue")
    html_output = renderer.render(markdown_content, mode="light") # 示例用法中也传递 mode
    
    with open("final_output.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("Final output saved to final_output.html")
