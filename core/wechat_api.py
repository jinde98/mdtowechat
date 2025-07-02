import os
import requests
import time
import yaml
import logging
import json # 确保导入json模块
import hashlib
from bs4 import BeautifulSoup
from PIL import Image

class WeChatAPI:
    def __init__(self, config_path="config.yaml"):
        self.log = logging.getLogger("MdToWeChat")
        self.config_path = config_path
        self.access_token = None
        self.access_token_cache_file = "access_token.json"

        try:
            self.config = self._load_config()
        except FileNotFoundError as e:
            self.log.critical(f"Config file not found: {e}")
            raise
        except ValueError as e:
            self.log.critical(f"Config file parsing error: {e}")
            raise
            
        if not isinstance(self.config, dict):
            raise ValueError("配置文件解析失败，请检查YAML格式")
            
        self.wechat_config = self.config.get("wechat", {})
        self.app_id = self.wechat_config.get("app_id")
        self.app_secret = self.wechat_config.get("app_secret")
        self.default_author = self.config.get("DEFAULT_AUTHOR", "匿名")
        self.default_cover_media_id = self.config.get("DEFAULT_COVER_MEDIA_ID")

        if not self.app_id or not self.app_secret:
            raise ValueError("""
                WECHAT_APP_ID和WECHAT_APP_SECRET必须在config.yaml中设置
                示例格式：
                wechat:
                  app_id: your_app_id
                  app_secret: your_app_secret
            """)

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

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

    def get_thumb_media_id_and_url(self, cover_image_path):
        if not cover_image_path:
            self.log.warning("封面图路径为空, 尝试使用默认封面。")
            return self.default_cover_media_id, None
        if "mmbiz.qpic.cn" in cover_image_path:
            self.log.info(f"封面图是微信URL: {cover_image_path}，尝试查找media_id...")
            thumb_media_id = self.find_media_id_by_url(cover_image_path)
            if thumb_media_id:
                return thumb_media_id, cover_image_path
            self.log.warning(f"无法为URL {cover_image_path} 找到对应的media_id，将尝试重新上传。")
            try:
                temp_image_path = self._download_image_to_temp(cover_image_path)
                media_id, url, _ = self.add_permanent_material(temp_image_path, 'image')
                os.remove(temp_image_path)
                return media_id, url
            except Exception as e:
                self.log.error(f"处理微信封面图失败: {e}")
                return None, None
        else:
            self.log.info(f"封面图是本地文件或外部URL: {cover_image_path}，将上传为永久素材。")
            image_to_upload = cover_image_path
            if cover_image_path.startswith(('http://', 'https://')):
                try:
                    image_to_upload = self._download_image_to_temp(cover_image_path)
                except Exception as e:
                    self.log.error(f"下载封面图失败: {e}")
                    return None, None
            media_id, url, _ = self.add_permanent_material(image_to_upload, 'image')
            if image_to_upload != cover_image_path:
                os.remove(image_to_upload)
            return media_id, url

    def process_content_images(self, html_content, uploaded_images_cache):
        self.log.info("开始处理文章内容中的图片...")
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            src = img_tag.get('src')
            if not src:
                continue
            if "mmbiz.qpic.cn" in src:
                self.log.info(f"内容图片 {src} 是微信URL，跳过处理。")
                continue
            if src in uploaded_images_cache:
                self.log.info(f"内容图片 {src} 已作为封面图上传，直接使用缓存URL。")
                img_tag['src'] = uploaded_images_cache[src]
                continue
            self.log.info(f"内容图片 {src} 不是微信URL，准备上传...")
            image_path_for_upload = src
            if src.startswith(('http://', 'https://')):
                 try:
                    image_path_for_upload = self._download_image_to_temp(src)
                 except Exception as e:
                     self.log.error(f"下载内容图片失败: {src}, error: {e}")
                     continue
            new_url, error_msg = self.upload_image_for_content(image_path_for_upload)
            if image_path_for_upload != src:
                os.remove(image_path_for_upload)
            if new_url:
                self.log.info(f"内容图片上传成功，新URL: {new_url}")
                img_tag['src'] = new_url
            else:
                self.log.warning(f"内容图片 {src} 上传失败: {error_msg}，将保留原始链接。")
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

    def find_media_id_by_url(self, image_url, retries=1):
        if "mmbiz.qpic.cn" not in image_url:
            self.log.warning(f"非微信图库URL，无法查找media_id: {image_url}")
            return None

        payload = {"type": "image", "offset": 0, "count": 20}
        total_count = -1
        
        access_token = self.get_access_token()
        if not access_token:
            self.log.error("无法获取 access_token，find_media_id_by_url 操作失败")
            return None

        api_url = "https://api.weixin.qq.com/cgi-bin/material/batchget_material"

        while True:
            try:
                response = self._make_request("POST", api_url, access_token, json=payload)
                data = response.json()

                if "errcode" in data and data["errcode"] != 0:
                    self.log.error(f"获取素材列表失败: {data}")
                    return None

                if total_count == -1:
                    total_count = data.get('total_count', 0)
                    if total_count == 0:
                        self.log.warning("素材库为空，无法找到任何图片。")
                        return None

                for item in data.get('item', []):
                    if item.get('url') == image_url:
                        self.log.info(f"找到图片，media_id为: {item['media_id']}")
                        return item['media_id']

                if payload['offset'] + payload['count'] >= total_count:
                    break
                
                payload['offset'] += payload['count']

            except requests.exceptions.RequestException as e:
                error_str = str(e)
                if retries > 0 and ('40001' in error_str or '42001' in error_str or '40014' in error_str):
                    self.log.warning("Access token expired or invalid, refreshing and retrying find_media_id_by_url...")
                    access_token = self._fetch_and_cache_access_token()
                    retries -= 1
                    continue
                
                self.log.error(f"查找media_id过程中发生网络或请求错误: {e}", exc_info=True)
                return None
            except Exception as e:
                self.log.error(f"查找media_id过程中发生未知错误: {e}", exc_info=True)
                return None

        self.log.warning(f"遍历完所有素材后，未找到图片 {image_url} 对应的media_id")
        return None
