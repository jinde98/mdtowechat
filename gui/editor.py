import os
import uuid
from PyQt5.QtWidgets import QTextEdit, QApplication
from PyQt5.QtGui import QImage, QTextCursor

class PastingImageEditor(QTextEdit):
    """
    一个自定义的QTextEdit，增加了粘贴图片时自动上传的功能。
    """
    def __init__(self, wechat_api, parent=None):
        super().__init__(parent)
        self.wechat_api = wechat_api

    def canInsertFromMimeData(self, source):
        """只接受包含图片或文本的数据。"""
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        """重写粘贴逻辑，处理图片数据。"""
        if source.hasImage():
            # 注意：为了简单起见，这里同步执行。
            # 在实际生产环境中，为避免UI冻结，应使用QThread执行网络操作。
            self.paste_image(source.imageData())
        else:
            super().insertFromMimeData(source)

    def paste_image(self, image: QImage):
        """处理图片粘贴的完整流程：保存、上传、替换。"""
        cursor = self.textCursor()
        
        # 1. 将图片保存到临时文件
        temp_dir = 'temp_images'
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        temp_path = os.path.join(temp_dir, filename)
        image.save(temp_path, "PNG")

        # 2. 在光标处插入占位符并保持选中状态，以便后续替换
        placeholder = f"![Uploading {filename}...]()"
        cursor.insertText(placeholder)
        cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(placeholder))
        
        # 立即处理UI事件，确保占位符显示出来
        QApplication.processEvents()

        # 3. 上传临时图片文件
        wechat_url, error_msg = self.wechat_api.upload_image_for_content(temp_path)
        
        # 4. 根据上传结果，用最终的Markdown链接替换占位符
        if wechat_url:
            final_markdown = f"![pasted_image]({wechat_url})"
        else:
            final_markdown = f"![Upload FAILED: {error_msg}]()"
        
        # 因为占位符仍被选中，所以这次插入会直接替换它
        cursor.insertText(final_markdown)

        # 5. 清理本地的临时文件
        try:
            os.remove(temp_path)
        except Exception as e:
            # 在后台打印错误，不打扰用户
            print(f"Error removing temp file {temp_path}: {e}")
