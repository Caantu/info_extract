# 信息检索与抽取系统

一个基于Python的信息检索与抽取系统，能够从新闻网站爬取文章并提供搜索和信息抽取功能。

## 功能特性

- **网络爬虫**：从BBC、Guardian、Reuters、TechCrunch等新闻网站爬取文章
- **信息检索**：基于TF-IDF和向量空间模型的文档检索系统
- **信息抽取**：从文档中自动抽取金额、日期、组织机构等结构化信息
- **交互式界面**：提供命令行交互界面进行搜索和查询

## 系统架构

项目包含三个主要模块：

1. **crawler.py** - 网络爬虫模块
2. **ir.py** - 信息检索模块
3. **ie.py** - 信息抽取模块

## 依赖要求

```
requests
beautifulsoup4
chardet
```

## 安装依赖

```bash
pip install requests beautifulsoup4 chardet
```

## 使用方法

### 1. 数据爬取

首先运行爬虫获取新闻文章：

```bash
python crawler.py
```

爬虫会：
- 从多个新闻网站爬取文章
- 将文章保存到`crawled_data/articles/`目录
- 生成元数据文件`crawled_data/metadata.csv`

### 2. 信息检索

运行信息检索系统：

```bash
python ir.py
```

系统会：
- 构建倒排索引和TF-IDF向量
- 提供交互式搜索界面
- 支持关键词搜索并返回相关文档

### 3. 信息抽取

运行信息抽取系统：

```bash
python ie.py
```

系统会：
- 从文档中抽取结构化信息
- 提供交互式查询界面
- 支持按类型查看和搜索抽取结果

## 目录结构

```
project/
├── crawler.py          # 网络爬虫
├── ir.py              # 信息检索
├── ie.py              # 信息抽取
├── crawled_data/      # 爬取数据目录
│   ├── articles/      # 文章文件
│   └── metadata.csv   # 元数据
├── index.pkl          # 检索索引文件
└── extraction_results.json  # 抽取结果
```

## 支持的信息类型

信息抽取系统支持以下信息类型：

- 金额信息（美元、英镑、欧元等）
- 百分比数据
- 日期信息
- 组织机构
- 引用内容
- 电子邮件地址
- 带单位的数值

## 使用示例

### 信息检索示例

```
请输入查询词: artificial intelligence
正在搜索: 'artificial intelligence'...

找到 5 个相关文档:

1. 相关度: 0.8521
   标题: AI Revolution in Healthcare
   日期: 2024-01-15
   匹配内容: Artificial intelligence is transforming healthcare...
```

### 信息抽取示例

```
命令说明:
  1 - 按信息类型查看
  2 - 搜索特定内容
  3 - 查看某篇文档的所有抽取信息
  4 - 显示统计信息
  5 - 人工评价抽取结果
```

## 注意事项

1. 爬虫运行时请遵守网站的robots.txt规则
2. 建议在爬虫请求间添加适当延时
3. 首次运行需要联网获取文章数据
4. 索引文件会自动保存，重启程序时可快速加载

## 开发说明

- 使用BeautifulSoup进行HTML解析
- 实现了基本的中文支持
- 包含简单的文本预处理和停用词过滤
- 支持多种新闻网站的内容提取

## 许可证

本项目仅供学习和研究使用。
