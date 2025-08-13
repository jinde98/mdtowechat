from bs4 import BeautifulSoup

class WeChatHTMLCleaner:
    """负责清理和修复HTML，以确保其与微信公众号编辑器的兼容性。"""

    def clean(self, soup):
        """
        对BeautifulSoup对象执行所有清理操作。
        :param soup: BeautifulSoup对象
        """
        self._process_lists(soup)
        self._filter_unsupported_elements(soup)
        return soup

    def _process_lists(self, soup):
        """
        [核心渲染逻辑] 通过递归清理和样式化列表来增强与微信的兼容性。
        """
        def style_list_items(list_tag, level=0):
            is_ordered = list_tag.name == 'ol'
            list_tag['style'] = "list-style-type: none; padding: 0; margin: 0;"
            
            item_counter = 1
            for li in list(list_tag.find_all('li', recursive=False)):
                for nested_list in li.find_all(['ul', 'ol'], recursive=False):
                    style_list_items(nested_list, level + 1)
                
                if li.p and len(li.find_all(recursive=False)) == 1:
                    li.p.unwrap()
                
                text = li.get_text(strip=True).replace(u'\xa0', '').strip()
                if not text and not li.find('img'):
                    li.decompose()
                    continue

                first_child = li.find(recursive=False)
                if first_child and first_child.name == 'p':
                    first_child.unwrap()

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
                style_list_items(list_tag, 0)

    def _filter_unsupported_elements(self, soup):
        """
        过滤微信公众号不支持的HTML标签和属性。
        """
        for s in soup(['script', 'style']):
            s.decompose()

        for tag in soup.find_all(True):
            if tag.name not in ['html', 'body', 'head']:
                allowed_attrs = ['style', 'src', 'href', 'alt', 'title', 'width', 'height', 'data-src', 'data-type', 'data-w', 'data-h']
                attrs = dict(tag.attrs)
                for attr, _ in attrs.items():
                    if attr not in allowed_attrs:
                        del tag[attr]
