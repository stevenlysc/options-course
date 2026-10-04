# Options Course · 期权策略系统课

58 节图文课件，部署在 https://invest.stevenlysc.com/options/

- 课程表（index）：`https://invest.stevenlysc.com/options/`
- 单课地址：`https://invest.stevenlysc.com/options/<slug>`，如 `lesson-1-long-call`

## 工程结构

```
manifest.json              # 58 节课程清单（slug / 中英文名 / 档位 / 分类 / 状态）
lessons/<slug>.body.html   # 单课正文片段
templates/lesson.html      # 单课页面模板
templates/index.html       # 课程表模板
build.py                   # 渲染全部页面 → dist/worker.js（页面内联进 Worker）
deploy_cf.py               # 发布 Worker `options-course` + 确保 /options 路由
```

## 发布新课

1. 在 `manifest.json` 把对应课程 `status` 改为 `published`
2. 新建 `lessons/<slug>.body.html`（照第 1 课的版式写）
3. `python3 build.py && python3 deploy_cf.py`
4. curl 带 `?v=随机` 核验（边缘节点偶发短暂旧缓存）

## 部署说明

- Cloudflare Worker 名：`options-course`
- 路由：`invest.stevenlysc.com/options` 与 `invest.stevenlysc.com/options/*`
- 凭据走 authd surrogates（`custom.cloudflare`），不落盘
