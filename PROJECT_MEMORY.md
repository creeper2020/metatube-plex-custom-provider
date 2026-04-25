# Project Memory: MetaTube Plex Custom Metadata Provider

## 当前目标

这个项目把 `metatube-community/metatube-plex-plugins` 迁移为 Plex Custom Metadata Provider。

当前采用 Go 单体版 Provider：同一个进程同时提供 Plex Custom Metadata Provider HTTP 接口，并直接调用 `metatube-sdk-go` 的抓取 engine、SQLite 缓存和图片处理能力。不再需要独立 MetaTube API 后端。

## 代码结构

- `provider-go/`
  - Go 单体版 Plex Provider，当前正式使用。
  - 通过 `replace github.com/metatube-community/metatube-sdk-go => ../../metatube-sdk-go` 复用本地 SDK。
- `provider/`
  - 旧的 Python Provider 实现，保留用于回滚或对照。
- `/home/plex/metatube-sdk-go`
  - 本地克隆的 MetaTube SDK/后端代码，Go Provider 直接引用它的 engine。

## 正式部署

systemd 服务：

```text
metatube-provider.service
```

正式二进制：

```text
/home/plex/bin/metatube-plex-provider-go
```

正式配置：

```text
/home/plex/metatube-provider-go.env
```

systemd unit：

```text
/etc/systemd/system/metatube-provider.service
```

当前服务只监听本地：

```text
127.0.0.1:8080
```

这是为了给反向代理使用，不直接暴露 `8080` 到公网。

反代上游应指向：

```text
http://127.0.0.1:8080
```

Go Provider 支持 `X-Forwarded-Proto` 和 `X-Forwarded-Host`，反代需要传这两个 header，确保返回给 Plex 的图片 URL 是公网域名。

## Plex Provider 地址

Provider 使用路径 token 鉴权，格式是：

```text
https://your-domain.example/_metatube/<token>
```

不要把真实 token 写进代码仓库。真实值在：

```text
/home/plex/metatube-provider-go.env
```

## 已迁移功能

Go 单体版已覆盖旧 Python Provider 的主要功能：

- Plex Custom Metadata Provider 根文档
- `/library/metadata/matches`
- `/library/metadata/{ratingKey}`
- `/library/metadata/{ratingKey}/images`
- 图片代理：封面、背景图、演员图
- 多源匹配与合并
- 精确番号过滤
- 影片源过滤/排序
- 标题模板
- 标题、演员、类型替换表
- AVBASE 真名演员替换
- 标题/简介翻译
- 演员头像
- 导演、片商、类型、评分
- 中文字幕检测
- 中文字幕封面徽章
- 路径鉴权
- systemd 开机自启

说明：`Translation Reviews` 保留配置兼容，但旧 Python Provider 实际没有把 reviews 输出到 Plex metadata，Go 版也保持一致。

## 常用命令

进入 Go Provider：

```sh
cd /home/plex/metatube-plex-plugins/provider-go
```

测试：

```sh
env GOCACHE=/tmp/go-build-cache GOMODCACHE=/home/plex/.gomodcache go test ./...
```

编译：

```sh
env GOCACHE=/tmp/go-build-cache GOMODCACHE=/home/plex/.gomodcache go build -o /home/plex/bin/metatube-plex-provider-go .
```

重启服务：

```sh
systemctl restart metatube-provider
```

查看服务状态：

```sh
systemctl status metatube-provider --no-pager
```

本机健康检查，需要带路径 token：

```sh
curl http://127.0.0.1:8080/_metatube/<token>/health
```

确认没有公网直连监听：

```sh
curl http://10.0.7.234:8080/_metatube/<token>/health
```

期望结果是连接失败，因为服务只监听 `127.0.0.1`。

## 配置项

配置文件 `/home/plex/metatube-provider-go.env` 支持：

```text
METATUBE_HOST
METATUBE_PORT
METATUBE_DSN
METATUBE_AUTH_PATH
METATUBE_AUTH_TOKEN
METATUBE_ENABLE_ACTOR_IMAGES
METATUBE_ENABLE_DIRECTORS
METATUBE_ENABLE_RATINGS
METATUBE_ENABLE_REAL_ACTOR_NAMES
METATUBE_ENABLE_BADGES
METATUBE_BADGE_URL
METATUBE_ENABLE_MOVIE_PROVIDER_FILTER
METATUBE_MOVIE_PROVIDER_FILTER
METATUBE_ENABLE_TITLE_TEMPLATE
METATUBE_TITLE_TEMPLATE
METATUBE_ENABLE_TITLE_SUBSTITUTION
METATUBE_TITLE_SUBSTITUTION_TABLE
METATUBE_ENABLE_ACTOR_SUBSTITUTION
METATUBE_ACTOR_SUBSTITUTION_TABLE
METATUBE_ENABLE_GENRE_SUBSTITUTION
METATUBE_GENRE_SUBSTITUTION_TABLE
METATUBE_TRANSLATION_MODE
METATUBE_TRANSLATION_ENGINE
METATUBE_TRANSLATION_ENGINE_PARAMETERS
```

替换表变量使用 Base64 编码内容，每行格式：

```text
旧=新
```

标题模板支持：

```text
{provider} {id} {number} {title} {series} {maker} {label} {director} {actors} {first_actor} {year} {date}
```

## 验证过的样例

测试过：

```text
IPX-333
JUQ-907
```

`JUQ-907` 验证结果：

- 手动匹配返回多源合并候选
- 合并详情正常
- 演员、导演、片商、类型、评分正常
- 封面图 `GET` 正常
- 图片 `HEAD` 正常

## 注意事项

- 不要重新启动旧的 `metatube-backend`，当前架构不再需要它。
- 旧 Python Provider 仍在 `provider/`，不要删除，除非明确确认不再需要回滚。
- Go 单体版依赖本地 `/home/plex/metatube-sdk-go`，移动目录前需要同步修改 `provider-go/go.mod` 的 `replace`。
- 反代公网暴露时必须使用 HTTPS，因为路径 token 会出现在 URL 中。
- 服务只监听 `127.0.0.1` 是刻意设计，公网入口应全部走反向代理。
