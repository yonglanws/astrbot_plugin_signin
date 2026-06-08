# AstrBot 世界计划签到插件

# 注意
需要提前将数据配置到持久化目录，否则插件无法正常运行。

下载链接：

[123Pan(登录免付费)](https://1817184181.share.123865.com/123pan/fDUVVv-XM0Vh)  

[我的NAS](https://share.fnnas.net/s/ff8f53b4752e4016a6)

将文件解压到 `AstrBot/data/plugin_data/astrbot_plugin_signin/` 目录下。

确保文件目录结构如下：  

```
/AstrBot/data/plugin_data/astrbot_plugin_signin/
├── img/
│   ├── ena/
│   ├── knd/
│   └── ...
└── song/
    ├── songs.json
    └── images/

```


## 安装

```bash
cd AstrBot/data/plugins
git clone https://github.com/yonglanws/astrbot_plugin_signin.git
```

## 使用

发送 `签到` 即可。支持指定角色：

```
签到 ena          # 东云绘名卡面
签到 彰人          # 别名匹配
```

## 目录说明

| 目录 | 路径 | 说明 |
|------|------|------|
| 插件目录 | `AstrBot/data/plugins/astrbot_plugin_signin/` | 代码、字体、默认资源 |
| **持久化目录** | `AstrBot/data/plugin_data/astrbot_plugin_signin/` | 运行时数据，更新插件**不会**丢失 |

首次启动时，插件会自动将默认资源（图片、歌曲）同步到持久化目录。此后所有运行时读写都在持久化目录中进行。

## 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sign_in_command` | string | `签到` | 触发指令 |

在 AstrBot WebUI 插件设置页面直接修改后重载即可。

## 自定义

### 新增角色

在**持久化目录** `AstrBot/data/plugin_data/astrbot_plugin_signin/img/` 下操作：

1. 创建角色名目录（如 `miku/`）
2. 放入 `ok.png`、`yi.png`、`ji.png` 和卡面图片 `card_*.jpg`
3. 在插件目录的 `characters.json` 中添加角色信息（可选，用于别名搜索）
4. 重载插件即可

### 添加歌曲

编辑持久化目录下的 `plugin_data/astrbot_plugin_signin/song/songs.json`，封面放入 `song/images/{id}.png`。

### 更换字体

替换插件目录下的 `MiSans-Medium.ttf` 后重载。

## 常见问题

**Q: 图片显示不出来？**  
A: 检查持久化目录 `AstrBot/data/plugin_data/astrbot_plugin_signin/img/`。渲染失败会自动降级为文字签到。

**Q: 如何备份数据？**  
A: 复制持久化目录下的 `signin.db`。

## 许可证

GPLv3