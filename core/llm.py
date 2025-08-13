import json
from openai import OpenAI
import logging
from .config import ConfigManager

class LLMProcessor:
    def __init__(self):
        self.log = logging.getLogger("MdToWeChat.LLM")
        self.config_manager = ConfigManager()
        self._load_config_values()
        self._initialize_client()

    def _load_config_values(self):
        """从ConfigManager加载或重新加载配置值。"""
        self.api_key = self.config_manager.get("llm.api_key")
        self.model = self.config_manager.get("llm.model")
        self.base_url = self.config_manager.get("llm.base_url")

    def _initialize_client(self):
        """根据当前配置初始化OpenAI客户端。"""
        if not all([self.api_key, self.model, self.base_url]):
            self.log.warning("LLM configuration (api_key, model, base_url) is not fully set in config.yaml")
            self.client = None
        else:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def reload_config(self):
        """外部调用的方法，用于在配置更改后刷新实例。"""
        self.log.info("重新加载 LLMProcessor 配置...")
        self.config_manager.load()
        self._load_config_values()
        self._initialize_client()

    def process_content(self, content, system_prompt):
        """
        Processes the given content using the LLM.
        """
        if not self.client:
            return None, "LLM客户端未初始化。请检查config.yaml中的配置。"
            
        self.log.info(f"Processing content with LLM model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                timeout=180
            )
            processed_content = response.choices[0].message.content
            self.log.info("Successfully processed content with LLM.")
            return processed_content, None
        except Exception as e:
            self.log.error(f"Failed to process content with LLM: {e}", exc_info=True)
            return None, str(e)
