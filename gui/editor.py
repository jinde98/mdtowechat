import os, logging
import uuid
from PyQt5.QtWidgets import QTextEdit, QApplication
from PyQt5.QtGui import QImage, QTextCursor

from PyQt5.QtCore import QThread
from core.workers import ImageUploadWorker
import logging

class PastingImageEditor(QTextEdit):
    """
    一个自定义的 QTextEdit 组件，专门用于处理图片的粘贴操作。

    它重写了Qt的粘贴机制，实现了当用户从剪贴板粘贴图片时，
    能够以**异步**的方式将图片上传到微信服务器，并用返回的URL替换占位符。
    """
    def __init__(self, wechat_api, parent=None):
        super().__init__(parent)
        self.wechat_api = wechat_api
        self.log = logging.getLogger(__name__)
        # 使用一个字典来存储正在进行的上传任务，以防止线程和worker被垃圾回收
        self.upload_tasks = {}

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
        else:
            # 如果是纯文本，则执行父类的默认粘贴行为。
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
        bold_action.triggered.connect(lambda: self._format_text("**", "**"))
        
        italic_action = menu.addAction("斜体 (*I*)")
        italic_action.triggered.connect(lambda: self._format_text("*", "*"))
        
        code_action = menu.addAction("代码 (`C`)")
        code_action.triggered.connect(lambda: self._format_text("`", "`"))
        
        menu.exec_(event.globalPos())

    def _format_text(self, prefix, suffix):
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
