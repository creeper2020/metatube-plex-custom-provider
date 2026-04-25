# MetaTube Custom Metadata Provider

这是面向 Plex `Custom Metadata Providers` 的 MetaTube 迁移版本。它是一个独立 HTTP 服务，不再使用旧 Plex Python 插件运行时。

## 当前范围

- 支持 Movie 类型 Provider。
- 支持 `/library/metadata/matches` 匹配。
- 支持 `/library/metadata/{ratingKey}` 元数据读取。
- 复用 MetaTube 后端的电影搜索、电影详情、图片、演员头像和翻译接口。
- 番号精确命中多个源时，会把多个源合并成第一候选；手动匹配时仍保留单源候选作为备选。
- 保留旧插件的大部分环境配置能力，包括标题模板、演员/类型替换、真实演员名、Provider 过滤和可选翻译。

合并规则：

- 标题、封面、背景图、厂商等冲突字段默认使用优先源。
- 演员、类型、预览图等列表字段按源顺序去重合并。
- 评分、时长等字段使用第一个有效值补齐。
- 优先源顺序可以通过 `METATUBE_MOVIE_PROVIDER_FILTER` 控制。

旧插件里的 Collections、Reviews 和 Trailer Extras 暂未迁移。Collections 需要额外的 `collection` feature 和 children endpoint；Reviews 和 Trailer Extras 在 Plex 当前公开的 Metadata Provider schema 中还没有稳定的对应字段。

## 运行

```bash
cd provider
export METATUBE_API_SERVER="https://api.metatube.internal"
export METATUBE_API_TOKEN="your-token"
python -m metatube_provider
```

默认监听 `http://127.0.0.1:8080`。如果 PMS 在 Docker 或其他机器上运行，再把 `METATUBE_HOST` 改成 PMS 能访问到的内网地址。

也可以把配置写入 `provider/.env`。该文件已被 `.gitignore` 忽略，服务启动时会自动读取。

公网部署时建议开启路径 token：

```env
METATUBE_HOST=0.0.0.0
METATUBE_AUTH_PATH=_metatube
METATUBE_AUTH_TOKEN=your-long-random-token
```

然后在 Plex 里注册：

```text
http://your-host:8080/_metatube/your-long-random-token
```

未带 token 前缀的请求会返回 404。

也可以用 Docker：

```bash
cd provider
docker build -t metatube-provider .
docker run --rm -p 8080:8080 \
  -e METATUBE_API_SERVER="https://api.metatube.internal" \
  -e METATUBE_API_TOKEN="your-token" \
  metatube-provider
```

## 注册到 Plex

需要 Plex Media Server 1.43.0 或更新版本。

1. 打开 Plex Web。
2. 进入 `Settings -> Metadata Agents -> Add Provider`。
3. 填入 Provider URL，例如 `http://127.0.0.1:8080`。如果 Provider 跑在 Docker 或其他机器上，使用 PMS 能访问到的地址。
4. 在 Metadata Agents 页面新建 Agent，把 `MetaTube Movie Provider` 设置为 Primary。
5. 新建 Movie Library，在 Advanced 里选择这个 Agent。

Provider 根路径返回的 identifier 是：

```text
tv.plex.agents.custom.metatube.movie
```

## 测试

```bash
python -m unittest discover -s tests -t .
```
