# juejinxiaoce2markdown

Python3 将掘金小册保存为本地 markdown （会处理图片）

## 功能

- 将掘金小册保存为本地 markdown 文件
- 支持处理图片并保存到本地
- 支持在线获取小册 ID 列表
- 支持配置是否覆盖已爬取的文件
- 在每个小册目录下生成 `README.md` 文件，包含小册目录
- 在主目录下生成 `README.md` 文件，包含所有小册的目录

## 使用指南

1. 安装依赖

    ```shell
    pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
    ```

2. 根据实际情况修改 `config.yml`

    ```yaml
    sessionid: "这里填写自己的sessionid" # 填写登录掘金之后 cookie 里的 sessionid
    cookie: "这里填写自己的cookie" # 填写登录掘金之后 cookie 里的 cookie
    fetch_book_ids_online: true # 是否在线获取booklet_id列表
    book_ids: [] # 这里可以留空，如果fetch_book_ids_online为true
    save_dir: "book" # 保存小册的目录，默认会在当前目录下新建一个 book 目录
    overwrite_existing: false # 是否覆盖已爬取的文件，默认不覆盖
    ```

3. 运行主程序

    ```shell
    python3 main.py
    ```

4. 爬取结果预览

    ```
    ├── book
    │   └── 深入浅出TypeScript：从基础知识到类型编程
    │       ├── 1-小册食用指南.md
    │       ├── 2-到底为什么要学习 TypeScript？.md
    │       ├── README.md
    │       └── img
    │           ├── 1
    │           │   └── 1
    │           └── 2
    │               ├── 1
    │               ├── 2
    │               ├── 3
    │               ├── 4
    │               └── 5
    ├── config.yml
    ├── main.py
    ├── requirements.txt
    └── README.md
    ```
