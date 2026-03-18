# 🚀 GitHub Actions 部署指南

将学术论文智能体部署到 GitHub Actions，实现云端定时自动运行并推送邮件。

---

## 📋 部署步骤

### 1. 创建 GitHub 仓库

在 GitHub 上创建一个新仓库（如 `literature-daily-push`）：

1. 访问 https://github.com/new
2. 填写 Repository name: `literature-daily-push`
3. 选择 **Private**（推荐，保护邮箱隐私）
4. **不要勾选** "Initialize this repository with a README"
5. 点击 **Create repository**

### 2. 配置 SSH 密钥（推荐）

SSH 方式比 HTTPS 更安全，且推送时无需输入密码。

#### 2.1 检查现有 SSH 密钥

```bash
ls ~/.ssh/
# 查看是否有 id_rsa.pub 或 id_ed25519.pub 文件
```

#### 2.2 生成新的 SSH 密钥（如果没有）

```bash
# 使用 Ed25519 算法（推荐，更安全）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 或使用传统 RSA 算法
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 按提示操作，可直接回车使用默认路径
```

#### 2.3 添加 SSH 密钥到 SSH Agent

**Windows (Git Bash):**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

**Mac:**
```bash
eval "$(ssh-agent -s)"
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

**Linux:**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

#### 2.4 复制公钥到 GitHub

```bash
cat ~/.ssh/id_ed25519.pub
```

复制输出的内容，然后：
1. 登录 GitHub
2. 点击头像 → **Settings**
3. 左侧菜单 → **SSH and GPG keys**
4. 点击 **New SSH key**
5. Title: 随意填写（如 "My Laptop"）
6. Key: 粘贴刚才复制的公钥
7. 点击 **Add SSH key**

#### 2.5 测试 SSH 连接

```bash
ssh -T git@github.com
```

看到以下信息即成功：
```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

### 3. 推送代码到仓库

在项目目录中执行：

```bash
# 初始化 Git 仓库（如果尚未初始化）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 添加远程仓库（使用 SSH 地址）
git remote add origin git@github.com:你的用户名/literature-daily-push.git

# 推送代码
git branch -M main
git push -u origin main
```

**切换已有仓库到 SSH：**

```bash
git remote set-url origin git@github.com:你的用户名/literature-daily-push.git
```

### 4. 配置 GitHub Secrets

进入仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**

#### 必需配置

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `EMAIL_ENABLED` | 是否启用邮件 | `true` |
| `EMAIL_SENDER` | 发件人邮箱 | `your_email@qq.com` |
| `EMAIL_PASSWORD` | 邮箱授权码 | `abcdefghijklmnop` |
| `EMAIL_RECEIVERS` | 收件人邮箱（多个用逗号分隔） | `email1@qq.com,email2@gmail.com` |

#### LLM 配置（推荐）

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `LLM_ENABLED` | 是否启用 LLM 筛选 | `true` |
| `LLM_API_KEY` | LLM API Key | `sk-xxx` |
| `LLM_MODEL` | 模型名称 | `glm-5` |
| `LLM_API_URL` | 服务商 | `dashscope` |

#### 搜索源配置（可选）

| Secret 名称 | 说明 | 默认值 |
|------------|------|--------|
| `SEARCH_SOURCE` | 搜索源 | `multi` |
| `DAYS_BACK` | 搜索最近几天的文章 | `30` |
| `SORT_BY` | 排序方式 | `relevance` |
| `OPENALEX_EMAIL` | OpenAlex 邮箱 | - |
| `PUBMED_EMAIL` | PubMed 邮箱 | - |
| `PUBMED_API_KEY` | PubMed API Key | - |

### 5. 授权码获取方法

#### QQ邮箱

