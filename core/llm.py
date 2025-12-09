import json
from openai import OpenAI
import logging
from .config import ConfigManager

class LLMProcessor:
    """
    大语言模型（LLM）处理器。

    该类封装了与 OpenAI 兼容的 API 的所有交互。它负责：
    1. 从全局配置 (`ConfigManager`) 中读取 API Key、模型名称和 API Base URL。
    2. 基于配置初始化 `openai` 客户端。
    3. 提供一个统一的方法 `process_content` 来调用 LLM 进行文本处理。
    4. 支持在运行时重新加载配置。
    """
    def __init__(self):
        """
        初始化LLM处理器。
        """
        self.log = logging.getLogger(__name__)
        # 从 core.config 获取全局唯一的配置管理器实例
        self.config_manager = ConfigManager()
        # 加载配置并初始化客户端
        self._load_config_values()
        self._initialize_client()

    def _load_config_values(self):
        """
        从 ConfigManager 加载或重新加载 LLM 相关的配置值到实例属性。
        """
        self.api_key = self.config_manager.get("llm.api_key")
        self.model = self.config_manager.get("llm.model")
        # base_url 允许用户配置使用自定义的或第三方的 OpenAI 兼容 API
        self.base_url = self.config_manager.get("llm.base_url")

    def _initialize_client(self):
        """
        根据当前加载的配置初始化 OpenAI 客户端。
        如果关键配置（API Key, Model, Base URL）不完整，则客户端将为 None。
        """
        if not all([self.api_key, self.model, self.base_url]):
            self.log.warning("LLM 的配置（api_key, model, base_url）在 config.yaml 中不完整。LLM 功能将不可用。")
            self.client = None
        else:
            try:
                self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
                self.log.info(f"OpenAI 客户端已成功初始化。模型: {self.model}, Base URL: {self.base_url}")
            except Exception as e:
                self.log.error(f"初始化 OpenAI 客户端时失败: {e}", exc_info=True)
                self.client = None

    def reload_config(self):
        """
        提供一个从外部调用的接口，用于在配置更改后（例如，在设置对话框中保存了新配置）
        重新加载配置并重新初始化客户端。
        """
        self.log.info("正在重新加载 LLMProcessor 的配置...")
        self.config_manager.load()  # 确保配置管理器也从文件中重新加载
        self._load_config_values()
        self._initialize_client()

    def process_content(self, content, system_prompt):
        """
        使用配置好的大语言模型处理输入的内容。
        
        :param content: 需要处理的用户内容（例如，从网页抓取的文章）。
        :param system_prompt: 给模型的系统级指令，用于设定其角色和行为。
        :return: 一个元组 (processed_content, error)。
                 成功时，processed_content 是模型返回的文本，error 是 None。
                 失败时，processed_content 是 None，error 是错误信息的字符串。
        """
        if not self.client:
            return None, "LLM客户端未初始化。请检查 config.yaml 中的配置是否完整且正确。"
            
        self.log.info(f"正在使用LLM模型 '{self.model}' 处理内容...")
        try:
            # 调用 OpenAI 的 chat completions API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                timeout=180  # 设置一个较长的超时时间（3分钟）以应对可能的慢响应
            )
            
            # 提取模型返回的核心内容
            processed_content = response.choices[0].message.content
            self.log.info("LLM内容处理成功。")
            return processed_content, None
            
        except Exception as e:
            # 捕获所有可能的API异常（如网络错误、认证失败、速率限制等）
            self.log.error(f"调用LLM时发生错误: {e}", exc_info=True)
            return None, f"LLM API调用失败: {e}"
