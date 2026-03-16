# 🚀 快速开始指南

选择适合你的部署方式：

---

## 方式一：GitHub Actions 云端部署（推荐 ⭐）

**优点**：免费、稳定、零维护、自动运行

### 5分钟快速部署

#### 1. 创建 GitHub 仓库

在 GitHub 网页上创建一个新的空仓库（如 `arxiv-daily-push`），**不要**初始化 README。

#### 2. 配置 SSH 密钥（如果尚未配置）

```bash
# 检查是否已有 SSH 密钥
ls ~/.ssh/id_rsa.pub

# 如果没有，生成新的 SSH 密钥
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 复制公钥到剪贴板（Windows）
cat ~/.ssh/id_rsa.pub | clip

# 或者 Mac/Linux
cat ~/.ssh/id_rsa.pub | pbcopy
```

将公钥添加到 GitHub：**Settings → SSH and GPG keys → New SSH key**

#### 3. 推送代码到仓库

```bash
# 在项目目录中执行
git init
git add .
git commit -m "Initial commit"

# 使用 SSH 地址（推荐）
git remote add origin git@github.com:你的用户名/arxiv-daily-push.git

# 如果使用 HTTPS，会要求输入用户名和密码（或 Token）
# git remote add origin https://github.com/你的用户名/arxiv-daily-push.git

git branch -M main
git push -u origin main
```

#### 4. 配置 Secrets

进入仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | 填写内容 |
|--------|----------|
| `EMAIL_ENABLED` | `true` |
| `EMAIL_SENDER` | 你的QQ邮箱 |
| `EMAIL_PASSWORD` | QQ邮箱16位授权码 |
| `EMAIL_RECEIVERS` | 接收推送的邮箱 |

#### 5. 手动测试

- 进入 Actions 页面
- 点击 "Run workflow"
- 勾选 `test_email: true`
- 点击 Run

#### 6. 完成！

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

2. **配置邮箱**
   ```bash
   # 编辑 config.yaml，填入邮箱和授权码
   # 确保 email.enabled: true
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

## 🌟 新增功能

### PDF 全文读取
- 自动下载论文 PDF
- 提取全文文本内容
- 支持长文本处理（自动截断）

### 论文自动总结
- 使用 LLM 对论文全文进行深度总结
- 提取关键点、研究方法、结论、局限性
- JSON 格式输出，易于解析

### 多源搜索
- 支持 arXiv、Semantic Scholar、OpenAlex
- 多源结果合并去重
- 更全面的论文覆盖

---

## 🔑 SSH 配置详解

### 为什么使用 SSH？

| 方式 | 优点 | 缺点 |
|------|------|------|
| **SSH** | 安全、免密码、配置一次永久使用 | 需要配置密钥 |
| **HTTPS** | 简单、无需配置 | 每次推送需输入用户名密码/Token |

### 配置 SSH 步骤

1. **生成 SSH 密钥对**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # 或传统 RSA
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

2. **启动 SSH Agent**
   ```bash
   # Windows (Git Bash)
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_rsa

   # Mac
   eval "$(ssh-agent -s)"
   ssh-add -K ~/.ssh/id_rsa

   # Linux
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_rsa
   ```

3. **复制公钥到 GitHub**
   ```bash
   cat ~/.ssh/id_rsa.pub
   ```
   复制输出内容 → GitHub Settings → SSH keys → New SSH key

4. **测试连接**
   ```bash
   ssh -T git@github.com
   # 看到 "Hi xxx! You've successfully authenticated" 即成功
   ```

5. **切换远程地址为 SSH**
   ```bash
   # 查看当前远程地址
   git remote -v

   # 切换为 SSH
   git remote set-url origin git@github.com:用户名/仓库名.git

   # 验证
   git remote -v
   ```

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

## 🆘 遇到问题？

1. 查看 [GITHUB_DEPLOY.md](GITHUB_DEPLOY.md) 详细部署文档
2. 查看 [README.md](README.md) 完整使用说明
3. 检查 Actions 日志中的错误信息
4. 使用 `test_email.py` 测试邮件配置

---

祝你使用愉快！📚
