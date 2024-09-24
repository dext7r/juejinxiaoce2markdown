import logging
import os
import re
import traceback
import yaml
from urllib.request import urlretrieve
import concurrent.futures
from typing import List, Dict, Any
import requests
from tqdm import tqdm
import threading
import time

# 配置日志
def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)7s: %(message)s')
    global logger, error_logger, success_logger, all_logger
    logger = logging.getLogger(__name__)

    log_dir = '.log'
    makedirs(log_dir)
    error_log_path = os.path.join(log_dir, 'error.log')
    success_log_path = os.path.join(log_dir, 'success.log')
    all_log_path = os.path.join(log_dir, 'all.log')

    error_logger = logging.getLogger('error_logger')
    error_handler = logging.FileHandler(error_log_path)
    error_logger.addHandler(error_handler)

    success_logger = logging.getLogger('success_logger')
    success_handler = logging.FileHandler(success_log_path)
    success_logger.addHandler(success_handler)

    all_logger = logging.getLogger('all_logger')
    all_handler = logging.FileHandler(all_log_path)
    all_logger.addHandler(all_handler)

def makedirs(path: str) -> None:
    """创建目录，如果目录不存在"""
    if not os.path.exists(path):
        os.makedirs(path)

def clear_slash(s: str) -> str:
    """清除字符串中的斜杠和竖线"""
    return s.replace('\\', '').replace('/', '').replace('|', '')

