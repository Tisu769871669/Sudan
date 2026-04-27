---
name: metast-product-list
description: 早期拆分的 Metast 商品列表查询 skill。当前线上建议优先使用统一的 `metast-mcp` skill；只有旧 agent 仍依赖本目录时才使用。
---

# Metast 商品列表查询

这是早期拆分出来的商品列表 skill。当前项目已经收敛到 `skills/metast-mcp/`，线上维护时优先安装和使用 `metast-mcp`。

如果旧 agent 仍然只安装了本 skill，可以继续用它查询当前上架商品。

## 准备凭证

需要环境变量：

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

## 使用方式

```bash
python3 scripts/fetch_product_list.py
```

## 适用场景

- 用户问当前有哪些商品。
- 用户问某个商品是否上架。
- 用户问商品价格、规格、库存、状态等实时信息。

## 输出要求

- 用户泛问时，用中文简要归纳商品信息。
- 用户问精确字段时，返回接口里的具体字段。
- API 失败时报告真实错误，不要编造商品数据。

## 维护建议

- 新功能不要继续加到本 skill，统一加到 `skills/metast-mcp/`。
- `references/api.md` 只保留旧 skill 的接口说明。
