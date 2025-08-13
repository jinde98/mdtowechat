import yaml
import os
import logging

class SingletonMeta(type):
    """
    一个用于创建单例的元类。
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class ConfigManager(metaclass=SingletonMeta):
    """
    一个单例类，用于管理整个应用的配置。
    """
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.log = logging.getLogger("ConfigManager")
        self.config = {}
        self.load()

    def load(self):
        """从YAML文件加载配置。"""
        try:
            if not os.path.exists(self.config_path):
                self.log.warning(f"配置文件 {self.config_path} 不存在，将使用空配置。")
                self.config = {}
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                if not isinstance(self.config, dict):
                    self.log.error("配置文件格式无效，应为YAML字典。重置为空配置。")
                    self.config = {}
            self.log.info("配置已成功加载。")
        except Exception as e:
            self.log.error(f"加载配置文件时出错: {e}", exc_info=True)
            self.config = {}
            
    def get(self, key, default=None):
        """
        获取一个配置项。支持嵌套键，使用点号分隔。
        例如: get('wechat.app_id')
        """
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def save(self, new_config_dict=None):
        """
        保存配置到YAML文件。
        :param new_config_dict: 如果提供，将用它替换当前配置。
        """
        if new_config_dict is not None and isinstance(new_config_dict, dict):
            self.config = new_config_dict
            
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            self.log.info("配置已成功保存。")
        except Exception as e:
            self.log.error(f"保存配置文件时出错: {e}", exc_info=True)

# 可以在应用启动时创建单例实例
config_manager = ConfigManager()
