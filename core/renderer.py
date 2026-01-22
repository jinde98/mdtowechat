import markdown
import re
from bs4 import BeautifulSoup
import os
import uuid
from styles import BLUE, NICE, GREEN, GEEK_BLACK, ORANGE_RED, BLUE_GLOW, MINIMALIST_WHITE, DREAMY_PURPLE, BOLD_RED

# 定义主题映射
THEMES = {
    "minimalist_white": MINIMALIST_WHITE, # 默认主题放在第一位
    "blue": BLUE,
    "nice": NICE,
    "green": GREEN,
    "geek_black": GEEK_BLACK,
    "orange_red": ORANGE_RED,
    "blue_glow": BLUE_GLOW,
    "dreamy_purple": DREAMY_PURPLE,
    "bold_red": BOLD_RED,
}

class MarkdownRenderer:
    """
    负责将Markdown文本渲染为兼容微信公众号格式的、带有内联样式的HTML。
    """
    def __init__(self, theme_name="minimalist_white"):
        """
        初始化渲染器。
        
        :param theme_name: 初始化的主题名称。
        """
        self.theme = self._load_theme(theme_name)
        # 配置Python-Markdown库，加载一系列常用扩展
        self.md = markdown.Markdown(
            extensions=[
                'markdown.extensions.fenced_code',  # 支持 ```code``` 语法
                'markdown.extensions.footnotes',    # 支持脚注
                'markdown.extensions.attr_list',    # 支持为元素添加属性，如 `{#id .class}`
                'markdown.extensions.def_list',     # 支持定义列表
                'markdown.extensions.sane_lists',   # 改进的列表解析逻辑
                'markdown.extensions.codehilite',   # 代码高亮
                'markdown.extensions.tables',       # 支持表格
                'markdown.extensions.toc',          # 支持目录生成
                'markdown.extensions.extra',        # 包含多种小改进的集合
            ],
            extension_configs={
                'markdown.extensions.codehilite': {
                    'pygments_style': 'monokai',  # 指定代码高亮的样式
                    'noclasses': True,           # 关键：生成内联style属性，而不是CSS class
                },
                'markdown.extensions.toc': {
                    'toc_depth': '2-3',  # 目录仅包含H2和H3标题
                },
            },
            tab_length=2,
        )

    def set_theme(self, theme_name):
        """
        在运行时切换渲染的主题。
        """
        self.theme = self._load_theme(theme_name)

    def get_available_themes(self):
        """
        获取所有可用的主题名称列表。
        """
        return list(THEMES.keys())

    def _load_theme(self, theme_name):
        """
        从 `styles` 包中加载指定主题的样式字典。
        如果主题不存在，则回退到默认主题。
        """
        theme = THEMES.get(theme_name.lower())
        if not theme:
            # 使用 logging 模块会更规范，但此处保持与原文一致
            print(f"警告: 主题 '{theme_name}' 未找到。将使用默认的 'minimalist_white' 主题。")
            theme = MINIMALIST_WHITE
        return theme

    def render(self, markdown_text, mode="light"):
        """
        将Markdown文本渲染为最终的HTML字符串。这是本类的核心公共方法。

        :param markdown_text: 原始的Markdown文本内容。
        :param mode: 当前的显示模式（"light" 或 "dark"），用于调整颜色。
        :return: 渲染完成、可用于微信的HTML内容字符串。
        """
        # 步骤 1: 预处理Markdown文本，修复常见书写错误
        processed_text = self._preprocess_markdown_text(markdown_text)

        # 步骤 2: 使用Python-Markdown库将文本转换为基础HTML片段
        html_fragment = self.md.convert(processed_text)

        # 步骤 3: 使用BeautifulSoup将HTML片段解析为一个完整的文档对象，便于操作
        doc = BeautifulSoup(
            f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>Preview</title></head><body>{html_fragment}</body></html>',
            'html.parser'
        )

        # 步骤 4: 递归处理和美化列表，解决微信编辑器的兼容性问题
        self._process_lists(doc)

        # 步骤 5: 将主题样式以内联方式应用到HTML元素上
        self._apply_theme_styles(doc, mode)
        
        # 步骤 6: 美化代码块，添加macOS风格的窗口装饰
        self._apply_mac_style_to_code_blocks(doc)

        # 步骤 7: 过滤掉微信不支持的HTML标签和属性，确保兼容性
        self._filter_unsupported_elements(doc)
 
        # 步骤 8: 返回body标签内的所有HTML内容
        return doc.body.decode_contents()

    def _preprocess_markdown_text(self, text):
        """
        对原始Markdown文本进行一系列预处理，以修复常见问题并提高解析成功率。
        这些规则基于实际使用中遇到的各种不规范写法。
        """
        # 规则1: 修复用户可能意外输入的 `<[...](...)` 或 `<![...](...)` 格式
        processed_text = re.sub(r'<!?(\[.*?\]\(.*?\))', r'\1', text)
        
        # 规则2: 在段落和列表之间强制添加换行，确保Markdown解析器能正确识别列表的开始。
        # 例如： "一些文字\n- 列表项" -> "一些文字\n\n- 列表项"
        processed_text = re.sub(r'([^\n])\n([ \t]*([\-\*\+]|\d+\.)\s)', r'\1\n\n\2', processed_text)

        # 规则3: 在相邻的不同类型列表之间添加换行，防止它们被错误地合并。
        processed_text = re.sub(r'([ \t]*[\-\*\+]\s.*\n)(?=[ \t]*\d+\.\s)', r'\1\n', processed_text)
        processed_text = re.sub(r'([ \t]*\d+\.\s.*\n)(?=[ \t]*[\-\*\+]\s)', r'\1\n', processed_text)

        # 规则4: 移除普通段落行首的四个空格，防止它们被错误地解析为代码块。
        # 这个操作需要逐行处理，并跳过真正的代码块（```...```）内部的行。
        lines = processed_text.split('\n')
        in_code_block = False
        new_lines = []
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
            
            if not in_code_block and line.startswith('    ') and line.strip() != "":
                new_lines.append(line[4:])
            else:
                new_lines.append(line)
        return '\n'.join(new_lines)
 
    def _apply_theme_styles(self, soup, mode):
        """
        根据当前主题和显示模式（亮/暗），将CSS样式以内联方式应用到HTML元素上。
        
        :param soup: BeautifulSoup文档对象。
        :param mode: "light" 或 "dark"。
        """
        # 根据模式确定body的背景和前景（文字）颜色
        # 如果当前是light模式，强制背景为白色，文字为深色，以保证预览区域的可读性
        if mode == "light":
            body_bg_color = "#ffffff"
            body_text_color = "#333333"
        else:
            # 如果是dark模式，则从主题中获取或使用默认深色
            body_bg_color = self.theme.get('body_background_color', '#2e2e2e')
            body_text_color = self.theme.get('body_text_color', '#f0f0f0')
        
        original_body_style = self.theme.get('body', '')
        # 强制将预览区域的背景设置为白色，以确保在亮色模式下始终可见
        soup.body['style'] = f"background-color: #ffffff !important; color: {body_text_color}; {original_body_style}".strip()

        # 如果主题定义了 'wrapper' 样式，则创建一个div将所有内容包裹起来
        if 'wrapper' in self.theme:
            wrapper_div = soup.new_tag('div')
            wrapper_div['style'] = self.theme['wrapper']
            # 将body的所有子元素移动到wrapper_div中
            for child in list(soup.body.children):
                wrapper_div.append(child)
            soup.body.append(wrapper_div)
 
        # 遍历主题字典，为每个HTML标签应用样式
        for tag_name, style in self.theme.items():
            # 跳过一些特殊处理或不应被全局样式影响的标签
            if tag_name in ['body', 'wrapper', 'section', 'ul', 'ol', 'li', 'img', 'pre', 'code']:
                continue
 
            for elem in soup.find_all(tag_name):
                existing_style = elem.get('style', '')
                # 如果主题样式中已定义颜色，则直接使用；否则，使用模式决定的全局文字颜色。
                if 'color:' in style.lower():
                    elem['style'] = f"{style}; {existing_style}".strip()
                else:
                    elem['style'] = f"color: {body_text_color}; {style}; {existing_style}".strip()

        # 显式处理 <img> 标签的样式，确保 max-width 等属性被应用
        if 'img' in self.theme:
            img_style = self.theme['img']
            for img_elem in soup.find_all('img'):
                existing_style = img_elem.get('style', '')
                img_elem['style'] = f"{img_style}; {existing_style}".strip()

        # 为所有顶级块级元素应用 'section' 样式，这通常用于控制段间距
        content_container = soup.body.find('div') if 'wrapper' in self.theme else soup.body
        if 'section' in self.theme and content_container:
            # 使用 'list(children)' 是因为我们将要修改这个列表
            for child in list(content_container.children):
                # 只包裹实际的HTML标签，忽略文本节点和脚本等
                if hasattr(child, 'name') and child.name:
                    section_tag = soup.new_tag('section')
                    section_tag['style'] = self.theme['section']
                    child.wrap(section_tag) # .wrap() 方法会自动处理元素的位置

    def _apply_mac_style_to_code_blocks(self, soup):
        """
        为所有 `<pre>` 代码块添加macOS风格的窗口装饰。
        """
        for pre_tag in soup.find_all('pre'):
            # 1. 创建窗口容器
            container = soup.new_tag('div')
            container['style'] = (
                "background: #1E1E1E; border-radius: 5px; "
                "box-shadow: rgba(0, 0, 0, 0.55) 0px 2px 10px; "
                "margin-top: 20px; margin-bottom: 20px; overflow: hidden;"
            )

            # 2. 创建标题栏
            title_bar = soup.new_tag('div')
            title_bar['style'] = (
                "height: 30px; background-color: #1E1E1E; display: flex; "
                "align-items: center; padding-left: 10px;"
            )

            # 3. 创建红绿灯按钮
            colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
            for color in colors:
                dot = soup.new_tag('span')
                dot['style'] = (
                    f"height: 12px; width: 12px; background-color: {color}; "
                    "border-radius: 50%; display: inline-block; margin-right: 8px;"
                )
                title_bar.append(dot)
            
            # 4. 创建代码内容的容器
            content_area = soup.new_tag('div')
            content_area['style'] = (
                "padding: 16px; overflow-x: auto; color: #DCDCDC; "
                "font-family: Operator Mono, Consolas, Monaco, Menlo, monospace; "
                "font-size: 14px; line-height: 1.5;"
            )
            
            # 5. 在文档流中，用新创建的窗口容器替换掉原来的 <pre> 标签
            pre_tag.replace_with(container)
            
            # 6. 将原始的 <pre> 标签本身移动到新容器的代码内容区
            # 同时为 <pre> 和 <code> 设置必要的样式以确保滚动和字体正确
            pre_tag['style'] = "overflow-x: auto; background: #1E1E1E; padding: 0; margin: 0;"
            if pre_tag.code:
                pre_tag.code['style'] = "font-family: inherit; font-size: inherit;"
            content_area.append(pre_tag)
            
            # 7. 组装最终的窗口结构
            container.append(title_bar)
            container.append(content_area)


    def _process_lists(self, soup):
        """
        [核心渲染逻辑] 递归地清理和样式化列表，以增强在微信编辑器中的兼容性和美观度。
        
        该函数是保证列表在微信公众号编辑器中正确显示的核心。它解决了多个由
        Markdown解析和微信编辑器特性共同导致的问题。请勿轻易修改此函数的逻辑。
        新增主题时，也无需为 ul, ol, li 单独定义样式，此函数会统一处理。

        主要解决的问题：
        1. 清理因Markdown书写不规范（如多余的空行）而产生的空的 `<li>` 标签。
        2. 移除 `markdown` 库为包含嵌套列表的 `<li>` 自动包裹的 `<p>` 标签，此举可防止不期望的额外换行。
        3. 构建一个稳定、健壮的 `<li>` 内部结构 (`<section><span>...</span>...</section>`)，
           以抵抗微信编辑器的二次解析和样式破坏。
        """
        def style_list_items_recursively(list_tag, level=0):
            is_ordered = list_tag.name == 'ol'
            # 移除默认的项目符号，因为我们将手动添加
            list_tag['style'] = "list-style-type: none; padding: 0; margin: 0;"
            
            item_counter = 1
            # 使用 list() 创建一个副本，因为我们将在循环中修改 `li` 的父节点
            for li in list(list_tag.find_all('li', recursive=False)):
                # 首先，递归处理所有嵌套在当前 `li` 中的列表
                for nested_list in li.find_all(['ul', 'ol'], recursive=False):
                    style_list_items_recursively(nested_list, level + 1)
                
                # 清理步骤 1: 移除 `li` 内部多余的 `<p>` 包装。
                # 这通常发生在列表项包含多行文本时。
                if li.p and len(li.find_all(recursive=False)) == 1:
                    li.p.unwrap() # .unwrap() 会移除 <p> 标签但保留其内容
                
                # 清理步骤 2: 删除空的或只包含空白字符的 `<li>` 标签
                text = li.get_text(strip=True).replace(u'\xa0', '').strip()
                if not text and not li.find('img'): # 保留包含图片的空列表项
                    li.decompose() # .decompose() 会将标签及其内容完全移除
                    continue

                # 样式化步骤 1: 应用缩进
                indent_size = 2  # em
                li['style'] = f"display: block; margin-bottom: 0.5em; padding-left: {level * indent_size}em;"

                # 样式化步骤 2: 构建健壮的内部结构
                # a. 创建一个新的 <section> 标签来包裹 `li` 的所有内容
                content_section = soup.new_tag('section')
                for child in list(li.children):
                    content_section.append(child)

                # b. 手动创建项目符号（有序或无序）
                prefix_text = f"{item_counter}. " if is_ordered else "• "
                prefix_span = soup.new_tag('span')
                # 使用不间断空格 (U+00A0) 代替普通空格，防止被微信编辑器压缩或忽略
                prefix_span.string = prefix_text.replace(" ", u"\u00A0")
                prefix_span['style'] = "margin-right: 0.6em;"
                
                # c. 将项目符号插入到 section 的最前面
                content_section.insert(0, prefix_span)

                # d. 清空原始的 `li`，然后将包含所有内容的新 section 放入其中
                li.clear()
                li.append(content_section)
                
                if is_ordered:
                    item_counter += 1

        # 从文档的顶层列表开始递归处理
        for list_tag in soup.find_all(['ul', 'ol']):
            # 确保只从最外层的列表开始，避免重复处理
            if not list_tag.find_parent(['ul', 'ol']):
                style_list_items_recursively(list_tag, 0)

    def _filter_unsupported_elements(self, soup):
        """
        过滤掉微信公众号编辑器不支持或可能引起兼容性问题的HTML标签和属性。
        """
        # 移除 <script> 和 <style> 标签，防止恶意代码和样式冲突
        for s in soup(['script', 'style']):
            s.decompose()

        # 遍历所有标签，只保留白名单中的属性
        for tag in soup.find_all(True):
            # body等标签上的属性通常是安全的
            if tag.name in ['html', 'body', 'head']:
                continue
                
            allowed_attrs = [
                'style', 'src', 'href', 'alt', 'title', 
                'width', 'height', 'data-src', 'data-type', 
                'data-w', 'data-h'
            ]
            # 创建一个属性字典的副本进行迭代，因为我们不能在迭代时修改它
            attrs = dict(tag.attrs)
            for attr, _ in attrs.items():
                if attr not in allowed_attrs:
                    del tag[attr]
