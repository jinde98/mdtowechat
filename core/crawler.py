import requests
import json
import logging
import yaml
import os

class Crawler:
    def __init__(self):
        self.log = logging.getLogger("MdToWeChat.Crawler")
        self.config = self._load_config()
        
        self.url = 'https://r.jina.ai/'
        self.headers = {
            'Content-Type': 'application/json'
        }
        api_key = self.config.get('jina', {}).get('api_key')
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
            self.log.info("Jina API Key found and set in headers.")
        else:
            self.log.info("No Jina API Key found in config. Proceeding without authentication.")

    def _load_config(self):
        config_path = 'config.yaml'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}

    def fetch(self, target_url):
        """
        Fetches the content of the target_url using the Jina AI reader API.
        """
        data = {
            'url': target_url
        }
        self.log.info(f"Fetching content from: {target_url}")
        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(data), timeout=120)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            self.log.info(f"Successfully fetched content for {target_url}. Response length: {len(response.text)}")
            return response.text, None
        except requests.exceptions.RequestException as e:
            self.log.error(f"Failed to fetch content from {target_url}: {e}", exc_info=True)
            return None, str(e)
