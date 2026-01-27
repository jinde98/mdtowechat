import markdown
import re
from bs4 import BeautifulSoup
import os
import uuid
from styles import BLUE, NICE, GREEN, GEEK_BLACK, ORANGE_RED, BLUE_GLOW, MINIMALIST_WHITE, DREAMY_PURPLE, BOLD_RED

# 定义主题映射
THEMES = {
    "default": MINIMALIST_WHITE, # 兼容旧代码的 'default' 引用
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

    def render(self, markdown_text, mode="light", for_preview=False):
        """
        将Markdown文本渲染为最终的HTML字符串。这是本类的核心公共方法。

        :param markdown_text: 原始的Markdown文本内容。
        :param mode: 当前的显示模式（"light" 或 "dark"），用于调整颜色。
        :param for_preview: 是否为本地预览模式。（注意：为了解决微信API的45166错误，现在无论是否预览，都将强制转换微信特有标签为标准HTML）
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

        # 步骤 6.5: 处理微信特有的自定义标签（仅在预览模式下）
        if for_preview:
            self._transform_wechat_tags(doc)

        # 步骤 7: 过滤掉微信不支持的HTML标签和属性，确保兼容性
        self._filter_unsupported_elements(doc)
 
        # 步骤 8: 返回body标签内的所有HTML内容
        return doc.body.decode_contents()

    def _transform_wechat_tags(self, soup):
        """
        将微信特有的自定义标签转换为可视化的HTML结构。
        目前支持: <mp-common-profile> (公众号名片)
        """
        for profile in soup.find_all('mp-common-profile'):
            nickname = profile.get('data-nickname', '公众号')
            headimg = profile.get('data-headimg', '')
            # 创建模拟的名片容器
            card_div = soup.new_tag('div')
            card_div['style'] = (
                "display: flex; align-items: center; padding: 12px; "
                "border: 1px solid #EAEAEA; background-color: #FAFAFA; "
                "border-radius: 4px; margin: 20px 0; max-width: 100%; box-sizing: border-box;"
            )
            
            # 头像
            if headimg:
                img_tag = soup.new_tag('img')
                img_tag['src'] = headimg
                img_tag['style'] = (
                    "width: 50px; height: 50px; border-radius: 50%; "
                    "margin-right: 12px; object-fit: cover; flex-shrink: 0;"
                )
                card_div.append(img_tag)
            
            # 文本信息容器
            info_div = soup.new_tag('div')
            info_div['style'] = "flex: 1; min-width: 0;"
            
            # 昵称
            name_div = soup.new_tag('div')
            name_div.string = nickname
            name_div['style'] = (
                "font-size: 16px; font-weight: bold; color: #333; "
                "margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            )
            info_div.append(name_div)
            
            # 描述
            desc_div = soup.new_tag('div')
            desc_div.string = "公众号"
            desc_div['style'] = "font-size: 12px; color: #999;"
            info_div.append(desc_div)
            
            card_div.append(info_div)
            
            profile.replace_with(card_div)

    def _preprocess_markdown_text(self, text):
        """
        对原始Markdown文本进行一系列预处理，以修复常见问题并提高解析成功率。
        """
        # 规则1: 修复用户可能意外输入的 `<[...](...)` 或 `<![...](...)` 格式
        processed_text = re.sub(r'<!?(\[.*?\]\(.*?\))', r'\1', text)
        
        # 规则2: 在段落和列表之间强制添加换行，确保Markdown解析器能正确识别列表的开始。
        processed_text = re.sub(r'([^\n])\n([ \t]*([\-\*\+]|\d+\.)\s)', r'\1\n\n\2', processed_text)

        # 规则3: 在相邻的不同类型列表之间添加换行，防止它们被错误地合并。
        processed_text = re.sub(r'([ \t]*[\-\*\+]\s.*\n)(?=[ \t]*\d+\.\s)', r'\1\n', processed_text)
        processed_text = re.sub(r'([ \t]*\d+\.\s.*\n)(?=[ \t]*[\-\*\+]\s)', r'\1\n', processed_text)

        # 规则4: 移除普通段落行首的四个空格，防止它们被错误地解析为代码块。
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
        """
        # 根据模式确定body的背景和前景（文字）颜色
        if mode == "light":
            body_bg_color = "#ffffff"
            body_text_color = "#333333"
        else:
            body_bg_color = self.theme.get('body_background_color', '#2e2e2e')
            body_text_color = self.theme.get('body_text_color', '#f0f0f0')
        
        original_body_style = self.theme.get('body', '')
        soup.body['style'] = f"background-color: #ffffff !important; color: {body_text_color}; {original_body_style}".strip()

        # 如果主题定义了 'wrapper' 样式，则创建一个div将所有内容包裹起来
        if 'wrapper' in self.theme:
            wrapper_div = soup.new_tag('div')
            wrapper_div['style'] = self.theme['wrapper']
            for child in list(soup.body.children):
                wrapper_div.append(child)
            soup.body.append(wrapper_div)
 
        # 遍历主题字典，为每个HTML标签应用样式
        for tag_name, style in self.theme.items():
            if tag_name in ['body', 'wrapper', 'section', 'ul', 'ol', 'li', 'img', 'pre', 'code']:
                continue
 
            for elem in soup.find_all(tag_name):
                existing_style = elem.get('style', '')
                if 'color:' in style.lower():
                    elem['style'] = f"{style}; {existing_style}".strip()
                else:
                    elem['style'] = f"color: {body_text_color}; {style}; {existing_style}".strip()

        if 'img' in self.theme:
            img_style = self.theme['img']
            for img_elem in soup.find_all('img'):
                existing_style = img_elem.get('style', '')
                img_elem['style'] = f"{img_style}; {existing_style}".strip()

        content_container = soup.body.find('div') if 'wrapper' in self.theme else soup.body
        if 'section' in self.theme and content_container:
            for child in list(content_container.children):
                if hasattr(child, 'name') and child.name and child.name not in ['section', 'div', 'mp-common-profile']: # 避免重复包裹已有容器
                    section_tag = soup.new_tag('section')
                    section_tag['style'] = self.theme['section']
                    child.wrap(section_tag)

    def _apply_mac_style_to_code_blocks(self, soup):
        # ... (代码不变) ...
        """
        为所有 `<pre>` 代码块添加macOS风格的窗口装饰。
        """
        for pre_tag in soup.find_all('pre'):
            container = soup.new_tag('div')
            container['style'] = (
                "background: #1E1E1E; border-radius: 5px; "
                "box-shadow: rgba(0, 0, 0, 0.55) 0px 2px 10px; "
                "margin-top: 20px; margin-bottom: 20px; overflow: hidden;"
            )

            title_bar = soup.new_tag('div')
            title_bar['style'] = (
                "height: 30px; background-color: #1E1E1E; display: flex; "
                "align-items: center; padding-left: 10px;"
            )

            colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
            for color in colors:
                dot = soup.new_tag('span')
                dot['style'] = (
                    f"height: 12px; width: 12px; background-color: {color}; "
                    "border-radius: 50%; display: inline-block; margin-right: 8px;"
                )
                title_bar.append(dot)
            
            content_area = soup.new_tag('div')
            content_area['style'] = (
                "padding: 16px; overflow-x: auto; color: #DCDCDC; "
                "font-family: Operator Mono, Consolas, Monaco, Menlo, monospace; "
                "font-size: 14px; line-height: 1.5;"
            )
            
            pre_tag.replace_with(container)
            
            pre_tag['style'] = "overflow-x: auto; background: #1E1E1E; padding: 0; margin: 0;"
            if pre_tag.code:
                pre_tag.code['style'] = "font-family: inherit; font-size: inherit;"
            content_area.append(pre_tag)
            
            container.append(title_bar)
            container.append(content_area)

    def _process_lists(self, soup):
        # ... (代码不变) ...
        """
        [核心渲染逻辑] 递归地清理和样式化列表，以增强在微信编辑器中的兼容性和美观度。
        """
        def style_list_items_recursively(list_tag, level=0):
            is_ordered = list_tag.name == 'ol'
            list_tag['style'] = "list-style-type: none; padding: 0; margin: 0;"
            
            item_counter = 1
            for li in list(list_tag.find_all('li', recursive=False)):
                for nested_list in li.find_all(['ul', 'ol'], recursive=False):
                    style_list_items_recursively(nested_list, level + 1)
                
                if li.p and len(li.find_all(recursive=False)) == 1:
                    li.p.unwrap() 
                
                text = li.get_text(strip=True).replace(u'\xa0', '').strip()
                if not text and not li.find('img'): 
                    li.decompose() 
                    continue

                indent_size = 2  # em
                li['style'] = f"display: block; margin-bottom: 0.5em; padding-left: {level * indent_size}em;"

                content_section = soup.new_tag('section')
                for child in list(li.children):
                    content_section.append(child)

                prefix_text = f"{item_counter}. " if is_ordered else "• "
                prefix_span = soup.new_tag('span')
                prefix_span.string = prefix_text.replace(" ", u"\u00A0")
                prefix_span['style'] = "margin-right: 0.6em;"
                
                content_section.insert(0, prefix_span)

                li.clear()
                li.append(content_section)
                
                if is_ordered:
                    item_counter += 1

        for list_tag in soup.find_all(['ul', 'ol']):
            if not list_tag.find_parent(['ul', 'ol']):
                style_list_items_recursively(list_tag, 0)

    def _filter_unsupported_elements(self, soup):
        """
        过滤掉微信公众号编辑器不支持或可能引起兼容性问题的HTML标签和属性。
        保留 mp-common-profile 及其相关属性。
        """
        # 移除 <script> 和 <style> 标签，防止恶意代码和样式冲突
        for s in soup(['script', 'style']):
            s.decompose()

        # 遍历所有标签，只保留白名单中的属性
        for tag in soup.find_all(True):
            # 特殊处理 mp-common-profile，保留其所有属性
            if tag.name == 'mp-common-profile':
                continue
                
            # body等标签上的属性通常是安全的
            if tag.name in ['html', 'body', 'head']:
                continue
                
            allowed_attrs = [
                'style', 'src', 'href', 'alt', 'title', 
                'width', 'height', 'data-src', 'data-type', 
                'data-w', 'data-h', 'class' # 保留 class 属性，这对某些微信组件很重要
            ]
            # 创建一个属性字典的副本进行迭代，因为我们不能在迭代时修改它
            attrs = dict(tag.attrs)
            for attr, _ in attrs.items():
                if attr not in allowed_attrs:
                    del tag[attr]
