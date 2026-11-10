# 张高俊的个人主页与博客

一个可部署到 **GitHub Pages** 的静态个人站点，面向 `MoLi0522.github.io`。

暖白与深绿的双主题、响应式布局、教育时间线、文章搜索与标签筛选、文章目录、代码复制、RSS、站点地图和 404 页面。无需数据库，无需安装第三方 Python 库，也没有第三方字体、脚本或统计追踪。

> **交付状态：网站已在本地生成，尚未上传到 GitHub，也尚未公开上线。**
> 仓库名和目标域名依据你提供的 GitHub 用户名设置；请在自己的账号中完成下面的发布操作。

## 一、先在本地看看

需要 **Python 3.11 或更高版本**。在本目录打开终端：

```powershell
python site.py build
python site.py serve
```

打开 <http://127.0.0.1:8000>。停止预览按 `Ctrl+C`。端口被占用时：

```powershell
python site.py serve --port 8126
```

`build` 会生成 `_site/` 并自动检查本地链接、文章锚点、图片替代文本、RSS 和站点地图。修改源文件后，重新运行 `python site.py build` 并刷新浏览器。

你也可以直接打开 `_site/index.html` 浏览基本内容；推荐使用本地服务器，以便搜索 URL 等浏览器功能正常工作。

## 二、发布到 GitHub Pages（推荐：自动部署）

### 1. 创建仓库

登录 <https://github.com/MoLi0522>，点击右上角 `+` → **New repository**。

- Repository name：**`MoLi0522.github.io`**
- Visibility：**Public**（适合 GitHub Free 的 Pages 个人站点）
- 不勾选初始化 README / .gitignore / License；直接创建空仓库。

仓库名必须是 `用户名.github.io`。如果 GitHub 提示仓库已存在，请先检查其内容，**不要覆盖原有网站或强制推送**。

### 2. 上传源代码

在本目录运行：

```powershell
git init
git add .
git commit -m "Create personal website and blog"
git branch -M main
git remote add origin https://github.com/MoLi0522/MoLi0522.github.io.git
git push -u origin main
```

Git 可能会在浏览器中让你登录 GitHub；不要向任何人提供密码或访问令牌。

如果 Git 提示缺少提交者信息，请先设置你希望公开在提交记录中的姓名和邮箱；若不想公开真实邮箱，可以使用 GitHub **Settings → Emails** 中提供的 noreply 邮箱。

### 3. 开启 Pages

仓库 → **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**。

然后到仓库 **Actions** 页面，找到 **Build and deploy to GitHub Pages**：

- 若首次任务因尚未开启 Pages 而失败，进入任务，点击 **Re-run all jobs**。
- 或选择该工作流 → **Run workflow** → main。
- 所有步骤变绿后，打开：<https://moli0522.github.io/>。

后续向 `main` 提交资料或文章修改，都会自动重新构建和发布。部署通常需要一些时间；若页面暂未更新，先查看 Actions 是否完成，再尝试刷新。

**不要将 `_site/` 提交到源代码仓库。** 工作流会自动构建并只发布此目录，不会把源配置和构建程序作为网页文件发布。

## 三、不使用 Git 命令的上传方式

在 GitHub 网页创建好空仓库后，使用 **uploading an existing file** / **Add file → Upload files** 上传本目录的源文件与文件夹。不要上传外层目录，也不需要上传 `_site/`。

尤其确认隐藏目录 `.github/workflows/pages.yml` 已在 GitHub 仓库内。有些系统文件选择器会忽略隐藏文件，如果上传后没有该目录，可在 GitHub 点击 **Add file → Create new file**，文件名填写 `.github/workflows/pages.yml`，复制本地同名文件内容并提交。

然后按照上一节开启 GitHub Actions。推荐优先使用 Git 命令，可以避免遗漏隐藏文件。

## 四、改个人资料

编辑 `content/profile.json`：

- `name` / `english_name`：中文名 / 英文名。
- `description` / `intro` / `tagline`：搜索摘要、个人介绍和主页短句。
- `github_username`：GitHub 用户名。
- `site_url`：正式 HTTPS 根地址，用于分享卡片、RSS、SEO；当前是 `https://moli0522.github.io`。此版本针对用户站点根域部署，不直接支持 `用户名.github.io/仓库名/` 子路径。
- `hometown`：当前展示为“河南 · 扶沟”。
- `education`：教育时间线。硕士 2026.09—至今；本科 2022.09—2026.06。
- `projects`：真实的个人公开项目，目前留空。添加后会自动显示项目卡片。

