# JD Spider with Playwright

一个基于 Playwright 的京东搜索页与商品详情页抓取脚本。

这个项目目前可以：

- 使用本机已安装的 Microsoft Edge 打开京东
- 复用已保存的登录状态，减少重复扫码登录
- 按关键词搜索商品
- 将搜索结果卡片提取为 `JSON`
- 按批次打开商品详情页
- 为每个商品分别保存 HTML、基础信息、图片和评论

## 功能特性

- 支持两种运行模式：
  - `debug`：每一步前暂停，按回车继续
  - `normal`：自动连续执行
- 通过 `crawler_config.json` 管理可调参数
- 兼容较新的京东搜索结果卡片结构
- 为每个商品创建独立输出目录

## 运行环境

- Windows
- Python 3.10 及以上
- 本机已安装 Microsoft Edge
- Conda 或普通 Python 环境

## 安装方式

### 方式一：Conda

```powershell
conda env create -f environment.yml
conda activate jd-playwright
```

### 方式二：pip

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 项目文件说明

- `open_jingdong.py`：主脚本入口
- `crawler_config.json`：运行配置文件
- `page_sources/`：保存搜索页 HTML 与 `products.json`
- `product_details/`：保存每个商品的详情数据
- `jd_storage_state.json`：保存 Playwright 登录态

## 配置文件

项目的大部分运行参数都放在 `crawler_config.json` 中。

示例：

```json
{
  "run_mode": "normal",
  "search": {
    "default_keyword": "西安大雁塔"
  },
  "comments": {
    "max_pages": 3,
    "page_size": 10
  },
  "detail_scraping": {
    "batch_size": 2,
    "open_interval_seconds": 8,
    "page_settle_seconds": 4,
    "batch_pause_seconds": 6
  },
  "login": {
    "default_scan_wait_seconds": 15
  }
}
```

### 主要配置项

- `run_mode`
  - `normal`：自动运行
  - `debug`：每一步等待回车
- `search.default_keyword`
  - 默认搜索关键词
- `comments.max_pages`
  - 每个商品最多抓取多少页评论
- `comments.page_size`
  - 每页抓取多少条评论
- `detail_scraping.batch_size`
  - 每批处理多少个商品
- `detail_scraping.open_interval_seconds`
  - 同一批次内两个商品详情页的打开间隔
- `detail_scraping.page_settle_seconds`
  - 商品详情页打开后额外等待多久再开始提取
- `detail_scraping.batch_pause_seconds`
  - 每一批之间暂停多久
- `login.default_scan_wait_seconds`
  - `normal` 模式下，如果没有有效登录态，默认给多少秒扫码时间

## 使用方式

### 正常模式

使用配置文件中的默认关键词自动运行：

```powershell
python open_jingdong.py
```

指定关键词运行：

```powershell
python open_jingdong.py "西安交通大学"
```

显式指定为正常模式：

```powershell
python open_jingdong.py --normal "西安交通大学"
```

### 调试模式

调试模式下，每个关键步骤都会暂停：

```powershell
python open_jingdong.py --debug
python open_jingdong.py --debug "西安交通大学"
```

## 输出目录结构

### 搜索结果输出

搜索页相关文件会保存到 `page_sources/`：

- `jingdong_page.html`
- `jingdong_page_viewable.html`
- `products.json`
- `first_product_detail.html`

### 商品详情输出

每个商品都会在 `product_details/` 下生成一个独立目录：

```text
product_details/
  001_<sku>_<title>/
    detail.html
    product.json
    comments.json
    comments_error.txt
    error.txt
    images/
      01.jpg
      02.jpg
```

其中：

- `detail.html`：商品详情页源码
- `product.json`：商品基础信息与详情信息
- `comments.json`：评论数据
- `comments_error.txt`：评论抓取失败时的错误信息
- `images/`：下载的商品图片

## 登录态说明

`jd_storage_state.json` 用来保存 Playwright 的浏览器登录状态，例如：

- cookies
- localStorage
- 其他与登录会话相关的信息

这样脚本下次运行时可以直接复用登录态，减少重复扫码。

这是一个**敏感文件**，不要公开，不要提交到公共仓库。

如果登录态失效，可以：

1. 删除 `jd_storage_state.json`
2. 重新运行脚本
3. 重新扫码登录

## 注意事项

- 当前项目通过 Playwright 的 `channel="msedge"` 使用本机 Edge。
- 京东页面 DOM 结构会变化，提取逻辑可能需要跟着调整。
- 部分商品评论接口可能失败，这种情况下会写入 `comments_error.txt`。
- 这个项目更适合个人研究、测试和内部自动化场景。

## 公开仓库前的安全检查

在公开仓库前，请确认**不要公开以下内容**：

- `jd_storage_state.json`
- `page_sources/` 中的真实抓取数据
- `product_details/` 中的真实抓取数据
- 任何包含账号、会话、个人信息的文件

建议将所有抓取产物目录都加入 `.gitignore`。

## 免责声明

请在遵守京东相关服务条款、robots 规则和适用法律法规的前提下使用本项目。本仓库仅用于学习、测试和内部自动化研究。
