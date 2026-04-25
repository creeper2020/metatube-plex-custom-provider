# MetaTube Plex Provider Go

这是一个单体版 Plex Custom Metadata Provider。它直接复用 `metatube-sdk-go` 的抓取、SQLite 缓存和图片处理能力，不再依赖外部 MetaTube API Server。

## 运行

```sh
METATUBE_HOST=0.0.0.0 \
METATUBE_PORT=8080 \
METATUBE_DSN=/home/plex/metatube-provider-go.db \
METATUBE_AUTH_TOKEN=replace-with-a-random-token \
/home/plex/bin/metatube-plex-provider-go
```

Provider 注册地址：

```text
http://host:8080/_metatube/replace-with-a-random-token
```

## 配置

- `METATUBE_HOST`：监听地址，默认 `127.0.0.1`
- `METATUBE_PORT`：监听端口，默认 `8080`
- `METATUBE_DSN`：SQLite 或 PostgreSQL DSN，默认 `/home/plex/metatube-provider-go.db`
- `METATUBE_AUTH_PATH`：路径鉴权前缀，默认 `_metatube`
- `METATUBE_AUTH_TOKEN`：路径鉴权 token，默认空
- `METATUBE_MANUAL_LIMIT`：手动匹配返回数量，默认 `10`
- `METATUBE_ENABLE_ACTOR_IMAGES`：是否抓取演员头像，默认 `true`
- `METATUBE_ENABLE_DIRECTORS`：是否写入导演，默认 `true`
- `METATUBE_ENABLE_RATINGS`：是否写入评分，默认 `true`
- `METATUBE_ENABLE_REAL_ACTOR_NAMES`：是否尝试通过 AVBASE 替换真实演员名，默认 `false`
- `METATUBE_ENABLE_BADGES`：是否给带中文字幕的视频封面叠加徽章，默认 `false`
- `METATUBE_BADGE_URL`：徽章图片，默认 `zimu.png`
- `METATUBE_ENABLE_MOVIE_PROVIDER_FILTER`：是否启用影片源过滤/排序，默认 `false`
- `METATUBE_MOVIE_PROVIDER_FILTER`：影片源顺序，例如 `FANZA,JavBus,JAV321`
- `METATUBE_ENABLE_TITLE_TEMPLATE`：是否启用标题模板，默认 `false`
- `METATUBE_TITLE_TEMPLATE`：标题模板，默认 `{number} {title}`
- `METATUBE_ENABLE_TITLE_SUBSTITUTION`：是否启用标题替换，默认 `false`
- `METATUBE_TITLE_SUBSTITUTION_TABLE`：Base64 编码的替换表，每行 `旧=新`
- `METATUBE_ENABLE_ACTOR_SUBSTITUTION`：是否启用演员替换，默认 `false`
- `METATUBE_ACTOR_SUBSTITUTION_TABLE`：Base64 编码的替换表，每行 `旧=新`
- `METATUBE_ENABLE_GENRE_SUBSTITUTION`：是否启用类型替换，默认 `false`
- `METATUBE_GENRE_SUBSTITUTION_TABLE`：Base64 编码的替换表，每行 `旧=新`
- `METATUBE_TRANSLATION_MODE`：翻译范围，默认 `Disabled`
- `METATUBE_TRANSLATION_ENGINE`：翻译引擎，默认 `Baidu`
- `METATUBE_TRANSLATION_ENGINE_PARAMETERS`：翻译引擎参数，例如 `baidu-app-id=xxx,baidu-app-key=yyy`

## 说明

这个版本只保留一个对 Plex 暴露的 HTTP 服务。图片也由同一个服务代理输出，不再使用 `/v1/images` 后端接口。

标题模板支持这些字段：

```text
{provider} {id} {number} {title} {series} {maker} {label} {director} {actors} {first_actor} {year} {date}
```
