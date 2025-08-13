import json
import os
import logging

class ImageCache:
    """
    一个简单的基于JSON文件的缓存，用于存储原始图片URL到微信图片URL的映射。
    """
    def __init__(self, cache_file_path='image_cache.json'):
        """
        初始化图片缓存。
        :param cache_file_path: 缓存文件的路径。
        """
        self.cache_file_path = cache_file_path
        self.log = logging.getLogger("ImageCache")
        self.cache = self._load_cache()

    def _load_cache(self):
        """从文件加载缓存。如果文件不存在，则返回一个空字典。"""
        if not os.path.exists(self.cache_file_path):
            return {}
        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.log.error(f"加载图片缓存文件失败: {e}, 将创建一个新的缓存。")
            return {}

    def _save_cache(self):
        """将当前缓存保存到文件。"""
        try:
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=4, ensure_ascii=False)
        except IOError as e:
            self.log.error(f"保存图片缓存文件失败: {e}")

    def get(self, original_url):
        """
        根据原始URL从缓存中获取微信URL。
        :param original_url: 原始图片URL（本地路径或网络URL）。
        :return: 对应的微信图片URL，如果未找到则返回None。
        """
        return self.cache.get(original_url)

    def set(self, original_url, wechat_url):
        """
        将一个新的URL映射添加到缓存中，并立即保存。
        :param original_url: 原始图片URL。
        :param wechat_url: 对应的微信图片URL。
        """
        self.cache[original_url] = wechat_url
        self._save_cache()

    def clear(self):
        """清空整个缓存。"""
        self.cache = {}
        self._save_cache()
        self.log.info("图片缓存已清空。")