class Juejinxiaoce2Markdown:
    img_pattern = re.compile(r'!\[.*?\]\((.*?)\)', re.S)
    lock = threading.Lock()  # 添加线程锁

    def __init__(self, config: Dict[str, Any]):
        logger.info(config)
        all_logger.info(config)
        pwd = os.path.dirname(os.path.abspath(__file__))
        default_save_dir = os.path.join(pwd, 'book')
        sessionid: str = config['sessionid']
        self.cookie: str = config['cookie']
        self.fetch_book_ids_online: bool = config.get('fetch_book_ids_online', False)
        self.book_ids: List[str] = config['book_ids']
        self.save_dir: str = config.get('save_dir', default_save_dir)
        self.overwrite_existing: bool = config.get('overwrite_existing', False)
        self.request_headers = {
            'cookie': f'sessionid={sessionid}; {self.cookie}',
        }
        makedirs(self.save_dir)

    def fetch_book_ids(self) -> None:
        """通过requests获取booklet_id列表"""
        url = 'https://api.juejin.cn/booklet_api/v1/booklet/bookletshelflist?aid=2608&uuid=7390948006004852278&spider=0'
        headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json',
            'cookie': self.cookie,
            'origin': 'https://juejin.cn',
            'referer': 'https://juejin.cn/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        }
        response = requests.post(url, headers=headers, json={})
        data = response.json()
        
        self.book_ids = [item['booklet_id'] for item in data['data']]

    def get_section_res(self, section_id: str) -> requests.Response:
        """获取小册章节内容"""
        url = f'https://api.juejin.cn/booklet_api/v1/section/get'
        data = {
            'section_id': str(section_id)
        }
        res = requests.post(url, headers=self.request_headers, json=data)
        time.sleep(1)  # 添加sleep反爬虫机制
        return res

    def get_book_info_res(self, book_id: str) -> requests.Response:
        """获取小册信息"""
        url = f'https://api.juejin.cn/booklet_api/v1/booklet/get'
        data = {
            'booklet_id': str(book_id)
        }
        res = requests.post(url, headers=self.request_headers, json=data)
        time.sleep(1)  # 添加sleep反爬虫机制
        return res

    @classmethod
    def save_markdown(cls, markdown_file_path: str, section_img_dir: str, markdown_relative_img_dir: str, markdown_str: str) -> None:
        """保存markdown文件并处理图片"""
        img_urls = re.findall(cls.img_pattern, markdown_str)
        for img_index, img_url in enumerate(img_urls):
            new_img_url: str = img_url.replace('\n', '')
            try:
                suffix = os.path.splitext(new_img_url)[-1]
                img_file_name = f'{img_index + 1}{suffix}'.replace('?', '')
                md_relative_img_path = os.path.join(markdown_relative_img_dir, img_file_name)
                img_save_path = os.path.join(section_img_dir, img_file_name)
                urlretrieve(new_img_url, img_save_path)
                markdown_str = markdown_str.replace(img_url, md_relative_img_path)
            except Exception as e:
                error_msg = {
                    'msg': '处理图片失败',
                    'img_url': new_img_url,
                    'e': repr(e),
                    'traceback': traceback.format_exc(),
                    'markdown_relative_img_dir': markdown_relative_img_dir
                }
                logger.error(error_msg)
                error_logger.error(error_msg)
                all_logger.error(error_msg)
        with open(markdown_file_path, 'w', encoding='utf8') as f:
            f.write(markdown_str)

    def generate_readme(self, book_save_path: str, sections: List[Dict[str, Any]]) -> None:
        """生成每个book的README.md文件"""
        readme_path = os.path.join(book_save_path, 'README.md')
        with open(readme_path, 'w', encoding='utf8') as f:
            f.write('# 目录\n\n')
            for index, section in enumerate(sections):
                section_title = clear_slash(section['title'])
                section_file = f'{index + 1}-{section_title}.md'
                f.write(f'<a href="{section_file}">{section_title}</a>\n')

    def generate_main_readme(self) -> None:
        """生成主目录的README.md文件"""
        readme_path = os.path.join(self.save_dir, 'README.md')
        with open(readme_path, 'w', encoding='utf8') as f:
            f.write('# 目录\n\n')
            for index, book_id in enumerate(self.book_ids):
                book_info_res = self.get_book_info_res(book_id)
                if book_info_res.status_code != 200 or 'data' not in book_info_res.json() or not book_info_res.json()['data']:
                    f.write(f'<a href="#" style="color: red;">小册 "{index + 1}" 正在写作中</a>\n')
                    continue
                book_info = book_info_res.json()
                book_title = clear_slash(book_info['data']['booklet']['base_info']['title'])
                f.write(f'<a href="{book_title}/README.md">{book_title}</a>\n')

    def deal_a_book(self, book_id: str) -> None:
        """处理单个小册"""
        try:
            book_info_res = self.get_book_info_res(book_id)
            if book_info_res.status_code != 200 or 'data' not in book_info_res.json() or not book_info_res.json()['data']:
                msg = f'小册 "{book_id}" 正在写作中，跳过'
                logger.info(msg)
                success_logger.info(msg)
                all_logger.info(msg)
                return
            book_info = book_info_res.json()
            book_title = clear_slash(book_info['data']['booklet']['base_info']['title'])
            book_save_path = os.path.join(self.save_dir, book_title)
            if not self.overwrite_existing and os.path.exists(book_save_path):
                msg = f'小册 "{book_title}" 已存在，跳过'
                logger.info(msg)
                success_logger.info(msg)
                all_logger.info(msg)
                return
            makedirs(book_save_path)
            sections = book_info['data']['sections']
            for index, section in enumerate(tqdm(sections, desc=f'Processing {book_title}', unit='section', colour='green')):
                section_id = section['section_id']
                section_title = clear_slash(section['title'])
                markdown_file_path = os.path.join(book_save_path, f'{index + 1}-{section_title}.md')
                section_img_dir = os.path.join(book_save_path, 'img', f'{section["id"]}')
                makedirs(section_img_dir)
                markdown_relative_img_dir = os.path.join('img', f'{section["id"]}')
                section_res = self.get_section_res(section_id)
                section_markdown = section_res.json()['data']['section']['markdown_show']
                self.save_markdown(markdown_file_path, section_img_dir, markdown_relative_img_dir, section_markdown)
            self.generate_readme(book_save_path, sections)
            msg = f'小册 "{book_title}" 处理完成'
            logger.info(msg)
            success_logger.info(msg)
            all_logger.info(msg)
        except Exception as e:
            error_msg = f'处理小册 "{book_id}" 出错: {e}'
            logger.error(error_msg)
            error_logger.error(error_msg)
            all_logger.error(error_msg)

    def main(self) -> None:
        """主函数，处理所有小册"""
        if self.fetch_book_ids_online:
            self.fetch_book_ids()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.deal_a_book, book_id) for book_id in self.book_ids]
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc='Processing books', unit='book', colour='blue'):
                try:
                    future.result()
                except Exception as e:
                    error_msg = f'处理小册出错: {e}'
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    all_logger.error(error_msg)
        self.generate_main_readme()

if __name__ == '__main__':
    setup_logging()  # 添加日志配置
    with open('config.yml', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    helper = Juejinxiaoce2Markdown(config)
    helper.main()