项目示例（**请替换为自己真实的项目，不要原样发布**）：

```json
"projects": [
  {
    "name": "你的真实项目名称",
    "description": "简要说明项目解决的问题，以及你实际完成的工作。",
    "url": "https://github.com/MoLi0522/真实仓库名"
  }
]
```

照片在 `assets/images/portrait.png`，已从你提供的图片中裁出。原图分辨率有限，建议后续替换为更清晰的同类竖版照片。社交分享封面在 `assets/images/social-card.png`；如果改名或换身份，请同步更换该图片。

主页的部分开场文字与栏目标题在 `site.py` 的 `homepage()` 函数中。如需深度改版，可直接修改。

### 隐私说明

公开网页默认展示姓名、学校、专业、教育经历、家乡和 GitHub。**出生年月、民族、政治面貌和性别未写入站点或源配置**，避免随公开仓库一并泄露。若你确实希望公开这些信息，可自行添加，但请先考虑长期公开与搜索引擎收录的影响。

联系入口仅使用你的 GitHub，没有虚构邮箱、微信、技能、论文、获奖经历或个人项目。GitHub 左栏显示的其他账号仓库不是个人作品，本网站未将它们列为你的项目。

## 五、写一篇新博客

在 `content/posts/` 新建 UTF-8 编码的 `.md` 文件，例如 `my-first-note.md`：

```markdown
+++
title = "我的第一篇学习笔记"
date = "2026-11-04"
slug = "my-first-note"
summary = "用一两句话说明这篇文章的内容。"
tags = ["学习笔记", "计算机"]
demo = false
+++

## 为什么要记录这个问题

正文从这里开始。

## 我的理解

- 一个关键点
- 另一个关键点

> 引用或值得记住的话。
```

- 文件开头 `+++` 之间是 **TOML 元数据**，不是 YAML。
- 日期使用 `YYYY-MM-DD`；文章按日期倒序，同日按 slug 排序。
- `slug` 只能使用小写英文字母、数字和短横线，且不能重复。发布后尽量不更改，避免旧链接失效。
- `demo = true` 会显示“初始文章 / 初始示例”提示；原创文章设为 `false`。
- 两篇随站点提供的文章均明确标为初始示例，不代表你已经独立发表过这些内容。可直接编辑或删除源文件。
- 内置轻量解析器支持段落、二至四级标题、加粗、斜体、行内代码、链接、列表、引用、分隔线、围栏代码块。不支持完整 CommonMark、复杂表格、嵌套列表、原始 HTML 或 Markdown 图片语法。
- 删除文章源文件后，构建会依据生成清单移除相应旧页面。

本地运行 `python site.py build` 检查无误后提交到 GitHub，Actions 会自动发布。

## 六、目录说明

```text
.
├── .github/workflows/pages.yml  # 自动构建、检查与部署
├── assets/
│   ├── css/style.css            # 所有主题与响应式样式
│   ├── js/main.js               # 搜索、筛选、主题与移动导航
│   └── images/                 # 照片、图标、分享封面
├── content/
│   ├── profile.json            # 个人资料与教育经历
│   └── posts/*.md              # 博客文章源文件
├── site.py                     # 零第三方依赖的生成器、检查器与预览服务
├── .gitignore
├── README.md
└── _site/                      # 自动生成的最终网站（不提交）
```

## 七、常见问题

**打开后 404？** 检查仓库名是否正确、Pages Source 是否为 GitHub Actions、最新 Actions 是否已成功。不要把源码再套一层文件夹上传。

**修改 Markdown 后没变化？** 本地需要重新 `build`，线上需要提交到 `main` 并等待工作流完成。

**Python 报找不到 `tomllib`？** Python 版本太旧，请使用 Python 3.11+。在部分 Windows 电脑上可以用 `py -3.12 site.py build`。

**想换域名？** 先把 `site_url` 改成自己的 HTTPS 根域，在发布目录配置 `CNAME`，再完成 GitHub Pages Custom domain 与 DNS 设置；确认 HTTPS 正常后发布。当前未替你申请或配置域名。

**联系表单在哪里？** 纯静态网站没有服务器端收件功能，当前只放 GitHub 联系入口。不要把邮箱密码、Token 或服务密钥写进公开仓库。

**内容版权？** 姓名、照片及个人资料属于站点本人；站点不自动替你选择开源许可证。若计划开源代码，请自行选择合适的 License；文章内容授权也请单独声明。
