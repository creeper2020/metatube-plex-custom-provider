# MetaTube Plex Custom Provider

这是一个面向 Plex Custom Metadata Providers API 的 MetaTube 刮削器。

项目把 `metatube-community/metatube-plex-plugins` 的 Plex 插件逻辑迁移成独立 HTTP Provider，并把 `metatube-community/metatube-sdk-go` 的刮削引擎整合进 `provider-go/`。运行时不再需要单独部署 MetaTube API Server，Plex 只需要访问这个 Provider 服务。

代码来源和许可说明见 [ATTRIBUTION.md](./ATTRIBUTION.md)。

## 当前状态

- 正式实现：[`provider-go/`](./provider-go/README_ZH.md)
- 运行方式：单个 Go 二进制，监听本地端口，推荐通过反向代理给 Plex 访问
- 后端依赖：无独立 MetaTube API Server，直接调用 `metatube-sdk-go`
- Plex 版本：面向支持 Custom Metadata Providers 的 Plex 版本
- 预告片：当前不输出预告片数据

## 功能

- Plex Custom Metadata Provider 根文档
- 手动匹配：`POST /library/metadata/matches`
- 元数据详情：`GET /library/metadata/{ratingKey}`
- 图片列表：`GET /library/metadata/{ratingKey}/images`
- 封面、背景图、演员图代理
- 多来源搜索、精确番号过滤和结果合并
- 影片源过滤和排序
- 标题模板
- 标题、演员、类型替换表
- AVBASE 真实演员名替换
- 标题和简介翻译
- 演员头像、导演、片商、类型、评分
- 中文字幕识别和封面徽章
- 路径 token 鉴权
- 反向代理公网 URL 生成支持

## 目录结构

```text
provider-go/          Go 单体版 Provider，当前主要实现
provider/             早期 Python Provider 原型，保留作对照和回滚参考
MetaTube.bundle/      上游旧版 Plex 插件代码，保留来源和兼容参考
MetaTubeHelper.bundle/上游旧版辅助插件代码，保留来源和兼容参考
ATTRIBUTION.md        上游代码和 SDK 引用说明
PROJECT_MEMORY.md     项目维护记录
```

## 构建

`provider-go/go.mod` 通过 `replace` 引用本地 `metatube-sdk-go`。请把两个仓库放在同一个父目录下：

```text
workspace/
  metatube-sdk-go/
  metatube-plex-custom-provider/
```

然后构建：

```sh
cd workspace/metatube-plex-custom-provider/provider-go
go test ./...
go build -o metatube-plex-provider .
```

如果你的 SDK 放在其他位置，修改 [`provider-go/go.mod`](./provider-go/go.mod) 里的 `replace github.com/metatube-community/metatube-sdk-go => ../../metatube-sdk-go`。

## 运行

建议只监听本机地址，再通过 Nginx、Caddy 或其他反向代理暴露 HTTPS：

```sh
METATUBE_HOST=127.0.0.1 \
METATUBE_PORT=8080 \
METATUBE_DSN=/path/to/metatube-provider-go.db \
METATUBE_AUTH_TOKEN='replace-with-a-random-token' \
./metatube-plex-provider
```

Provider 地址格式：

```text
https://your-domain.example/_metatube/<token>
```

`<token>` 来自 `METATUBE_AUTH_TOKEN`。不要把真实 token 提交到仓库。

## Plex 添加方式

在 Plex 的 Custom Metadata Providers 页面添加 Provider URL：

```text
https://your-domain.example/_metatube/<token>
```

添加后，在对应影片库里选择这个自定义 Provider，然后对影片执行匹配或刷新元数据。

## 反向代理

Provider 会根据 `X-Forwarded-Proto` 和 `X-Forwarded-Host` 生成返回给 Plex 的图片 URL。反代时需要传这些头。

Nginx 示例：

```nginx
location /_metatube/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

公网部署时建议只暴露 HTTPS，不要直接开放 `8080`。

## 常用配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `METATUBE_HOST` | `127.0.0.1` | 监听地址 |
| `METATUBE_PORT` | `8080` | 监听端口 |
| `METATUBE_DSN` | `/home/plex/metatube-provider-go.db` | SQLite 或 PostgreSQL DSN |
| `METATUBE_AUTH_PATH` | `_metatube` | 路径鉴权前缀 |
| `METATUBE_AUTH_TOKEN` | 空 | 路径鉴权 token |
| `METATUBE_REQUEST_TIMEOUT` | `60s` | 抓取请求超时 |
| `METATUBE_MANUAL_LIMIT` | `10` | 手动匹配返回数量 |
| `METATUBE_ENABLE_ACTOR_IMAGES` | `true` | 输出演员头像 |
| `METATUBE_ENABLE_DIRECTORS` | `true` | 输出导演 |
| `METATUBE_ENABLE_RATINGS` | `true` | 输出评分 |
| `METATUBE_ENABLE_REAL_ACTOR_NAMES` | `false` | 通过 AVBASE 尝试替换真实演员名 |
| `METATUBE_ENABLE_BADGES` | `false` | 给中文字幕影片封面加徽章 |
| `METATUBE_BADGE_URL` | `zimu.png` | 徽章图片 |
| `METATUBE_ENABLE_MOVIE_PROVIDER_FILTER` | `false` | 启用影片源过滤和排序 |
| `METATUBE_MOVIE_PROVIDER_FILTER` | 空 | 影片源顺序，例如 `FANZA,JavBus,JAV321` |
| `METATUBE_ENABLE_TITLE_TEMPLATE` | `false` | 启用标题模板 |
| `METATUBE_TITLE_TEMPLATE` | `{number} {title}` | 标题模板 |
| `METATUBE_ENABLE_TITLE_SUBSTITUTION` | `false` | 启用标题替换 |
| `METATUBE_TITLE_SUBSTITUTION_TABLE` | 空 | Base64 替换表，每行 `旧=新` |
| `METATUBE_ENABLE_ACTOR_SUBSTITUTION` | `false` | 启用演员替换 |
| `METATUBE_ACTOR_SUBSTITUTION_TABLE` | 空 | Base64 替换表，每行 `旧=新` |
| `METATUBE_ENABLE_GENRE_SUBSTITUTION` | `false` | 启用类型替换 |
| `METATUBE_GENRE_SUBSTITUTION_TABLE` | 空 | Base64 替换表，每行 `旧=新` |
| `METATUBE_TRANSLATION_MODE` | `Disabled` | 翻译范围 |
| `METATUBE_TRANSLATION_ENGINE` | `Baidu` | 翻译引擎 |
| `METATUBE_TRANSLATION_ENGINE_PARAMETERS` | 空 | 翻译引擎参数 |

标题模板支持：

```text
{provider} {id} {number} {title} {series} {maker} {label} {director} {actors} {first_actor} {year} {date}
```

## 验证

```sh
cd provider-go
go test ./...
```

本机健康检查：

```sh
curl http://127.0.0.1:8080/_metatube/<token>/health
```

## 许可与引用

本仓库是迁移和集成项目，保留上游代码来源说明：

- `metatube-community/metatube-plex-plugins`：MIT License
- `metatube-community/metatube-sdk-go`：Apache-2.0 License

详细来源、提交版本和说明见 [ATTRIBUTION.md](./ATTRIBUTION.md)。
