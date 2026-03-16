# 📚 arXiv 每日文章推送智能体

根据关键词自动抓取 arXiv 论文，每天推送相关文章到邮箱。支持 **本地运行** 和 **GitHub Actions 云端部署** 两种方式！

---

## 🌟 功能特点

- 🔍 **智能搜索**：根据关键词文件自动搜索相关论文，支持 arXiv、Semantic Scholar、OpenAlex 多源搜索
- 🎯 **关键词过滤**：搜索后自动过滤，只保留标题/摘要中包含核心关键词的文章
- 📊 **引用排序**：按引用次数排序，优先推送高影响力文章
- 🤖 **LLM 智能筛选**：使用大模型（GPT/DeepSeek/阿里云等）判断论文与关键词的真实相关性，过滤不相关文章
- 📄 **PDF 全文读取**：自动下载并读取论文 PDF，提取全文内容
- 📝 **论文自动总结**：使用 LLM 对论文全文进行深度总结，提取关键点、研究方法、结论等
- 🗂️ **自动分组**：按主题关键词块自动分类
- 🚫 **智能去重**：自动记录已推送文章，避免重复
- ⏰ **定时推送**：支持每天定时自动运行
- 📧 **邮件推送**：支持 SMTP 邮件推送，HTML 格式美观展示
- ☁️ **云端部署**：支持 GitHub Actions 免费云端运行
- 📄 **Markdown 报告**：生成本地 Markdown 格式报告备份

---

## 🚀 快速开始（二选一）

### 方式一：GitHub Actions 云端部署（推荐 ⭐）

**零成本、免维护、自动运行！**

```bash
# 1. 在 GitHub 创建仓库（如 arxiv-daily-push）
# 2. 配置 SSH 密钥（如果尚未配置）
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub  # 复制到 GitHub Settings -> SSH keys

# 3. 推送代码（使用 SSH）
git init
git add .
git commit -m "Initial commit"
git remote add origin git@github.com:你的用户名/arxiv-daily-push.git
git push -u origin main

# 4. 在 GitHub 仓库设置 Secrets（邮箱配置）
# 5. 完成！每天自动推送论文到邮箱
```

详细部署步骤见 [GITHUB_DEPLOY.md](GITHUB_DEPLOY.md)

### 方式二：本地运行（适合测试）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置邮箱（编辑 config.yaml）
# 设置 email.enabled: true
# 填写 sender_email 和 sender_password（授权码）

# 3. 运行
python arxiv_agent.py
```

---

## 📁 文件结构

```
.
├── .github/
│   └── workflows/
│       └── arxiv_daily.yml     # GitHub Actions 工作流
├── arxiv_agent.py              # 主程序（运行入口）
├── email_sender.py             # 邮件发送模块
├── llm_client.py               # LLM 客户端（统一接口）
├── llm_filter.py               # LLM 论文筛选模块
├── paper_summarizer.py         # 论文全文总结模块
├── pdf_reader.py               # PDF 读取模块
├── scholar_searcher.py         # 多源学术搜索模块
├── scheduler.py                # 本地定时任务调度器
├── test_email.py               # 邮件配置测试工具
├── keywords.txt                # 关键词配置文件
├── config.yaml                 # 配置文件（本地使用，含敏感信息）
├── config.example.yaml         # 配置模板（可安全提交）
├── requirements.txt            # Python 依赖
├── .gitignore                  # Git 忽略文件
├── README.md                   # 本文件
├── GITHUB_DEPLOY.md            # GitHub 部署指南
├── QUICK_START.md              # 5分钟快速开始
├── run.bat                     # Windows 一键运行脚本
├── setup_windows_task.ps1      # Windows 定时任务设置脚本
├── daily_papers/               # 报告输出目录
└── paper_history.json          # 文章历史（自动创建）
```

---

## 📧 邮件配置指南

### 快速配置

编辑 `config.yaml`：

```yaml
email:
  enabled: true
  sender_email: "your_email@qq.com"
  sender_password: "your_auth_code"  # 授权码，不是登录密码！
  receiver_emails:
    - "receiver@example.com"
  smtp_host: "smtp.qq.com"
  smtp_port: 587
  use_ssl: false
  use_tls: true
```

### 测试邮件配置

```bash
python test_email.py
```

---

## ⚙️ LLM 智能筛选配置

系统支持使用大模型进行更精准的论文筛选和总结。

### 支持的 LLM 服务商

| 服务商 | model 示例 | api_url |
|--------|-----------|---------|
| 阿里云 DashScope | qwen3.5-flash, tongyi-xiaomi-analysis-pro | dashscope |
| OpenAI | gpt-3.5-turbo, gpt-4 | openai |
| DeepSeek | deepseek-chat | deepseek |
| Moonshot | moonshot-v1-8k | moonshot |
| Gemini | gemini-1.5-flash | gemini |
| Claude | claude-3-sonnet-20240229 | claude |

### 配置示例

```yaml
llm:
  enabled: true
  api_key: "your-api-key"
  model: "tongyi-xiaomi-analysis-pro"
  api_url: "dashscope"
  temperature: 0.3
  max_tokens: 2000
  min_score: 5.0      # 最低相关性分数 (0-10)
  top_n: 30           # 最多选取前N篇
  delay: 2.0          # 请求间隔（秒）
  max_retries: 3      # 失败重试次数
```

---

## 🔍 搜索源配置

```yaml
# 搜索源: multi(多源), arxiv, semantic_scholar, openalex
search_source: multi

# 排序方式: relevance(相关性), submittedDate(最新)
sort_by: submittedDate
```

---

## 📝 关键词格式

编辑 `keywords.txt` 自定义搜索关键词：

```
1. AI Agent for Biology
** AI agent **
** autonomous agent **
** bioinformatics **
...

2. Knowledge Graph Construction
** knowledge graph **
** knowledge representation **
** ontology **
...

3. Prompt Engineering
** prompt design **
** chain-of-thought **
...
```

- 支持中文和英文关键词
- 使用 `**` 包裹关键词
- 每个主题块用数字编号开头

---

## 🛠️ 命令行选项

```bash
# 执行并发送邮件
python arxiv_agent.py

# 仅生成本地报告，不发送邮件
python arxiv_agent.py --no-email

# 测试邮件配置
python test_email.py
```

---

## 📝 论文总结示例

系统会自动对论文进行深度总结，包含：

- **详细总结**：300-500字的研究背景、目的、方法、主要发现
- **关键点**：5个核心贡献
- **研究方法**：100-200字的方法描述
- **结论**：主要结论总结
- **局限性**：客观分析论文局限

---

## 🐛 故障排查

### 邮件发送失败

| 错误 | 解决方案 |
|------|----------|
| 535 认证失败 | 检查授权码是否正确 |
| 连接超时 | 尝试修改 use_ssl: false, use_tls: true |
| 邮件进垃圾箱 | 将发件人添加到通讯录 |

### LLM API 调用失败

- 检查 api_key 是否正确
- 确认模型名称是否匹配
- 检查网络连接

---

## 📋 更新日志

- **v2.0**: 新增 PDF 全文读取、论文自动总结、多源搜索功能
- **v1.2**: 新增 GitHub Actions 云端部署支持
- **v1.1**: 新增邮件推送功能
- **v1.0**: 初始版本

---

祝你使用愉快！📚
