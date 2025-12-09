import json
import os
import logging

class ImageCache:
    """
    图片URL缓存管理器。

    该类负责维护一个持久化的缓存，用于存储原始图片URL（本地文件路径或网络URL）
    与上传到微信服务器后获得的永久URL之间的映射。

    主要目的：
    1. 避免重复上传同一张图片，节省API调用次数和上传时间。
    2. 在多次编辑和发布同一篇文章时，能够快速找到已上传图片的URL。

    缓存机制：
    - 缓存以JSON文件的形式存储在本地（默认为 `image_cache.json`）。
    - 程序启动时加载缓存文件到内存。
    - 每当有新的图片成功上传并获得微信URL后，该映射关系会被添加到缓存并立即写回文件。
    """
    def __init__(self, cache_file_path='image_cache.json'):
        """
        初始化图片缓存管理器。
        :param cache_file_path: 缓存JSON文件的路径。
        """
        self.cache_file_path = cache_file_path
        # 使用 __name__ 可以让日志记录器自动继承项目的包结构，便于管理
        self.log = logging.getLogger(__name__)
        self.cache = self._load_cache()

    def _load_cache(self):
        """
        从JSON文件加载缓存到内存。
        如果文件不存在或内容损坏（非法的JSON），则返回一个空字典并记录错误。
        """
        if not os.path.exists(self.cache_file_path):
            self.log.info(f"缓存文件 '{self.cache_file_path}' 不存在，将创建一个新的缓存。")
            return {}
        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 确保加载的数据是字典类型
                if not isinstance(data, dict):
                    self.log.warning(f"缓存文件 '{self.cache_file_path}' 内容格式不正确，不是一个有效的JSON对象。将重置为空缓存。")
                    return {}
                self.log.info(f"成功从 '{self.cache_file_path}' 加载了 {len(data)} 条图片缓存记录。")
                return data
        except (json.JSONDecodeError, IOError) as e:
            self.log.error(f"加载图片缓存文件时出错: {e}。将使用空缓存。")
            return {}

    def _save_cache(self):
        """
        将内存中的当前缓存数据持久化到JSON文件。
        使用 `indent=4` 和 `ensure_ascii=False` 使JSON文件更具可读性。
        """
        try:
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=4, ensure_ascii=False)
        except IOError as e:
            self.log.error(f"保存图片缓存到 '{self.cache_file_path}' 时失败: {e}")

    def get(self, original_url):
        """
        根据原始URL从缓存中查找对应的微信URL。
        
        :param original_url: 原始图片URL（可以是本地文件路径或网络URL）。
        :return: 如果找到，返回对应的微信图片URL（字符串）；否则返回 None。
        """
        return self.cache.get(original_url)

    def set(self, original_url, wechat_url):
        """
        在缓存中添加或更新一条URL映射记录，并立即持久化到文件。
        
        :param original_url: 原始图片URL。
        :param wechat_url: 从微信服务器获取到的对应URL。
        """
        if not original_url or not wechat_url:
            self.log.warning("尝试向缓存中设置空的 original_url 或 wechat_url，操作被忽略。")
            return
            
        self.cache[original_url] = wechat_url
        self._save_cache()
        self.log.debug(f"缓存已更新: '{original_url}' -> '{wechat_url}'")

    def clear(self):
        """
        清空内存中的所有缓存记录，并同步清空缓存文件。
        这是一个危险操作，通常只在用户需要时调用。
        """
        self.cache = {}
        self._save_cache()
        self.log.info("图片缓存已被用户清空。")
