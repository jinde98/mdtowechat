import json
from openai import OpenAI
import logging
import yaml
import os

class LLMProcessor:
    def __init__(self):
        self.log = logging.getLogger("MdToWeChat.LLM")
        self.config = self._load_config()
        
        llm_config = self.config.get('llm', {})
        self.api_key = llm_config.get('api_key')
        self.model = llm_config.get('model')
        self.base_url = llm_config.get('base_url')

        if not all([self.api_key, self.model, self.base_url]):
            raise ValueError("LLM configuration (api_key, model, base_url) is not fully set in config.yaml")

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _load_config(self):
        config_path = 'config.yaml'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def process_content(self, content, system_prompt):
        """
        Processes the given content using the LLM.
        """
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
