import markdown
import re
from bs4 import BeautifulSoup
import os
import uuid
from styles import BLUE, NICE, GREEN, GEEK_BLACK, ORANGE_RED, BLUE_GLOW

# 定义主题映射
THEMES = {
    "blue": BLUE,
    "nice": NICE,
    "green": GREEN,
    "geek_black": GEEK_BLACK,
    "orange_red": ORANGE_RED,
    "blue_glow": BLUE_GLOW,
}

class MarkdownRenderer:
    """负责将Markdown渲染为微信公众号兼容的HTML，并应用主题样式。"""
    def __init__(self, theme_name="blue"):
        self.theme = self._load_theme(theme_name)
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
                'markdown.extensions.toc': {
                    'toc_depth': '2-3',  # 仅包含二级和三级标题
                }
            },
            tab_length=2,
        )

    def set_theme(self, theme_name):
        """设置新的主题。"""
        self.theme = self._load_theme(theme_name)

    def get_available_themes(self):
        """获取所有可用主题的名称。"""
        return list(THEMES.keys())

    def _load_theme(self, theme_name):
        """加载指定主题的CSS样式。"""
        theme = THEMES.get(theme_name.lower())
        if not theme:
            print(f"Warning: Theme '{theme_name}' not found. Using default 'blue' theme.") # 如果主题不存在，则使用默认的“blue”主题并打印警告。
            theme = BLUE
        return theme

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

        # 4. 清理和修复列表
        self._process_lists(doc)

        # 5. 应用主题样式
        self._apply_theme_styles(doc, mode)

        # 6. 过滤微信不支持的标签和属性
        self._filter_unsupported_elements(doc)
 
        # 7. 返回body内的HTML内容
        return doc.body.decode_contents()
 
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

    def _process_lists(self, soup):
        """
        [核心渲染逻辑] 通过递归清理和样式化列表来增强与微信的兼容性。
        
        该函数是保证列表在微信公众号编辑器中正确显示的核心。
        它解决了多个由 Markdown 解析和微信编辑器特性共同导致的问题。
        请勿轻易修改此函数的逻辑，未来新增主题时，也无需为 ul, ol, li 单独定义样式，
        此函数会统一处理。

        主要解决的问题：
        1. 清理因 Markdown 书写中空行产生的空 `<li>` 标签。
        2. 移除 `markdown` 库为包含嵌套列表的 `<li>` 自动包裹的 `<p>` 标签，防止换行。
        3. 构建一个稳定、健壮的 `<li>` 内部结构 (`<section><span>...</span>...</section>`)，
           以抵抗微信编辑器的二次解析和样式破坏。
        """
        def style_list_items(list_tag, level=0):
            is_ordered = list_tag.name == 'ol'
            list_tag['style'] = "list-style-type: none; padding: 0; margin: 0;"
            
            item_counter = 1
            for li in list(list_tag.find_all('li', recursive=False)):
                # 递归处理嵌套列表
                for nested_list in li.find_all(['ul', 'ol'], recursive=False):
                    style_list_items(nested_list, level + 1)
                
                # 简化：移除<li>内多余的<p>包装
                if li.p and len(li.find_all(recursive=False)) == 1:
                    li.p.unwrap()
                
                # 清理：删除空的或只包含空白的<li>
                # 我们通过替换掉 &nbsp; (non-breaking space) 来确保判断的准确性
                text = li.get_text(strip=True).replace(u'\xa0', '').strip()
                if not text and not li.find('img'):
                    li.decompose()
                    continue

                # 解决复杂列表项中 markdown 库自动添加 <p> 标签导致换行的问题
                # 我们找到第一个 <p> 元素并将其解包，这样文本就不会被块级元素包围
                first_child = li.find(recursive=False)
                if first_child and first_child.name == 'p':
                    first_child.unwrap()

                # 应用缩进
                indent_size = 2  # em
                li['style'] = f"display: block; margin-bottom: 0.5em; padding-left: {level * indent_size}em;"

                # 将li的现有内容包装在一个section中，以增强微信兼容性
                content_section = soup.new_tag('section')
                # 遍历li的子元素并添加到新的section中
                for child in list(li.children):
                    content_section.append(child)

                # 手动添加项目符号或编号
                prefix_text = f"{item_counter}. " if is_ordered else "• "
                prefix_span = soup.new_tag('span')
                # 使用 non-breaking space 避免被微信编辑器压缩
                prefix_span.string = prefix_text.replace(" ", u"\u00A0")
                prefix_span['style'] = "margin-right: 0.6em;"
                
                # 将项目符号和内容都放在 section 内，以避免不必要的换行
                content_section.insert(0, prefix_span)

                # 清空li，然后用包含所有内容的新section替换
                li.clear()
                li.append(content_section)
                
                if is_ordered:
                    item_counter += 1

        # 从顶层列表开始处理
        for list_tag in soup.find_all(['ul', 'ol']):
            if not list_tag.find_parent(['ul', 'ol']):
                style_list_items(list_tag, 0)
    
    # 删除重复的 _apply_theme_styles 方法
    def _filter_unsupported_elements(self, soup):
        """
        过滤微信公众号不支持的HTML标签和属性。
        """
        # 移除 script 和 style 标签
        for s in soup(['script', 'style']):
            s.decompose()

        # 移除微信不支持的属性
        for tag in soup.find_all(True):
            if tag.name not in ['html', 'body', 'head']:
                allowed_attrs = ['style', 'src', 'href', 'alt', 'title', 'width', 'height', 'data-src', 'data-type', 'data-w', 'data-h']
                attrs = dict(tag.attrs)
                for attr, _ in attrs.items():
                    if attr not in allowed_attrs:
                        del tag[attr]

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
