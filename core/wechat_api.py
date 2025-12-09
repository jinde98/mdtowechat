import os
import requests
import time
import logging
import json
import hashlib
from bs4 import BeautifulSoup
from PIL import Image
from .image_cache import ImageCache
from .config import ConfigManager

class WeChatAPI:
    """
    封装了与微信公众号后台API所有交互的类。
    
    主要功能包括：
    - 自动管理和缓存 `access_token`。
    - 上传图片到微信服务器（作为正文图片或永久素材）。
    - 创建图文消息草稿。
    - 统一处理图片，包括下载、格式转换、缓存和上传。
    """
    def __init__(self):
        """
        初始化微信API客户端。
        """
        self.log = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.access_token = None
        self.access_token_cache_file = "access_token.json"
        self.image_cache = ImageCache()
        self._load_config_values()

    def _load_config_values(self):
        """
        从全局配置管理器加载或重新加载微信相关的配置。
        """
        self.app_id = self.config_manager.get("wechat.app_id")
        self.app_secret = self.config_manager.get("wechat.app_secret")
        self.default_author = self.config_manager.get("wechat.default_author", "匿名")
        self.default_cover_media_id = self.config_manager.get("wechat.default_cover_media_id")

        if not self.app_id or not self.app_secret:
            self.log.warning("微信的 app_id 或 app_secret 未在 config.yaml 中配置。部分功能将不可用。")

    def reload_config(self):
        """
        提供一个外部接口，用于在配置更改后（例如，在设置对话框中）刷新实例的配置。
        """
        self.log.info("正在重新加载 WeChatAPI 的配置...")
        self.config_manager.load()
        self._load_config_values()

    def get_access_token(self):
        """
        获取一个有效的 `access_token`。
        
        这是一个健壮的获取流程：
        1. 尝试从本地缓存文件 (`access_token.json`) 加载。
        2. 检查缓存的 token 是否在有效期内。
        3. 如果缓存有效，则直接返回。
        4. 如果缓存不存在或已过期，则自动调用微信API获取新的 `access_token` 并更新缓存。
        
        :return: 一个有效的 `access_token` 字符串，或者在获取失败时返回 `None`。
        """
        cached_token, expiry_time = self._load_access_token_from_cache()
        
        # 检查缓存的 token 是否存在且未过期
        if cached_token and expiry_time > time.time():
            self.log.info("从缓存文件中成功加载了有效的 access_token。")
            self.access_token = cached_token
            return cached_token
        
        # 如果缓存无效，则从服务器获取
        if cached_token:
            self.log.info("缓存文件中的 access_token 已过期，正在重新获取...")
        else:
            self.log.info("缓存文件中没有 access_token，正在从服务器获取...")
        
        return self._fetch_and_cache_access_token()

    def _fetch_and_cache_access_token(self):
        """
        调用微信API获取新的 `access_token` 并将其缓存到本地文件。
        """
        # 确保 app_id 和 app_secret 已配置
        if not self.app_id or not self.app_secret:
            self.log.error("无法获取 access_token，因为 app_id 或 app_secret 未配置。")
            return None
            
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "access_token" in data:
                access_token = data["access_token"]
                # 微信返回的有效期是秒，默认为7200
                expires_in = data.get("expires_in", 7200)
                self._save_access_token_to_cache(access_token, expires_in)
                self.log.info("成功获取 access_token 并已更新缓存。")
                self.access_token = access_token
                return access_token
            else:
                # API调用成功，但返回了错误信息
                self.log.error(f"获取 access_token 失败，微信返回: {data}")
                return None
        except requests.exceptions.RequestException as e:
            self.log.error(f"请求 access_token 时网络出错: {e}", exc_info=True)
            return None

    def _load_access_token_from_cache(self):
        """
        从本地JSON文件中加载 `access_token` 和其过期时间。
        :return: (token, expiry_time) 或 (None, 0)
        """
        if not os.path.exists(self.access_token_cache_file):
            return None, 0
            
        try:
            with open(self.access_token_cache_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content:
                    return None, 0
                cache_data = json.loads(content)
                return cache_data.get("access_token"), cache_data.get("expiry_time", 0)
        except (json.JSONDecodeError, IOError) as e:
            self.log.error(f"加载 access_token 缓存文件失败: {e}", exc_info=True)
            return None, 0

    def _save_access_token_to_cache(self, access_token, expires_in):
        """
        将 `access_token` 和计算出的过期时间保存到本地JSON文件。
        """
        try:
            # 设置一个300秒（5分钟）的缓冲期，提前认为 token 过期，以避免临界情况
            expiry_time = time.time() + expires_in - 300
            cache_data = {"access_token": access_token, "expiry_time": expiry_time}
            with open(self.access_token_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)
            self.log.info("access_token 已保存到缓存文件，计算出的过期时间为: %s", 
                          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry_time)))
        except IOError as e:
            self.log.error(f"保存 access_token 缓存文件失败: {e}", exc_info=True)

    def _make_request(self, method, url, access_token, **kwargs):
        """
        一个统一的私有方法，用于向微信API服务器发送请求。

        它会自动处理 `access_token` 的附加、请求的发送、以及对返回结果的初步错误检查。
        """
        try:
            # 自动将 access_token 添加到 URL 的查询参数中
            params = kwargs.get('params', {})
            params['access_token'] = access_token
            kwargs['params'] = params

            response = requests.request(method, url, **kwargs)
            response.raise_for_status()  # 如果响应状态码不是 2xx，则抛出 HTTPError

            # 对于某些API调用（如删除素材），成功时响应体可能为空
            if not response.content:
                return response

            json_data = response.json()

            # 微信API的错误通常通过JSON中的 'errcode' 字段返回
            if json_data.get("errcode"):
                self.log.error(f"微信API返回错误: {json_data}")
                # 将微信的错误信息包装成一个标准的请求异常
                raise requests.exceptions.RequestException(f"微信API错误: {json_data}")

            return response

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.log.error(f"网络连接或请求超时: {e}", exc_info=True)
            raise requests.exceptions.RequestException(f"网络或请求错误: {e}")
        except json.JSONDecodeError:
            self.log.error(f"解析微信API响应的JSON时失败: {response.text}")
            raise requests.exceptions.RequestException("JSON解码失败")
        except requests.exceptions.RequestException as e:
            # 捕获由 raise_for_status() 或我们自己抛出的异常
            self.log.error(f"微信API请求异常: {e}", exc_info=True)
            raise

    def upload_image_for_content(self, image_path, retries=1):
        """
        上传图片以用于图文消息内容。
        这种方式上传的图片URL是临时的，但可用于文章内容中。
        
        :param image_path: 本地图片文件的路径。
        :param retries: 失败后的重试次数。
        :return: (url, error_message)
        """
        access_token = self.get_access_token()
        if not access_token:
            return None, "无法获取Access Token"
        url = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
        try:
            with open(image_path, 'rb') as f:
                files = {'media': f}
                response = self._make_request("POST", url, access_token, files=files)
                data = response.json()
                if "url" in data:
                    self.log.info(f"内容图片上传成功: {data['url']}")
                    return data["url"], None
                else:
                    error_msg = f"内容图片上传失败: {data}"
                    self.log.error(error_msg)
                    return None, error_msg
        except requests.exceptions.RequestException as e:
            # 捕获 access_token 失效相关的错误码，并触发重试机制
            error_str = str(e)
            if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                self.log.warning("Access Token可能已失效，正在刷新并重试...")
                self._fetch_and_cache_access_token()
                return self.upload_image_for_content(image_path, retries - 1)
            
            self.log.error(f"内容图片上传时发生未知请求异常: {e}", exc_info=True)
            return None, f"内容图片上传发生未知异常: {e}"
        except Exception as e:
            self.log.error(f"内容图片上传时发生意外错误: {e}", exc_info=True)
            return None, f"内容图片上传发生意外错误: {e}"

    def add_permanent_material(self, file_path, material_type='image', retries=1):
        """
        新增永久素材到微信后台（如图、视频、语音、缩略图）。
        封面图必须使用此接口上传。
        
        :param file_path: 本地文件的路径。
        :param material_type: 素材类型，默认为 'image'。
        :param retries: 失败后的重试次数。
        :return: (media_id, url, error_message)
        """
        access_token = self.get_access_token()
        if not access_token:
            return None, None, "无法获取Access Token"
        
        url = "https://api.weixin.qq.com/cgi-bin/material/add_material"
        params = {'type': material_type}

        try:
            with open(file_path, 'rb') as f:
                files = {'media': (os.path.basename(file_path), f)}
                
                # 视频素材需要额外的描述信息
                if material_type == 'video':
                    description = {"title": "VIDEO_TITLE", "introduction": "VIDEO_INTRODUCTION"}
                    response = self._make_request("POST", url, access_token, params=params, files=files, data={'description': json.dumps(description)})
                else:
                    response = self._make_request("POST", url, access_token, params=params, files=files)
                
                data = response.json()

                if "media_id" in data:
                    media_id = data['media_id']
                    media_url = data.get('url') # 图片和视频素材会返回url
                    self.log.info(f"永久素材上传成功。Media ID: {media_id}, URL: {media_url}")
                    return media_id, media_url, None
                else:
                    error_msg = f"新增永久素材 '{file_path}' 失败: {data}"
                    self.log.error(error_msg)
                    return None, None, error_msg

        except requests.exceptions.RequestException as e:
            # 同样实现了 access_token 失效后的自动重试
            error_str = str(e)
            if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                self.log.warning("Access Token可能已失效，正在刷新并重试...")
                self._fetch_and_cache_access_token()
                return self.add_permanent_material(file_path, material_type, retries - 1)
            
            self.log.error(f"新增永久素材时发生未知请求异常: {e}", exc_info=True)
            return None, None, f"新增永久素材发生未知异常: {e}"
        except Exception as e:
            self.log.error(f"新增永久素材时发生意外错误: {e}", exc_info=True)
            return None, None, f"新增永久素材发生意外错误: {e}"

    def create_draft(self, articles, retries=1):
        """
        创建一篇新的图文草稿。
        
        :param articles: 一个符合微信API格式的文章列表。
        :param retries: 失败后的重试次数。
        :return: (media_id, error_message)
        """
        access_token = self.get_access_token()
        if not access_token:
            return None, "无法获取Access Token"
        url = "https://api.weixin.qq.com/cgi-bin/draft/add"
        payload = {"articles": articles}
        try:
            # 确保 payload 被正确编码为 UTF-8，以支持中文字符
            response = self._make_request(
                "POST", url, access_token, 
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), 
                headers={'Content-Type': 'application/json; charset=utf-8'}
            )
            data = response.json()
            if "media_id" in data:
                self.log.info(f"草稿创建成功，Media ID: {data['media_id']}")
                return data["media_id"], None
            else:
                error_msg = f"创建草稿失败: {data.get('errmsg', '未知错误')}"
                self.log.error(error_msg)
                return None, error_msg
        except requests.exceptions.RequestException as e:
            # 同样实现了 access_token 失效后的自动重试
            error_str = str(e)
            if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                self.log.warning("Access Token可能已失效，正在刷新并重试...")
                self._fetch_and_cache_access_token()
                return self.create_draft(articles, retries - 1)
            
            self.log.error(f"创建草稿时发生未知请求异常: {e}", exc_info=True)
            return None, f"创建草稿发生未知异常: {e}"
        except Exception as e:
            self.log.error(f"创建草稿时发生意外错误: {e}", exc_info=True)
            return None, f"创建草稿发生意外错误: {e}"

    def _upload_image(self, original_url, upload_type='content'):
        """
        [核心流程] 统一的图片上传方法，封装了缓存、下载和上传的完整逻辑。
        
        :param original_url: 原始图片URL（本地路径或网络URL）。
        :param upload_type: 'content' (正文图片) 或 'permanent' (永久素材，如封面)。
        :return: (media_id, wechat_url, error_message)
        """
        if not original_url:
            return None, None, "图片URL为空"

        # 步骤 1: 检查缓存，如果图片已上传过，直接返回缓存的结果
        cached_data = self.image_cache.get(original_url)
        if cached_data:
            self.log.info(f"在缓存中找到图片，跳过上传: {original_url}")
            if upload_type == 'permanent':
                return cached_data.get('media_id'), cached_data.get('url'), None
            else: # 'content'
                return None, cached_data.get('url'), None

        # 步骤 2: 准备要上传的本地文件。如果是网络图片，先下载到临时文件。
        local_path_to_upload = original_url
        is_temp_file = False
        if original_url.startswith(('http://', 'https://')):
            try:
                local_path_to_upload = self._download_image_to_temp(original_url)
                if not local_path_to_upload:
                    raise IOError("下载或转换图片失败")
                is_temp_file = True
            except Exception as e:
                error_msg = f"下载网络图片失败: {original_url}, 错误: {e}"
                self.log.error(error_msg)
                return None, None, error_msg
        
        # 步骤 3: 根据 upload_type 执行相应的上传操作
        media_id, wechat_url, error = (None, None, None)
        if upload_type == 'permanent':
            media_id, wechat_url, error = self.add_permanent_material(local_path_to_upload, 'image')
        else: # content
            wechat_url, error = self.upload_image_for_content(local_path_to_upload)

        # 步骤 4: 如果是网络图片，上传完成后删除临时文件
        if is_temp_file and os.path.exists(local_path_to_upload):
            try:
                os.remove(local_path_to_upload)
            except OSError as e:
                self.log.error(f"删除临时图片文件失败: {local_path_to_upload}, 错误: {e}")

        # 步骤 5: 如果上传成功，将结果更新到缓存
        if not error and wechat_url:
            self.image_cache.set(original_url, {'media_id': media_id, 'url': wechat_url})
            self.log.info(f"图片上传成功并已缓存: {original_url}")
        
        return media_id, wechat_url, error

    def get_thumb_media_id_and_url(self, cover_image_path):
        """
        获取封面图的 media_id。如果未提供路径，则尝试使用配置中的默认封面ID。
        """
        if not cover_image_path:
            self.log.warning("未提供封面图路径，将尝试使用配置文件中的默认封面ID。")
            return self.default_cover_media_id, None
        
        # 封面图必须作为永久素材上传
        media_id, url, error = self._upload_image(cover_image_path, upload_type='permanent')
        if error:
            self.log.error(f"封面图上传或处理失败: {error}")
            return None, None
            
        return media_id, url

    def process_content_images(self, html_content):
        """
        遍历HTML内容，找出所有图片，将它们上传到微信服务器，并替换回src属性。
        """
        self.log.info("开始处理HTML内容中的所有图片...")
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        
        for img_tag in img_tags:
            src = img_tag.get('src')
            # 如果图片URL为空，或者是已经是微信的URL，则跳过
            if not src or "mmbiz.qpic.cn" in src:
                if src: self.log.info(f"图片 '{src}' 已是微信URL或为空，跳过处理。")
                continue

            # 调用统一的图片上传流程，上传为正文图片
            _, new_url, error = self._upload_image(src, upload_type='content')
            
            if new_url:
                self.log.info(f"图片上传并替换成功: '{src}' -> '{new_url}'")
                img_tag['src'] = new_url
            else:
                self.log.warning(f"图片 '{src}' 上传失败: {error}。将保留原始链接。")
                
        return str(soup)

    def _download_image_to_temp(self, url):
        """
        从网络URL下载图片，并统一转换为JPG格式保存到临时目录。
        """
        self.log.info(f"正在下载网络图片: {url}")
        temp_dir = 'temp_images'
        os.makedirs(temp_dir, exist_ok=True)

        # 使用URL的MD5哈希作为文件名，避免特殊字符和重复下载
        temp_file_base_name = os.path.join(temp_dir, f"{hashlib.md5(url.encode()).hexdigest()}")
        
        try:
            # 伪装成浏览器User-Agent，防止一些网站的反爬虫机制
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()

            # 先下载到不带扩展名的临时文件
            with open(temp_file_base_name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 使用Pillow进行格式识别和转换
            self.log.info("下载完成，开始使用Pillow进行格式转换...")
            with Image.open(temp_file_base_name) as img:
                # 转换为RGB模式，这是保存为JPG所必需的
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 定义最终的JPG文件名并保存
                final_jpg_path = f"{temp_file_base_name}.jpg"
                img.save(final_jpg_path, 'jpeg', quality=85) # quality参数可以平衡质量和文件大小
            
            self.log.info(f"图片已成功转换为JPG格式并保存到: {final_jpg_path}")
            return final_jpg_path

        except requests.exceptions.RequestException as e:
            self.log.error(f"下载图片时出错: {url}, 错误: {e}")
            raise
        except Exception as e:
            self.log.error(f"使用Pillow处理或转换图片时出错: {url}, 错误: {e}", exc_info=True)
            raise
        finally:
            # 清理下载的原始临时文件
            if os.path.exists(temp_file_base_name):
                try:
                    os.remove(temp_file_base_name)
                except OSError as e:
                    self.log.error(f"无法删除临时文件 {temp_file_base_name}: {e}")
