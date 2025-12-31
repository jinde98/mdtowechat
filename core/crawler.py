import requests
import json
import logging
import yaml
import os

class Crawler:
    """
    网页内容抓取器。
    
    本类利用 Jina AI 提供的 Reader API (r.jina.ai) 将任意网页URL转换为干净的、
    适合阅读的 Markdown 格式内容。这避免了直接解析原始HTML的复杂性。
    """
    def __init__(self):
        """
        初始化抓取器。
        它会读取配置文件以获取 Jina API Key（如果提供的话）。
        """
        self.log = logging.getLogger("MdToWeChat.Crawler")
        self.config = self._load_config()
        
        # Jina AI Reader API的端点
        self.jina_api_url = 'https://r.jina.ai/'
        
        # 准备请求头
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        # 尝试从配置中获取Jina API Key并添加到请求头
        api_key = self.config.get('jina', {}).get('api_key')
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
            self.log.info("已找到并设置 Jina API Key。")
        else:
            self.log.info("未在配置中找到 Jina API Key。将以匿名方式访问，可能会有效率限制。")

    def _load_config(self):
        """
        一个简单的内部方法，用于加载 `config.yaml` 文件。
        """
        config_path = 'config.yaml'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                self.log.error(f"加载配置文件 '{config_path}' 时出错: {e}")
                return {}
        return {}

    def fetch(self, target_url):
        """
        使用 Jina AI Reader API 抓取指定 URL 的内容。
        
        :param target_url: 需要抓取的网页地址。
        :return: 一个元组 (content, error)。
                 如果成功，content 是 Markdown 格式的字符串，error 是 None。
                 如果失败，content 是 None，error 是错误信息的字符串。
        """
        # API 需要的请求体是包含 'url' 键的 JSON
        payload = {
            'url': target_url
        }
        
        self.log.info(f"正在通过 Jina API 抓取内容: {target_url}")
        
        try:
            # 发送 POST 请求，设置了120秒的超时
            response = requests.post(
                self.jina_api_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=120
            )
            # 如果响应状态码是 4xx 或 5xx，则会抛出 HTTPError 异常
            response.raise_for_status()
            
            self.log.info(f"成功抓取内容: {target_url}。响应长度: {len(response.text)}")
            # Jina API 成功时直接返回 Markdown 文本
            return response.text, None
            
        except requests.exceptions.RequestException as e:
            # 捕获所有 requests 相关的异常（如连接超时、DNS错误等）
            self.log.error(f"抓取内容失败: {target_url}。错误: {e}", exc_info=True)
            return None, f"网络请求失败: {e}"
