# Web Content Extraction & Conversion Tool

一个强大的网页内容提取与转换工具，能够自动获取指定文章链接（如 X.com 推文、技术博客等）的完整内容，包括正文文本、图片资源、超链接等元素，并将其转换为结构化的 Markdown 文档。

## ✨ 核心功能

1.  **智能抓取**: 利用 Playwright 模拟浏览器行为，完美支持动态加载页面（SPA），如 Twitter/X.com。
2.  **精准提取**: 基于 Readability 算法智能识别文章主体，自动去除广告、导航栏等无关元素。
3.  **资源本地化**: 自动下载文章中的图片资源到本地 `assets` 目录，并更新 Markdown 中的引用路径。
4.  **Markdown 转换**: 生成符合 GitHub Flavored Markdown (GFM) 标准的文档，保留标题层级、代码块、引用等格式。
5.  **格式校验与优化**: 自动修复相对路径，优化图片链接，确保文档结构完整。
6.  **健壮性**: 内置重试机制与详细日志记录，有效处理网络异常与解析错误。

## 🚀 快速开始

### 前置要求

*   Python 3.8+
*   Node.js (可选，仅用于某些特定插件)
*   Playwright 浏览器内核

### 安装

1.  克隆仓库：
    ```bash
    git clone https://github.com/your-username/web-content-extractor.git
    cd web-content-extractor
    ```

2.  创建虚拟环境并安装依赖：
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    playwright install chromium
    ```

### 使用方法

#### 方式一：使用 Makefile (推荐)

该项目提供了 `Makefile` 以简化常用操作。

*   **安装依赖**:
    ```bash
    make install
    ```

*   **运行工具**:
    ```bash
    # 使用默认 URL 运行
    make run

    # 指定 URL 运行
    make run URL=https://example.com
    ```

*   **运行测试**:
    ```bash
    make test
    ```

*   **清理输出**:
    ```bash
    make clean
    ```

*   **查看帮助**:
    ```bash
    make help
    ```

#### 方式二：手动运行

```bash
python main.py https://x.com/koylanai/status/2025286163641118915 --output output_dir
```

### 参数说明

*   `url`: 目标网页链接 (必填)
*   `--output`, `-o`: 输出目录 (默认为 `output`)
*   `--debug`: 开启调试模式，输出详细日志

## 📂 项目结构

```text
.
├── main.py                 # 程序入口
├── requirements.txt        # 依赖列表
├── src/
│   ├── fetcher.py          # 网页抓取模块 (Playwright)
│   ├── parser.py           # 内容解析模块 (Readability)
│   ├── converter.py        # Markdown 转换模块
│   ├── asset_manager.py    # 资源下载管理模块
│   └── logger.py           # 日志模块
└── output/                 # 默认输出目录
    ├── assets/             # 图片资源
    └── article.md          # 生成的 Markdown 文档
```

## 🛠️ 技术栈

*   **Python**: 核心开发语言
*   **Playwright**: 动态网页抓取
*   **Readability-lxml**: 文章内容提取
*   **BeautifulSoup4**: HTML 解析与清洗
*   **Markdownify**: HTML 转 Markdown
*   **Requests**: 静态资源下载

## 📝 License

MIT License