1. 登录 [QQ邮箱网页版](https://mail.qq.com)
2. 点击「设置」→「账户」
3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」
4. 开启「IMAP/SMTP服务」
5. 按提示发送短信，获得 **16位授权码**

#### 163邮箱

1. 登录 [163邮箱](https://mail.163.com)
2. 点击「设置」→「POP3/SMTP/IMAP」
3. 开启「IMAP/SMTP服务」
4. 获取 **授权码**

#### Gmail

1. 登录 Google 账户
2. 安全性 → 两步验证（先开启）
3. 应用专用密码 → 生成密码
4. 复制 **16位应用专用密码**

### 6. 验证部署

#### 手动触发测试

1. 进入仓库 **Actions** 标签页
2. 选择 **arXiv Daily Paper Push** 工作流
3. 点击 **Run workflow** 下拉菜单
4. 点击 **Run workflow**

等待几分钟后，检查：
- ✅ 工作流运行成功（绿色勾号）
- ✅ 收到邮件

#### 查看定时任务

工作流默认配置：
```yaml
schedule:
  - cron: '0 1 * * *'  # 每天 UTC 01:00（北京时间 09:00）
```

如需修改时间，编辑 `.github/workflows/arxiv_daily.yml`

### 7. 查看运行结果

#### 方式一：GitHub Actions 日志

1. 进入仓库 **Actions** 标签页
2. 点击最新的工作流运行记录
3. 查看每个步骤的日志输出

#### 方式二：邮件接收

每次运行成功后，自动发送邮件到配置的收件箱

#### 方式三：Artifacts 下载

1. 工作流运行完成后
2. 进入该次运行详情页
3. 页面底部 **Artifacts** 区域
4. 下载 `daily-papers-xxx` 文件

---

## 🔍 搜索源说明

| 搜索源 | Secret 值 | 说明 |
|--------|----------|------|
| 多源合并 | `multi` | 同时搜索所有源（推荐） |
| arXiv | `arxiv` | 物理、数学、计算机科学 |
| bioRxiv | `biorxiv` | 生物医学预印本 |
| OpenAlex | `openalex` | 综合性学术搜索 |
| PubMed | `pubmed` | 生物医学权威数据库 |

---

## 🤖 LLM 服务商配置

| 服务商 | `LLM_API_URL` | `LLM_MODEL` 示例 |
|--------|---------------|------------------|
| 智谱 AI | `zhipu` | glm-5, glm-4 |
| 阿里云 | `dashscope` | qwen3.5-flash |
| DeepSeek | `deepseek` | deepseek-chat |
| OpenAI | `openai` | gpt-4 |
| Moonshot | `moonshot` | moonshot-v1-8k |

---

## 🔧 高级配置

### 自定义定时规则

编辑 `.github/workflows/arxiv_daily.yml`：

```yaml
# 每天北京时间 8:00、12:00、18:00 运行
schedule:
  - cron: '0 0 * * *'   # UTC 00:00 = 北京时间 08:00
  - cron: '0 4 * * *'   # UTC 04:00 = 北京时间 12:00
  - cron: '0 10 * * *'  # UTC 10:00 = 北京时间 18:00
```

[cron 表达式在线工具](https://crontab.guru/)

### 多邮箱推送

在 `EMAIL_RECEIVERS` 中添加多个邮箱，用逗号分隔：

```
EMAIL_RECEIVERS: your_qq@qq.com,your_gmail@gmail.com
```

---

## 📁 仓库文件说明

```
.
├── .github/
│   └── workflows/
│       └── arxiv_daily.yml    # GitHub Actions 工作流
├── arxiv_agent.py              # 主程序
├── email_sender.py             # 邮件发送模块
├── llm_client.py               # LLM 客户端（统一接口）
├── llm_filter.py               # LLM 论文筛选模块
├── paper_summarizer.py         # 论文全文总结模块
├── pdf_reader.py               # PDF 读取模块
├── multi_searcher.py           # 多源学术搜索模块（arXiv/bioRxiv/OpenAlex/PubMed）
├── keywords.txt                # 关键词配置
├── config.yaml                 # 基础配置（本地使用）
├── config.example.yaml         # 配置模板
├── requirements.txt            # Python 依赖
├── paper_history.json          # 文章历史（自动创建，用于去重）
└── daily_papers/               # 报告输出目录
```

---

## 🐛 故障排查

### SSH 连接问题

```bash
# 检查 SSH 连接
ssh -T git@github.com

# 如果失败，重新添加私钥
ssh-add ~/.ssh/id_ed25519
```

### 工作流运行失败

1. 点击失败的运行记录
2. 查看具体步骤的错误日志
3. 常见问题：
   - Secrets 未配置或配置错误 → 检查 Settings → Secrets
   - 授权码错误 → 重新获取邮箱授权码
   - 关键词文件不存在 → 确保 `keywords.txt` 已提交

### 邮件发送失败

1. 检查垃圾邮件文件夹
2. 确认 `EMAIL_ENABLED` 设置为 `true`
3. 确认 `EMAIL_PASSWORD` 是授权码，不是登录密码

### LLM 调用失败

1. 检查 `LLM_API_KEY` 是否正确
2. 确认 `LLM_MODEL` 匹配服务商
3. 检查 `LLM_API_URL` 是否正确

---

## 💡 最佳实践

1. **使用 SSH 而非 HTTPS**：免密码、更安全
2. **使用私有仓库**：保护邮箱地址等敏感信息
3. **定期更新关键词**：编辑 `keywords.txt` 并 push 到仓库
4. **监控运行状态**：GitHub 会自动邮件通知工作流失败
5. **配置 PubMed API Key**：提高请求限制（每秒 10 次而非 3 次）

---

## 📄 许可证

MIT License - 可自由使用和修改
