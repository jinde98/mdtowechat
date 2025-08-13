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
    """负责与微信公众号API进行交互，包括获取Access Token、上传图片、创建图文草稿等。"""
    def __init__(self):
        self.log = logging.getLogger("MdToWeChat")
        self.config_manager = ConfigManager()
        self.access_token = None
        self.access_token_cache_file = "access_token.json"
        self.image_cache = ImageCache()
        self._load_config_values()

    def _load_config_values(self):
        """从ConfigManager加载或重新加载配置值。"""
        self.app_id = self.config_manager.get("wechat.app_id")
        self.app_secret = self.config_manager.get("wechat.app_secret")
        self.default_author = self.config_manager.get("wechat.default_author", "匿名")
        self.default_cover_media_id = self.config_manager.get("wechat.default_cover_media_id")

        if not self.app_id or not self.app_secret:
            self.log.warning("微信 app_id 或 app_secret 未在 config.yaml 中配置。")
            # 不再抛出异常，以便用户可以在UI中设置
            
    def reload_config(self):
        """外部调用的方法，用于在配置更改后刷新实例。"""
        self.log.info("重新加载 WeChatAPI 配置...")
        self.config_manager.load()
        self._load_config_values()

    def get_access_token(self):
        cached_token, expiry_time = self._load_access_token_from_cache()
        if cached_token and expiry_time > time.time():
            self.log.info("从缓存文件中加载 access_token")
            self.access_token = cached_token
            return cached_token
        else:
            if cached_token:
                self.log.info("缓存文件中的 access_token 已过期或无效，重新获取")
            else:
                self.log.info("缓存文件中没有 access_token，重新获取")
            return self._fetch_and_cache_access_token()

    def _fetch_and_cache_access_token(self):
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "access_token" in data:
                access_token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                self._save_access_token_to_cache(access_token, expires_in)
                self.log.info("获取 access_token 成功并保存到缓存文件")
                self.access_token = access_token
                return access_token
            else:
                self.log.error(f"获取 access_token 失败: {data}")
                return None
        except Exception as e:
            self.log.error(f"请求 access_token 出错: {e}", exc_info=True)
            return None

    def _load_access_token_from_cache(self):
        try:
            if os.path.exists(self.access_token_cache_file):
                with open(self.access_token_cache_file, "r") as f:
                    content = f.read()
                    if not content:
                        return None, 0
                    cache_data = json.loads(content)
                    token = cache_data.get("access_token")
                    expiry_time = cache_data.get("expiry_time")
                    if token and expiry_time:
                        return token, expiry_time
            return None, 0
        except Exception as e:
            self.log.error(f"加载 access_token 缓存失败: {e}", exc_info=True)
            return None, 0

    def _save_access_token_to_cache(self, access_token, expires_in):
        try:
            expiry_time = time.time() + expires_in - 300
            cache_data = {"access_token": access_token, "expiry_time": expiry_time}
            with open(self.access_token_cache_file, "w") as f:
                json.dump(cache_data, f)
            self.log.info("access_token 已保存到缓存文件，过期时间为:%s", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry_time)))
        except Exception as e:
            self.log.error(f"保存 access_token 缓存失败: {e}", exc_info=True)

    def _make_request(self, method, url, access_token, **kwargs):
        try:
            params = kwargs.get('params', {})
            params['access_token'] = access_token
            kwargs['params'] = params

            response = requests.request(method, url, **kwargs)
            response.raise_for_status()

            if not response.content:
                return response

            json_data = response.json()

            if json_data.get("errcode"):
                self.log.error(f"WeChat API Error: {json_data}")
                raise requests.exceptions.RequestException(f"WeChat API Error: {json_data}")

            return response

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.log.error(f"Request error: {e}", exc_info=True)
            raise requests.exceptions.RequestException(f"网络或请求错误: {e}")
        except json.JSONDecodeError:
            self.log.error(f"Failed to decode JSON from response: {response.text}")
            raise requests.exceptions.RequestException("JSON解码失败")
        except requests.exceptions.RequestException as e:
            self.log.error(f"Request exception: {e}", exc_info=True)
            raise

    def upload_image_for_content(self, image_path, retries=1):
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
                    self.log.info(f"Image uploaded for content: {data['url']}")
                    return data["url"], None
                else:
                    error_msg = f"Failed to upload image for content: {data}"
                    self.log.error(error_msg)
                    return None, error_msg
        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                self.log.warning(f"Access token expired or invalid, refreshing and retrying upload_image_for_content...")
                self._fetch_and_cache_access_token()
                return self.upload_image_for_content(image_path, retries - 1)
            
            self.log.error(f"Unexpected error uploading image for content: {e}", exc_info=True)
            return None, f"内容图片上传发生未知异常: {e}"
        except Exception as e:
            self.log.error(f"Unexpected error uploading image for content: {e}", exc_info=True)
            return None, f"内容图片上传发生未知异常: {e}"

    def add_permanent_material(self, file_path, material_type='image', retries=1):
        access_token = self.get_access_token()
        if not access_token:
            return None, None, "无法获取Access Token"
        
        url = "https://api.weixin.qq.com/cgi-bin/material/add_material"
        params = {'type': material_type}

        try:
            with open(file_path, 'rb') as f:
                files = {'media': (os.path.basename(file_path), f)}
                
                if material_type == 'video':
                    description = {"title": "VIDEO_TITLE", "introduction": "VIDEO_INTRODUCTION"}
                    response = self._make_request("POST", url, access_token, params=params, files=files, data={'description': json.dumps(description)})
                else:
                    response = self._make_request("POST", url, access_token, params=params, files=files)
                
                data = response.json()

                if "media_id" in data:
                    media_id = data['media_id']
                    media_url = data.get('url')
                    self.log.info(f"Permanent material added successfully. Media ID: {media_id}, URL: {media_url}")
                    return media_id, media_url, None
                else:
                    error_msg = f"Failed to add permanent material {file_path}: {data}"
                    self.log.error(error_msg)
                    return None, None, error_msg

        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                self.log.warning(f"Access token expired or invalid, refreshing and retrying add_permanent_material...")
                self._fetch_and_cache_access_token()
                return self.add_permanent_material(file_path, material_type, retries - 1)
            
            self.log.error(f"Unexpected error adding permanent material: {e}", exc_info=True)
            return None, None, f"新增永久素材发生未知异常: {e}"
        except Exception as e:
            self.log.error(f"Unexpected error adding permanent material: {e}", exc_info=True)
            return None, None, f"新增永久素材发生未知异常: {e}"

    def create_draft(self, articles, retries=1):
        access_token = self.get_access_token()
        if not access_token:
            return None, "无法获取Access Token"
        url = "https://api.weixin.qq.com/cgi-bin/draft/add"
        payload = {"articles": articles}
        try:
            response = self._make_request("POST", url, access_token, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': 'application/json; charset=utf-8'})
            data = response.json()
            if "media_id" in data:
                self.log.info(f"Draft created successfully with media_id: {data['media_id']}")
                return data["media_id"], None
            else:
                error_msg = f"Failed to create draft: {data.get('errmsg', '未知错误')}"
                self.log.error(error_msg)
                return None, error_msg
        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                self.log.warning(f"Access token expired or invalid, refreshing and retrying create_draft...")
                self._fetch_and_cache_access_token()
                return self.create_draft(articles, retries - 1)
            
            self.log.error(f"Unexpected error creating draft: {e}", exc_info=True)
            return None, f"创建草稿发生未知异常: {e}"
        except Exception as e:
            self.log.error(f"Unexpected error creating draft: {e}", exc_info=True)
            return None, f"创建草稿发生未知异常: {e}"

    def _upload_image(self, original_url, upload_type='content'):
        """
        统一的图片上传方法，处理缓存、下载和上传逻辑。
        :param original_url: 原始图片URL（本地路径或网络URL）
        :param upload_type: 'content' 或 'permanent'
        :return: (media_id, wechat_url, error_message)
        """
        if not original_url:
            return None, None, "图片URL为空"

        # 1. 检查缓存
        cached_data = self.image_cache.get(original_url)
        if cached_data:
            self.log.info(f"从缓存中找到图片: {original_url} -> {cached_data}")
            if upload_type == 'permanent':
                return cached_data.get('media_id'), cached_data.get('url'), None
            else:
                return None, cached_data.get('url'), None

        # 2. 准备要上传的本地文件路径
        local_path_to_upload = original_url
        is_temp_file = False
        if original_url.startswith(('http://', 'https://')):
            try:
                local_path_to_upload = self._download_image_to_temp(original_url)
                is_temp_file = True
            except Exception as e:
                error_msg = f"下载图片失败: {original_url}, error: {e}"
                self.log.error(error_msg)
                return None, None, error_msg
        
        # 3. 执行上传
        media_id, wechat_url, error = (None, None, None)
        if upload_type == 'permanent':
            media_id, wechat_url, error = self.add_permanent_material(local_path_to_upload, 'image')
        else: # content
            wechat_url, error = self.upload_image_for_content(local_path_to_upload)

        # 4. 清理临时文件
        if is_temp_file and os.path.exists(local_path_to_upload):
            os.remove(local_path_to_upload)

        # 5. 如果上传成功，更新缓存
        if not error and wechat_url:
            self.image_cache.set(original_url, {'media_id': media_id, 'url': wechat_url})
            self.log.info(f"图片上传成功并已缓存: {original_url} -> {wechat_url}")
        
        return media_id, wechat_url, error

    def get_thumb_media_id_and_url(self, cover_image_path):
        if not cover_image_path:
            self.log.warning("封面图路径为空, 尝试使用默认封面。")
            return self.default_cover_media_id, None
        
        media_id, url, error = self._upload_image(cover_image_path, upload_type='permanent')
        if error:
            self.log.error(f"封面图处理失败: {error}")
            return None, None
            
        return media_id, url

    def process_content_images(self, html_content):
        self.log.info("开始处理文章内容中的图片...")
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            src = img_tag.get('src')
            if not src or "mmbiz.qpic.cn" in src:
                if src: self.log.info(f"内容图片 {src} 是微信URL或为空，跳过处理。")
                continue

            _, new_url, error = self._upload_image(src, upload_type='content')
            
            if new_url:
                self.log.info(f"内容图片上传成功，新URL: {new_url}")
                img_tag['src'] = new_url
            else:
                self.log.warning(f"内容图片 {src} 上传失败: {error}，将保留原始链接。")
        return str(soup)

    def _download_image_to_temp(self, url):
        self.log.info(f"正在从URL下载图片: {url}")
        temp_dir = 'temp_images'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # 初始临时文件名，不带特定扩展名
        temp_file_path_initial = os.path.join(temp_dir, f"{hashlib.md5(url.encode()).hexdigest()}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, stream=True, headers=headers)
            response.raise_for_status()

            with open(temp_file_path_initial, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.log.info(f"图片已下载到临时文件: {temp_file_path_initial}")

            # 使用Pillow进行格式转换
            self.log.info("开始转换图片格式为JPG...")
            img = Image.open(temp_file_path_initial)
            
            # 转换为RGB模式，这是保存为JPG所必需的
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 定义最终的JPG文件名
            final_jpg_path = f"{temp_file_path_initial}.jpg"
            img.save(final_jpg_path, 'jpeg')
            self.log.info(f"图片已成功转换为JPG格式并保存到: {final_jpg_path}")

            return final_jpg_path

        except requests.exceptions.RequestException as e:
            self.log.error(f"下载图片时出错: {url}, error: {e}")
            raise
        except Exception as e:
            self.log.error(f"处理或转换图片时出错: {url}, error: {e}", exc_info=True)
            raise
        finally:
            # 清理初始的临时文件
            if os.path.exists(temp_file_path_initial):
                try:
                    os.remove(temp_file_path_initial)
                except OSError as e:
                    self.log.error(f"无法删除临时文件 {temp_file_path_initial}: {e}")
