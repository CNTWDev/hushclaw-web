# hushclaw-web

HushClaw 的官网与技能目录（[hushclaw](https://github.com/CNTWDev/hushclaw) 的对外站点）：首页介绍产品理念与安装方式，`/skills` 浏览、提交和评分社区技能，`/docs` 发布文章，`/admin` 管理后台。

> HushClaw 是一个深度了解你的个人 AI 助理：记住你的偏好、背景和做事方法，从你的反馈与修正中反思、持续进化；运行在你自己的电脑上，记忆和数据由你持有。

技术栈：FastAPI + Uvicorn · SQLite + SQLAlchemy + Alembic · Jinja2 · Python 3.10+

---

## 服务器一键安装

适用于带 systemd 的 Linux 服务器（Ubuntu / Debian / CentOS / Rocky 等），用 root 或 sudo 执行：

```bash
curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh | sudo bash
```

脚本会自动完成：

1. 安装缺少的系统依赖（git、python3、python3-venv）
2. 创建系统用户 `hushclaw-web`，把代码克隆到 `/opt/hushclaw-web`
3. 生成运行配置 `/etc/hushclaw-web/hushclaw-web.env`（随机的 `SECRET_KEY` 和后台密码）
4. 创建虚拟环境、安装 Python 依赖、执行数据库迁移（`alembic upgrade head`）
5. 注册并启动 systemd 服务 `hushclaw-web`，等待健康检查通过
6. 安装运维命令 `hushclaw-web`

安装完成后会打印一次后台密码（之后可在 env 文件里查看）。服务默认只监听 `127.0.0.1:8000`，对外访问请配置反向代理（见下文）。

安装前可以用环境变量改默认值（只在首次安装时生效，之后保存在 `/etc/hushclaw-web/deploy.conf`）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HUSHCLAW_WEB_PORT` | `8000` | 服务端口 |
| `HUSHCLAW_WEB_HOST` | `127.0.0.1` | 监听地址；不用反向代理时可设为 `0.0.0.0` |
| `HUSHCLAW_WEB_BRANCH` | `master` | 跟踪的分支 |
| `HUSHCLAW_WEB_DIR` | `/opt/hushclaw-web` | 代码目录 |
| `HUSHCLAW_WEB_DATA` | `/var/lib/hushclaw-web` | 数据目录（数据库、备份） |
| `HUSHCLAW_WEB_IMPORT_DB` | 空 | 首次安装时导入已有的 SQLite 数据库 |
| `HUSHCLAW_WEB_STRICT_PORT` | `0` | 设为 `1` 时端口被占用直接报错，不自动换端口 |

例如：

```bash
curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh \
  | sudo HUSHCLAW_WEB_PORT=9000 bash
```

## 更新到最新代码

```bash
sudo hushclaw-web update
```

更新流程：拉取 GitHub 上最新代码 → 备份数据库和上传文件 → 切换到新代码 → 依赖有变化时重新安装 → 数据库迁移 → 重启服务 → 健康检查。

- 已经是最新时什么都不做；要强制重新部署用 `sudo hushclaw-web update --force`。
- **健康检查失败会自动回滚**：代码切回上一个版本、数据库恢复到更新前的备份、重启旧版本。
- 没有装 `hushclaw-web` 命令的机器，也可以直接用一行命令更新：

  ```bash
  curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh | sudo bash -s -- update
  ```

- 想定时自动更新，可以加一条 cron（每天 4 点）：

  ```bash
  echo '0 4 * * * root /usr/local/bin/hushclaw-web update >> /var/log/hushclaw-web-update.log 2>&1' | sudo tee /etc/cron.d/hushclaw-web
  ```

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `sudo hushclaw-web update [--force]` | 拉取最新代码并重启 |
| `hushclaw-web status` | 当前部署的版本、端口和服务状态 |
| `hushclaw-web logs [-f]` | 查看服务日志 |
| `sudo hushclaw-web restart` | 重启服务（同样会处理端口占用） |
| `sudo hushclaw-web backup` | 手动备份数据库和上传文件 |
| `sudo hushclaw-web rollback [--with-db]` | 回到上一次部署的版本；`--with-db` 同时恢复那次更新前的数据库 |
| `sudo hushclaw-web uninstall [--purge]` | 卸载服务；默认保留代码、数据和配置，`--purge` 全部删除 |

## 端口被占用怎么办

安装、更新和重启时，脚本都会先检查端口，并区分两种情况：

1. **被 hushclaw-web 自己的旧进程占用**（比如以前手动 `./start.sh` 或 `uvicorn` 跑起来的、没停掉的旧服务）：脚本识别出它是本项目的进程，先停掉（含 `--reload` 的子进程），然后在原端口重新启动。
2. **被别的程序占用**：脚本打印占用者的 PID 和命令，自动选择后面第一个空闲端口（如 8001），写回 `deploy.conf`，并提醒你同步修改反向代理里的端口。如果你希望端口固定、宁可失败也不要换，安装时设置 `HUSHCLAW_WEB_STRICT_PORT=1`。

要手动换端口：编辑 `/etc/hushclaw-web/deploy.conf` 里的 `PORT`，然后 `sudo hushclaw-web restart`。

## 反向代理（nginx 示例）

```nginx
server {
    listen 80;
    server_name hushclaw.example.com;
    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

服务以 `--proxy-headers` 启动，评分等按 IP 去重的功能能拿到真实访客 IP。HTTPS 可以用 certbot 或直接换 Caddy。

## 目录与配置

| 路径 | 内容 |
| --- | --- |
| `/opt/hushclaw-web` | 代码（git checkout）和虚拟环境 `.venv` |
| `/opt/hushclaw-web/static/uploads` | 用户上传的文件（不受 git 更新影响，会随备份打包） |
| `/var/lib/hushclaw-web/hushclaw-web.db` | 数据库 |
| `/var/lib/hushclaw-web/backups/` | 每次更新前的备份，保留最近 10 份 |
| `/var/lib/hushclaw-web/deploy-history` | 每次成功部署的时间和 commit |
| `/etc/hushclaw-web/hushclaw-web.env` | 运行配置：后台密码、`SECRET_KEY`、SMTP 等，修改后 `sudo hushclaw-web restart` |
| `/etc/hushclaw-web/deploy.conf` | 部署配置：仓库、分支、目录、端口 |

### 从旧的手动部署迁移

如果服务器上已经有一份手动跑的站点（例如仓库目录里的 `hushclas.db`），首次安装时把旧数据库导入：

```bash
curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh \
  | sudo HUSHCLAW_WEB_IMPORT_DB=/path/to/old/hushclas.db bash
```

旧进程如果还占着同一个端口，脚本会识别并停掉它。不带这个变量时，新安装会以仓库里自带的 `hushclas.db`（技能和分类的种子数据）为初始数据库。上传文件请手动复制到 `/opt/hushclaw-web/static/uploads/`。

## 安装脚本的升级

- **脚本跟着代码一起升级。** `hushclaw-web` 命令只是调用代码目录里的 `install.sh`；`update` 拉下新代码后，会用**新版本**的脚本完成剩下的步骤（依赖、迁移、systemd 单元、重启）。所以修改 `install.sh` 并合并到 `master` 后，服务器下一次 `update` 就会用上新脚本，无需额外操作。
- systemd 单元文件和 `hushclaw-web` 命令每次部署都会按新脚本重写；`deploy.conf` 和 `hushclaw-web.env` 只在缺失时生成，已有的配置不会被覆盖。
- 修改脚本时请：
  1. 更新脚本顶部的 `SCRIPT_VERSION`（`hushclaw-web version` 可查看）
  2. 保持对旧 `deploy.conf` 的兼容：新增配置项要有默认值
  3. 先在测试机上跑一遍全新安装和 `update --force`，再合并
- 如果某次脚本改坏了导致 `update` 无法完成，可以在服务器上 `sudo hushclaw-web rollback` 回到上一版，或者用一行命令直接拉取 GitHub 上修好的脚本执行 `update`。

---

## 本地开发

```bash
./start.sh
```

自动创建虚拟环境、安装依赖，并在 `http://localhost:8000` 启动（带 `--reload`）。或者手动：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

复制 `.env.example` 为 `.env` 可修改本地配置。`python seed_data.py` 会**清空**技能、分类和评分后重新写入种子数据，只在本地使用。

### 项目结构

```
hushclaw-web/
├── install.sh          # 服务器一键安装 / 更新脚本
├── app/
│   ├── main.py         # 应用入口
│   ├── database.py     # 数据库连接
│   ├── models.py       # SQLAlchemy 模型
│   ├── routes/         # home / skills / docs / auth / account / api / admin
│   └── templates/      # Jinja2 模板
├── alembic/            # 数据库迁移
├── static/             # CSS、JS、图片、上传文件
├── requirements.txt
├── seed_data.py        # 种子数据（会清空现有数据）
└── start.sh            # 本地开发启动脚本
```

### 数据模型

- **Category**：技能分类
- **Skill**：标题、描述、平台、标签、评分
- **Rating**：按 IP 评分（每人每个技能一票）
- **User / EmailOTP / UserToken**：邮箱验证码登录
- **AppVersion**：客户端版本管理
- **Doc**：文章
