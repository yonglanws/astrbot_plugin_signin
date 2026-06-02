# AstrBot 世界计划签到插件 (astrbot_plugin_signin_new)

[![AstrBot Plugin](https://img.shields.io/badge/AstrBot-Plugin-blue)](https://github.com/AstrBotDevs/AstrBot)
[![Version](https://img.shields.io/badge/version-v2.2.0-green)](https://github.com/yonglanws/astrbot_plugin_signin)

## ✨ 功能特性

### 🎯 核心功能
- **📅 签到日历可视化** - 直观展示本月签到记录，支持连续签到天数统计
- **🎲 运势抽取** - 每次随机生成宜/忌事项和运势等级（大吉~大凶）
- **🎭 角色卡面** - 支持 25+ 角色卡面背景，可随机或指定角色签到
- **🔍 别名搜索** - 支持通过角色名、中文名、别名搜索指定角色
- **🎵 歌曲推荐** - 从歌曲库随机推荐音乐，显示封面和信息
- **🎨 美观界面** - 采用毛玻璃效果、渐变色彩，左右分栏布局
- **📝 文字降级** - 图片渲染失败时自动降级为文字签到
- **⚙️ 完全可配置** - 所有功能均可在管理面板中自定义开关和参数

### 🎨 界面设计
- **左侧面板**: 签到核心内容（成功图标、用户名、日期时间、运势等级、宜忌、歌曲推荐）
- **右侧面板**: 留空，展示完整卡面背景
- **固定尺寸渲染**: 2400×2160px 高清图片输出

---

## 📦 安装方法

### 方法一：从 GitHub 克隆（推荐）

```bash
cd AstrBot/data/plugins
git clone https://github.com/yonglanws/astrbot_plugin_signin.git
```

### 方法二：手动安装

1. 下载插件压缩包
2. 解压到 `AstrBot/data/plugins/` 目录
3. 重命名文件夹为 `astrbot_plugin_signin_new`
4. 在 AstrBot WebUI 中启用插件

---

## 🚀 使用说明

### 基础使用

1. 启动 AstrBot 并加载本插件
2. 在群聊或私聊中发送指令（默认为 `签到`）
3. 插件将返回精美的签到卡片图片

### 指定角色签到

支持通过角色名、中文名或别名指定签到卡面：

```
签到 ena          # 使用东云绘名的卡面
签到 彰人          # 使用东云彰人的卡面（别名匹配）
签到 小气走        # 使用宵崎奏的卡面（别名匹配）
```

如果指定的角色不存在或找不到对应卡面，将自动降级为随机角色。

> 角色信息定义在 `characters.json` 中，新增角色时只需在 `data/img/` 下创建对应名称的目录即可自动识别。

## ⚙️ 配置说明

### 通过管理面板配置（推荐）

本插件完全支持 AstrBot 的可视化配置系统。在 AstrBot 管理面板的插件设置页面可以直接修改所有配置项。

#### 配置项列表

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sign_in_command` | string | `签到` | 触发签到的指令名称 |
| `footer_text` | string | `mzkbot by 慵懒午睡 \| 请勿迷信哦🥺` | 签到卡片底部自定义文本 |
| `show_calendar` | bool | `true` | 是否显示签到日历 |
| `show_song_recommendation` | bool | `true` | 是否显示歌曲推荐 |

#### 高级配置 - 界面设置 (`ui_settings`)

| 子配置项 | 类型 | 默认值 | 说明 |
|----------|------|--------|------|
| `card_opacity` | float | `0.22` | 卡片透明度 (0.0-1.0) |
| `blur_intensity` | int | `26` | 模糊强度 (0-50) |

---

### 手动编辑配置文件

配置文件位置: `data/config/astrbot_plugin_signin_config.json`

```json
{
  "sign_in_command": "签到",
  "footer_text": "mzkbot by 慵懒午睡 | 请勿迷信哦🥺",
  "show_calendar": true,
  "show_song_recommendation": true,
  "ui_settings": {
    "card_opacity": 0.22,
    "blur_intensity": 26
  }
}
```

> **注意**: 修改配置文件后需要重启或重载插件才能生效

---

## 📁 项目结构

```
astrbot_plugin_signin/
├── main.py                      # 主程序文件
├── metadata.yaml                # 插件元数据
├── _conf_schema.json            # 配置 Schema 定义
├── characters.json              # 角色信息（名称、别名）
├── README.md                    # 项目文档
├── MiSans-Medium.ttf            # MiSans 字体文件
└── data/                        # 插件自带资源（首次启动时同步到持久化目录）
    ├── img/                     # 图片资源（按角色分目录）
    │   ├── ena/                 # 东云绘名角色卡面
    │   │   ├── ok.png
    │   │   ├── yi.png
    │   │   ├── ji.png
    │   │   └── card_*.jpg       # 卡面背景图
    │   ├── knd/                 # 宵崎奏角色卡面
    │   ├── mfy/                 # 朝比奈真冬角色卡面
    │   ├── mzk/                 # 晓山瑞希角色卡面
    │   ├── akt/                 # 东云彰人角色卡面
    │   ├── tks/                 # 天马司角色卡面
    │   └── ...                  # 更多角色...
    └── song/
        ├── songs.json           # 歌曲数据库
        └── images/
            ├── 1.png            # 歌曲封面...
            └── ...
```

> **数据持久化**: 用户数据（`signin.db`、配置等）存储在 AstrBot 数据目录的 `plugin_data/astrbot_plugin_signin/` 下，更新插件时不会丢失。

---

## 🔧 自定义配置

### 添加歌曲

编辑 `data/song/songs.json`：

```json
[
  {
    "id": 1,
    "n": "Song Name",
    "cn": "歌曲中文名"
  },
  {
    "id": 2,
    "n": "Another Song",
    "cn": "另一首歌"
  }
]
```

并将对应的封面图片放入 `data/song/images/` 目录，命名为 `{id}.png` 或 `{id}.jpg`

### 替换图片资源

图片资源按角色分目录存储，插件启动时会**自动扫描** `data/img/` 下的所有子目录作为可用角色。

将自定义图片放入对应角色的 `data/img/{角色名}/` 目录：
- `ok.png` - 成功图标（透明背景 PNG）
- `yi.png` - 宜图标
- `ji.png` - 忌图标
- `card_*.jpg/png/webp` - 卡面背景图（建议正方形）

**新增角色步骤：**
1. 在 `plugin_data/img/` 下创建以角色 `name` 命名的目录（如 `miku/`）
2. 放入 `ok.png`、`yi.png`、`ji.png` 和卡面图片
3. 在 `characters.json` 中添加角色信息（可选，用于别名搜索）
4. 重启或重载插件即可自动识别

> 目录名必须与 `characters.json` 中的 `name` 字段一致才能被别名搜索匹配。

### 更换字体

替换 `MiSans-Medium.ttf` 为你喜欢的字体文件（支持 TTF 格式）

---

## 📊 数据结构

### 签到数据格式 (`signin.db`)

签到数据使用 SQLite 数据库存储，主要表结构：

| 表名 | 说明 |
|------|------|
| `users` | 用户基本信息 |
| `checkins` | 签到记录 |
| `daily_state` | 每日签到状态（连续天数等） |

**字段说明：**
- `context_id`: 群聊/私聊上下文 ID
- `user_id`: 用户唯一标识
- `username`: 用户昵称
- `last_checkin`: 最后一次签到日期
- `streak_days`: 连续签到天数
- `signed_dates`: 本月签到日期列表

---

## 🔄 版本历史

### v2.2.0 (当前版本)
- ✨ 新增角色别名搜索系统，支持 `签到 角色名` 指定卡面
- ✨ 支持 `characters.json` 定义角色名称和别名
- ✨ 新增 `akt`、`tks` 等多个角色卡面
- ✨ 图片渲染失败时自动降级为文字签到
- 🔧 数据目录改为 AstrBot 标准持久化路径 `plugin_data/astrbot_plugin_signin/`
- 🔧 静态资源（img/song）增量同步到持久化目录
- 🔧 角色列表改为动态扫描，新增角色无需修改代码

### v2.1.0
- ✨ 新增 `footer_text` 配置项，支持自定义签到卡片底部文本
- ✨ 背景图改为按角色分目录随机选取，支持多角色卡面
- 🔧 删除 `help_text` 配置项
- 🔧 删除 `show_daily_quote`、`background_opacity`、`font_size_scale`、`data_settings` 等未使用配置
- 🔧 修复新版 t2i 渲染引擎背景图偏移问题
- 🔧 数据存储迁移到 SQLite 数据库

### v2.0.0
- ✨ 新增左右分栏布局设计
- ✨ 新增签到日历可视化功能
- ✨ 新增连续签到天数统计
- ✨ 新增随机歌曲推荐功能
- ✨ 支持 AstrBot 可视化配置系统
- 🔧 优化数据结构，支持签到历史记录
- 🐛 修复多项已知问题

### v1.0.0
- 🎉 初始版本发布
- ✅ 基础签到功能
- ✅ 运势抽取（宜/忌）
- ✅ HTML 自定义渲染

---

## ❓ 常见问题

### Q: 如何修改签到指令？
A: 在 AstrBot 管理面板的插件设置中修改 `sign_in_command` 配置项，或直接编辑配置文件。

### Q: 如何隐藏某个功能模块？
A: 将对应配置项设为 `false`，例如：
- 隐藏日历: `"show_calendar": false`
- 隐藏歌曲推荐: `"show_song_recommendation": false`

### Q: 图片显示不出来怎么办？
A: 请检查持久化目录 `plugin_data/astrbot_plugin_signin/img/` 下的图片文件是否存在且未损坏。首次启动时会自动从插件目录同步资源，如果同步失败可手动复制。如果渲染引擎异常，插件会自动降级为文字签到。

### Q: 如何指定角色签到？
A: 在签到指令后加上角色名或别名，例如：
- `签到 ena` — 使用东云绘名卡面
- `签到 彰人` — 使用东云彰人卡面（别名匹配）
- `签到 小气走` — 使用宵崎奏卡面（别名匹配）

角色信息定义在 `characters.json` 中，支持 `name`、`fullNameChinese` 和 `aliases` 三种匹配方式。

### Q: 歌曲封面如何添加？
A: 将封面图片命名为 `{歌曲ID}.png` 或 `{歌曲ID}.jpg`，放入 `data/song/images/` 目录。

### Q: 如何备份签到数据？
A: 复制 AstrBot 数据目录下的 `plugin_data/astrbot_plugin_signin/signin.db` 文件即可完整备份所有用户的签到记录。数据库文件会自动在首次使用时创建。

### Q: 支持哪些消息平台？
A: 支持所有 AstrBot 兼容的平台，包括 QQ（aiocqhttp/官方）、Telegram、飞书、企业微信、钉钉等。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境准备

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add some amazing feature'`
4. 推送到分支: `git push origin feature/amazing-feature`
5. 提交 Pull Request

### 代码规范

- 使用 [ruff](https://docs.astral.sh/ruff/) 进行代码格式化
- 遵循 PEP 8 编码规范
- 添加必要的注释和文档字符串
- 测试所有新功能

---

## 📄 许可证

本项目采用 GPLv3 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) - 强大的聊天机器人框架
- [MiSans](https://hyperos.mi.com/font-download) - 小米出品的现代字体
- 所有贡献者和使用者

---

## 📞 联系方式

- **作者**: ylws (慵懒午睡)
- **GitHub**: [yonglanws](https://github.com/yonglanws)
- **Issue**: [提交问题](https://github.com/yonglanws/astrbot_plugin_signin_new/issues)
- **讨论区**: [GitHub Discussions](https://github.com/yonglanws/astrbot_plugin_signin_new/discussions)

---

## ⭐ Star 历史

如果这个项目对你有帮助，请给一个 ⭐ 支持一下！

<p align="center">
  <b>Made with ❤️ by ylws</b>
</p>
