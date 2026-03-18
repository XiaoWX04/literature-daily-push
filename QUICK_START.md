# 🚀 快速开始指南

选择适合你的部署方式：

---

## 方式一：GitHub Actions 云端部署（推荐 ⭐）

**优点**：免费、稳定、零维护、自动运行

### 5分钟快速部署

#### 1. 创建 GitHub 仓库

在 GitHub 网页上创建一个新的空仓库（如 `literature-daily-push`），**不要**初始化 README。

#### 2. 推送代码到仓库

```bash
# 在项目目录中执行
git init
git add .
git commit -m "Initial commit"

# 使用 SSH 地址（推荐）
git remote add origin git@github.com:你的用户名/literature-daily-push.git

# 或者使用 HTTPS
# git remote add origin https://github.com/你的用户名/literature-daily-push.git

git branch -M main
git push -u origin main
```

#### 3. 配置 Secrets

进入仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | 填写内容 |
|--------|----------|
| `EMAIL_ENABLED` | `true` |
| `EMAIL_SENDER` | 你的QQ邮箱 |
| `EMAIL_PASSWORD` | QQ邮箱16位授权码 |
| `EMAIL_RECEIVERS` | 接收推送的邮箱 |

#### 4. 手动测试

- 进入 Actions 页面
- 点击 "Run workflow"
- 点击 Run

#### 5. 完成！

每天北京时间 09:00 自动推送论文到邮箱

详细部署文档：[GITHUB_DEPLOY.md](GITHUB_DEPLOY.md)

---

## 方式二：本地运行（适合测试）

**优点**：快速测试、方便调试

### 步骤

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置 config.yaml**
   ```yaml
   # 邮件配置
   email:
     enabled: true
     sender_email: "your_email@qq.com"
     sender_password: "your_auth_code"  # 授权码
     receiver_emails:
       - "receiver@example.com"

   # LLM 配置
   llm:
     enabled: true
     api_key: "your-api-key"
     model: "glm-5"
     api_url: "dashscope"

   # 搜索源配置
   search_source: multi  # 或 arxiv, biorxiv, openalex, pubmed
   ```

3. **运行测试**
   ```bash
   # 测试邮件配置
   python test_email.py

   # 运行主程序
   python arxiv_agent.py
   ```

4. **（可选）设置定时任务**
   ```bash
   # Windows
   ./setup_windows_task.ps1

   # 或使用 Python 调度器
   python scheduler.py
   ```

---

## ⚡ 快速对比

| 特性 | GitHub Actions | 本地运行 |
|------|----------------|----------|
| 成本 | **免费** | 电费/电脑 |
| 维护 | **无需维护** | 需保持电脑开机 |
| 稳定性 | **云端稳定** | 依赖本地环境 |
| 配置难度 | 中等 | 简单 |
| 适合场景 | 长期使用 | 测试调试 |

---

## 🔍 搜索源选择

| 搜索源 | 适用领域 | 配置值 |
|--------|----------|--------|
| **多源合并** | 综合（推荐） | `multi` |
| arXiv | 物理、数学、CS | `arxiv` |
| bioRxiv | 生物医学预印本 | `biorxiv` |
| OpenAlex | 综合性学术 | `openalex` |
| PubMed | 生物医学权威 | `pubmed` |

```yaml
search_source: multi  # 推荐使用多源搜索
```

---

## 🤖 LLM 服务商选择

| 服务商 | model 示例 | api_url | 特点 |
|--------|-----------|---------|------|
| 智谱 AI | glm-5, glm-4 | zhipu | 国内直连 |
| 阿里云 | qwen3.5-flash | dashscope | 国内直连 |
| DeepSeek | deepseek-chat | deepseek | 性价比高 |
| OpenAI | gpt-4 | openai | 需代理 |
| Moonshot | moonshot-v1-8k | moonshot | 长文本 |

---

## 📮 获取邮箱授权码

### QQ邮箱（推荐）
1. 登录 [mail.qq.com](https://mail.qq.com)
2. 设置 → 账户 → 开启 IMAP/SMTP 服务
3. 发送短信验证 → 获得 **16位授权码**

### 163邮箱
1. 登录 [mail.163.com](https://mail.163.com)
2. 设置 → POP3/SMTP/IMAP → 开启服务
3. 获取授权码

---

## 🔑 获取 API Key

### 智谱 AI
1. 访问 [open.bigmodel.cn](https://open.bigmodel.cn)
2. 注册/登录
3. API Keys → 创建新的 API Key

### 阿里云 DashScope
1. 访问 [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
2. 开通服务
3. API-KEY 管理 → 创建

### DeepSeek
1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册/登录
3. API Keys → 创建

### PubMed API Key（可选）
1. 访问 [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/)
2. 注册/登录
3. Settings → API Key Management → Create an API Key

**有 API Key**: 每秒 10 次请求  
**无 API Key**: 每秒 3 次请求

---

## 📝 关键词配置示例

编辑 `keywords.txt`：

```
1. AI Agent for Biology
** AI agent **
** autonomous agent **
** biological agent **
** bioinformatics agent **
** protein design agent **
...

2. Knowledge Graph Construction
** knowledge graph **
** knowledge representation **
** ontology construction **
** entity extraction **
** relation extraction **
...
```

---

## 🆘 常见问题

### Q: 邮件发送失败？
- 检查授权码是否正确（不是登录密码）
- 尝试 `use_ssl: false, use_tls: true`
- 运行 `python test_email.py` 测试

### Q: LLM 调用失败？
- 检查 api_key 是否正确
- 确认 model 名称匹配服务商
- 检查 max_tokens 是否超出限制（建议 2000）

### Q: 搜索结果为空？
- 检查关键词格式是否正确
- 尝试增大 `days_back` 参数
- 检查网络连接

### Q: PDF 下载失败？
- 部分论文可能没有公开 PDF
- 系统会自动使用摘要进行总结
- 报告中会标注"基于摘要总结"

---

## 📚 更多文档

- [README.md](README.md) - 完整使用说明
- [GITHUB_DEPLOY.md](GITHUB_DEPLOY.md) - GitHub 部署详解

---

祝你使用愉快！📚
