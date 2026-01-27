import os, logging
import uuid
from PyQt5.QtWidgets import QTextEdit, QApplication
from PyQt5.QtGui import QImage, QTextCursor, QFont

from PyQt5.QtCore import QThread
from core.workers import ImageUploadWorker
from gui.highlighter import MarkdownHighlighter
import logging

class PastingImageEditor(QTextEdit):
    """
    一个自定义的 QTextEdit 组件，专门用于处理图片的粘贴操作。

    它重写了Qt的粘贴机制，实现了当用户从剪贴板粘贴图片时，
    能够以**异步**的方式将图片上传到微信服务器，并用返回的URL替换占位符。
    
    它也是一个纯文本 Markdown 编辑器，支持语法高亮。
    """
    def __init__(self, wechat_api, parent=None):
        super().__init__(parent)
        self.wechat_api = wechat_api
        self.log = logging.getLogger(__name__)
        # 使用一个字典来存储正在进行的上传任务，以防止线程和worker被垃圾回收
        self.upload_tasks = {}
        
        # --- 纯文本编辑增强 ---
        # 1. 禁用富文本输入 (这会过滤掉粘贴时的 HTML 格式)
        self.setAcceptRichText(False)
        
        # 2. 设置等宽字体 (编程/Markdown 标配)
        font = self.font()
        font.setFamily("Consolas") 
        if font.family() != "Consolas": # Fallback
             font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        
        # 3. 应用 Markdown 语法高亮
        self.highlighter = MarkdownHighlighter(self.document())

    def canInsertFromMimeData(self, source):
        """
        重写此方法以声明本组件能处理的数据类型。
        这里我们告诉Qt，除了默认的文本数据，我们还能处理图片数据。
        """
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        """
        重写核心的粘贴逻辑。
        当粘贴事件发生时，此方法被调用。
        """
        if source.hasImage():
            # 如果剪贴板中包含图片数据，则调用我们自定义的异步图片处理流程。
            self.paste_image_async(source.imageData())
        elif source.hasText():
            # 强制纯文本粘贴，再次确保移除所有格式
            self.insertPlainText(source.text())
        else:
            # 其他情况（如文件），尝试默认处理
            super().insertFromMimeData(source)

    def paste_image_async(self, image: QImage):
        """
        以异步方式处理图片粘贴的完整流程：保存 -> 插入占位符 -> 启动后台上传。
        
        :param image: 从剪贴板获取的 QImage 对象。
        """
        cursor = self.textCursor()
        
        # 步骤 1: 将图片从内存保存为一个临时的本地文件
        temp_dir = 'temp_images'
        os.makedirs(temp_dir, exist_ok=True)
        # 使用UUID确保文件名唯一
        upload_id = uuid.uuid4().hex
        filename = f"{upload_id}.png"
        temp_path = os.path.join(temp_dir, filename)
        image.save(temp_path, "PNG")

        # 步骤 2: 在光标处插入一个带唯一ID的占位符
        placeholder = f"![正在上传 {filename}...](uploading://{upload_id})"
        cursor.insertText(placeholder)
        
        # 步骤 3: 创建并启动后台上传Worker
        thread = QThread()
        worker = ImageUploadWorker(temp_path, self.wechat_api)
        worker.moveToThread(thread)

        # 步骤 4: 连接信号和槽
        # 当worker完成时，调用 _on_image_upload_finished 槽函数
        worker.finished.connect(self._on_image_upload_finished)
        # 当线程的事件循环结束后，安全地删除worker和thread对象
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        # 关键：当线程结束后，再从任务字典中移除它，以确保在线程运行期间始终存在强引用
        thread.finished.connect(lambda: self._cleanup_upload_task(upload_id))
        # 启动worker的run方法
        thread.started.connect(worker.run)
        
        # 步骤 5: 存储线程和worker的引用，防止被垃圾回收
        self.upload_tasks[upload_id] = (thread, worker)
        
        # 步骤 6: 启动线程
        thread.start()
        self.log.info(f"已为图片 {temp_path} 启动后台上传线程。")

    def contextMenuEvent(self, event):
        """
        自定义右键菜单，添加Markdown格式化选项并确保菜单为中文。
        """
        menu = self.createStandardContextMenu()
        
        # 汉化标准菜单项
        translation_map = {
            "Undo": "撤销",
            "Redo": "重做",
            "Cut": "剪切",
            "Copy": "复制",
            "Paste": "粘贴",
            "Delete": "删除",
            "Select All": "全选"
        }
        
        for action in menu.actions():
            # 移除快捷键提示部分进行匹配
            clean_text = action.text().replace("&", "")
            for eng, chi in translation_map.items():
                if clean_text.startswith(eng):
                    action.setText(chi)
                    break

        menu.addSeparator()
        
        bold_action = menu.addAction("加粗 (**B**)")
        bold_action.triggered.connect(self.toggle_bold)
        
        italic_action = menu.addAction("斜体 (*I*)")
        italic_action.triggered.connect(self.toggle_italic)
        
        code_action = menu.addAction("代码 (`C`)")
        code_action.triggered.connect(lambda: self.format_text("`", "`"))
        
        menu.exec_(event.globalPos())

    def format_text(self, prefix, suffix):
        """
        辅助方法：包裹选中的文本。
        """
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            cursor.insertText(f"{prefix}{suffix}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix))
            self.setTextCursor(cursor)

    # --- Markdown 快捷功能 ---

    def toggle_bold(self):
        self.format_text("**", "**")

    def toggle_italic(self):
        self.format_text("*", "*")

    def insert_code_block(self):
        """
        插入代码块。
        """
        cursor = self.textCursor()
        # 检查是否在一行的开头，如果不是，先换行
        if cursor.positionInBlock() > 0:
            cursor.insertText("\n")
        
        cursor.insertText("```\n\n```")
        cursor.movePosition(QTextCursor.Up)
        self.setTextCursor(cursor)

    def insert_link(self):
        """
        插入链接 [text](url)。
        """
        self.format_text("[", "](url)")
        # 选中 'url' 以便用户直接输入
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 4) # 选中 'url)'
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 1) # 选中 'url'
        # 上面的移动逻辑有点复杂，简化为：插入后光标在 ) 前面
        # 重新实现：
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"[{text}](url)")
            # 选中 url
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 3)
            self.setTextCursor(cursor)
        else:
            cursor.insertText("[text](url)")
            # 选中 text
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 6) # 回到 [ 后
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4) # 选中 text
            self.setTextCursor(cursor)

    def insert_quote(self):
        """
        插入引用。
        """
        cursor = self.textCursor()
        # 移动到行首
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.insertText("> ")
        self.setTextCursor(cursor)

    def insert_header(self, level):
        """
        插入标题 (H1-H6)。
        """
        if not 1 <= level <= 6:
            return
            
        cursor = self.textCursor()
        cursor.beginEditBlock()
        
        # 移动到行首
        cursor.movePosition(QTextCursor.StartOfBlock)
        # 选中当前行首可能的标题标记
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        text = cursor.selectedText()
        
        import re
        # 如果已经有标题标记，先移除
        text = re.sub(r'^#+\s*', '', text)
        
        # 插入新的标题标记
        new_text = f"{'#' * level} {text}"
        cursor.insertText(new_text)
        
        cursor.endEditBlock()

    def insert_table(self, rows=3, cols=3):
        """
        插入 Markdown 表格模板。
        """
        header = "| " + " | ".join(["标题"] * cols) + " |\n"
        separator = "| " + " | ".join(["---"] * cols) + " |\n"
        row_str = "| " + " | ".join(["内容"] * cols) + " |\n"
        
        table_text = "\n" + header + separator + (row_str * rows) + "\n"
        
        cursor = self.textCursor()
        cursor.insertText(table_text)

    def toggle_word_wrap(self):
        """
        切换自动换行。
        """
        if self.lineWrapMode() == QTextEdit.NoWrap:
            self.setLineWrapMode(QTextEdit.WidgetWidth)
            return True
        else:
            self.setLineWrapMode(QTextEdit.NoWrap)
            return False

    def _on_image_upload_finished(self, success, original_path, result):
        """
        槽函数：当图片上传完成后被调用。
        
        :param success: 上传是否成功。
        :param original_path: 原始临时文件的路径。
        :param result: 如果成功，是微信返回的URL；如果失败，是错误信息。
        """
        upload_id = os.path.basename(original_path).replace('.png', '')
        self.log.info(f"图片上传任务 {upload_id} 完成。成功: {success}")
        
        # 在编辑器中查找对应的占位符
        # 我们使用之前插入的唯一ID (uploading://{upload_id}) 来定位
        placeholder_url = f"uploading://{upload_id}"
        
        # 创建一个 Document-level 的查找
        doc = self.document()
        cursor = QTextCursor(doc)
        
        # 从文档开头开始查找
        cursor = doc.find(placeholder_url, cursor)
        
        if not cursor.isNull():
            # 如果找到了占位符
            if success:
                final_markdown = f"![pasted_image]({result})"
            else:
                # 截断过长的错误信息
                error_msg_short = (result[:50] + '...') if len(result) > 50 else result
                final_markdown = f"![上传失败: {error_msg_short}]()"
            
            # 使用找到的光标替换占位符
            # 我们需要选中整个Markdown图片链接 `![...](...)`
            cursor.select(QTextCursor.LineUnderCursor) # 选中整行可能过于宽泛，但能确保选中
            # 一个更精确的方法是手动计算占位符的长度并选择它
            # 但查找并替换通常更健壮
            
            # 重新构造占位符以精确选择
            filename = os.path.basename(original_path)
            full_placeholder = f"![正在上传 {filename}...](uploading://{upload_id})"
            
            # 再次查找并精确选择
            cursor = doc.find(full_placeholder, QTextCursor(doc))
            if not cursor.isNull():
                 cursor.insertText(final_markdown)
            else:
                 self.log.warning(f"无法在文档中再次找到占位符: {full_placeholder}")
        else:
            self.log.warning(f"图片上传完成，但无法在文档中找到占位符URL: {placeholder_url}")

        # 清理本地的临时文件
        try:
            if os.path.exists(original_path):
                os.remove(original_path)
                self.log.info(f"已删除临时图片文件: {original_path}")
        except Exception as e:
            self.log.error(f"删除临时图片文件 {original_path} 时出错: {e}")
            
        # 请求线程的事件循环退出。线程将在完成当前任务后安全地停止。
        if upload_id in self.upload_tasks:
            thread, _ = self.upload_tasks[upload_id]
            thread.quit()

    def _cleanup_upload_task(self, upload_id):
        """
        槽函数：在一个上传线程完全结束后，从任务字典中安全地移除其引用。
        """
        if upload_id in self.upload_tasks:
            self.log.info(f"清理已完成的上传任务: {upload_id}")
            del self.upload_tasks[upload_id]
