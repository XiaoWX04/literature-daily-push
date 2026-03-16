# 🚀 GitHub Actions 部署指南

将 arXiv 智能体部署到 GitHub Actions，实现云端定时自动运行并推送邮件。

---

## 📋 部署步骤

### 1. 创建 GitHub 仓库

在 GitHub 上创建一个新仓库（如 `arxiv-daily-push`）：

1. 访问 https://github.com/new
2. 填写 Repository name: `arxiv-daily-push`
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
# 或使用 RSA
ssh-add ~/.ssh/id_rsa
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
# 复制公钥内容
cat ~/.ssh/id_ed25519.pub
# 或
cat ~/.ssh/id_rsa.pub
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
git remote add origin git@github.com:你的用户名/arxiv-daily-push.git

# 如果使用 HTTPS，命令如下（不推荐）：
# git remote add origin https://github.com:你的用户名/arxiv-daily-push.git

# 推送代码
git branch -M main
git push -u origin main
```

**切换已有仓库到 SSH：**

```bash
# 查看当前远程地址
git remote -v

# 切换到 SSH
git remote set-url origin git@github.com:你的用户名/arxiv-daily-push.git

# 验证
git remote -v
# 应显示：origin  git@github.com:用户名/仓库名.git (fetch/push)
```

### 4. 配置 GitHub Secrets

进入仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**

添加以下 Secrets：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `EMAIL_ENABLED` | 是否启用邮件 | `true` |
| `EMAIL_SENDER` | 发件人邮箱 | `your_email@qq.com` |
| `EMAIL_PASSWORD` | 邮箱授权码 | `abcdefghijklmnop` |
| `EMAIL_RECEIVERS` | 收件人邮箱（多个用逗号分隔） | `email1@qq.com,email2@gmail.com` |

**可选配置**（用于非标准邮箱或自定义参数）：

| Secret 名称 | 说明 | 默认值 |
|------------|------|--------|
| `SMTP_HOST` | SMTP 服务器 | 自动检测 |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `USE_SSL` | 使用 SSL | `false` |
| `USE_TLS` | 使用 TLS | `true` |
| `DAYS_BACK` | 搜索最近几天的文章 | `30` |
| `SEARCH_SOURCE` | 搜索源 | `arxiv` |
| `SORT_BY` | 排序方式 | `submittedDate` |

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
4. 选择 `test_email: true` 测试邮件配置
5. 点击 **Run workflow**

等待几分钟后，检查：
- ✅ 工作流运行成功（绿色勾号）
- ✅ 收到测试邮件

#### 查看定时任务

工作流默认配置：
```yaml
schedule:
  - cron: '0 1 * * *'  # 每天 UTC 01:00（北京时间 09:00）
```

如需修改时间，编辑 `.github/workflows/arxiv_daily.yml`：
- UTC 时间转北京时间：**UTC + 8小时**
- 例如：UTC 01:00 = 北京时间 09:00

### 7. 查看运行结果

#### 方式一：GitHub Actions 日志

1. 进入仓库 **Actions** 标签页
2. 点击最新的工作流运行记录
3. 查看每个步骤的日志输出

#### 方式二：邮件接收

- 每次运行成功后，自动发送邮件到配置的收件箱

#### 方式三：Artifacts 下载

1. 工作流运行完成后
2. 进入该次运行详情页
3. 页面底部 **Artifacts** 区域
4. 下载 `daily-papers-xxx` 文件（包含 Markdown 报告）

---

## 🌟 新增功能说明

### PDF 全文读取与总结

系统现在支持：
- 自动下载论文 PDF
- 提取全文文本内容
- 使用 LLM 生成论文总结（关键点、研究方法、结论、局限性）

### LLM 智能筛选

支持多个 LLM 服务商：
- 阿里云 DashScope (qwen3.5-flash, tongyi-xiaomi-analysis-pro)
- OpenAI (GPT-3.5, GPT-4)
- DeepSeek (deepseek-chat)
- Moonshot (Kimi)
- Google Gemini
- Anthropic Claude

### 多源搜索

支持多个学术搜索源：
- **multi**: 多源合并（推荐）
- **arxiv**: 官方 arXiv
- **semantic_scholar**: Semantic Scholar
- **openalex**: OpenAlex

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
EMAIL_RECEIVERS: your_qq@qq.com,your_gmail@gmail.com,your_163@163.com
```

### 自定义搜索参数

添加 Secrets：
- `DAYS_BACK`: 搜索最近几天的文章（默认30天）
- `SEARCH_SOURCE`: 搜索源 (multi/arxiv/semantic_scholar/openalex)
- `SORT_BY`: 排序方式 (submittedDate/relevance)

### 启用/禁用邮件

设置 `EMAIL_ENABLED`：
- `true` - 启用邮件推送
- `false` - 禁用邮件，仅保留 Artifacts

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
├── scholar_searcher.py         # 多源学术搜索模块
├── keywords.txt                # 关键词配置
├── config.yaml                 # 基础配置（本地使用）
├── config.example.yaml         # 配置模板
├── requirements.txt            # Python 依赖
├── paper_history.json          # 文章历史（自动创建，用于去重）
└── daily_papers/               # 报告输出目录
    └── arxiv_papers_YYYY-MM-DD.md
```

---

## 🐛 故障排查

### SSH 连接问题

**问题：** `git push` 失败，提示权限不足

**解决：**
```bash
# 检查 SSH 连接
ssh -T git@github.com

# 如果失败，检查：
# 1. 是否已添加公钥到 GitHub
# 2. SSH Agent 是否运行
# 3. 私钥是否已添加

# 重新添加私钥
ssh-add ~/.ssh/id_ed25519
```

### 工作流运行失败

**问题：** Actions 页面显示红色 ❌

**解决：**
1. 点击失败的运行记录
2. 查看具体步骤的错误日志
3. 常见问题：
   - Secrets 未配置或配置错误 → 检查 Settings → Secrets
   - 授权码错误 → 重新获取邮箱授权码
   - 关键词文件不存在 → 确保 `keywords.txt` 已提交到仓库

### 邮件发送失败

**问题：** 工作流成功但收不到邮件

**解决：**
1. 检查垃圾邮件文件夹
2. 确认 `EMAIL_ENABLED` 设置为 `true`
3. 确认 `EMAIL_PASSWORD` 是授权码，不是登录密码
4. 使用 `test_email: true` 手动触发测试

### 去重失效（重复推送相同文章）

**原因：** GitHub Actions 每次运行是全新的环境

**解决：**
- 代码已配置自动提交 `paper_history.json` 到仓库
- 确保仓库有写权限（默认有）
- 检查是否有 `.gitignore` 排除了 `paper_history.json`

---

## 💡 最佳实践

1. **使用 SSH 而非 HTTPS**：免密码、更安全
2. **使用私有仓库**：保护邮箱地址等敏感信息
3. **定期更新关键词**：编辑 `keywords.txt` 并 push 到仓库
4. **监控运行状态**：GitHub 会自动邮件通知工作流失败
5. **保留历史记录**：`paper_history.json` 会随代码一起提交，保留完整推送历史

---

## 📄 许可证

MIT License - 可自由使用和修改
