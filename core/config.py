import yaml
import os
import logging

class SingletonMeta(type):
    """
    一个标准的单例模式元类。
    它确保一个类在整个应用程序生命周期中只有一个实例。
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # 如果类的实例尚不存在，则创建它
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        # 总是返回已存在的唯一实例
        return cls._instances[cls]

class ConfigManager(metaclass=SingletonMeta):
    """
    配置管理器 (ConfigManager)。
    
    这是一个单例类，负责整个应用程序的配置管理。
    使用单例模式可以确保在任何地方访问到的配置都是同一个实例，避免数据不一致。
    它负责加载、获取和保存 `config.yaml` 文件中的配置项。
    """
    def __init__(self, config_path="config.yaml"):
        """
        初始化配置管理器。
        :param config_path: 配置文件的路径。
        """
        self.config_path = config_path
        self.log = logging.getLogger("MdToWeChat.ConfigManager")
        self.config = {}
        self.load()

    def load(self):
        """
        从 YAML 文件加载配置。
        如果文件不存在或格式不正确，会记录警告/错误，并使用一个空的配置字典。
        """
        try:
            if not os.path.exists(self.config_path):
                self.log.warning(f"配置文件 '{self.config_path}' 不存在。将使用默认或空配置。")
                self.config = {}
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                # 确保加载的是一个字典，防止配置文件格式错误导致程序崩溃
                if not isinstance(self.config, dict):
                    self.log.error(f"配置文件 '{self.config_path}' 格式无效，根节点应为字典。已重置为空配置。")
                    self.config = {}
            self.log.info("配置已成功加载。")
        except Exception as e:
            self.log.error(f"加载配置文件时发生严重错误: {e}", exc_info=True)
            self.config = {}
            
    def get(self, key, default=None):
        """
        安全地获取一个配置项。支持使用点号（.）进行嵌套访问。
        
        示例:
        get('wechat.app_id')  # 等同于 self.config['wechat']['app_id']
        
        :param key: 配置项的键，如 'wechat.app_id'。
        :param default: 如果找不到键，返回的默认值。
        :return: 配置值或默认值。
        """
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            # 如果中间任何一个键不存在或值不是字典，则安全地返回默认值
            return default

    def save(self, new_config_dict=None):
        """
        将当前配置保存到 YAML 文件。
        
        :param new_config_dict: (可选) 如果提供一个新字典，它将完全替换当前的配置。
        """
        if new_config_dict is not None and isinstance(new_config_dict, dict):
            self.config = new_config_dict
            
        try:
            # 使用 'w' 模式写入文件，会覆盖旧文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                # `allow_unicode=True` 支持中文字符
                # `default_flow_style=False` 使其更易读（块样式而不是内联样式）
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            self.log.info(f"配置已成功保存到 '{self.config_path}'。")
        except Exception as e:
            self.log.error(f"保存配置文件时出错: {e}", exc_info=True)

# 在模块加载时就创建 ConfigManager 的单例实例。
# 之后，其他任何模块都可以通过 `from core.config import config_manager` 来获取这个唯一的实例。
config_manager = ConfigManager()
