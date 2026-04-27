---
name: metast-delivery-express-list
description: 早期拆分的 Metast 快递公司列表查询 skill。当前线上建议优先使用统一的 `metast-mcp` skill；只有旧 agent 仍依赖本目录时才使用。
---

# Metast 快递公司列表查询

这是早期拆分出来的快递公司列表 skill。当前项目已经收敛到 `skills/metast-mcp/`，线上维护时优先安装和使用 `metast-mcp`。

如果旧 agent 仍然只安装了本 skill，可以继续用它查询可用快递公司。

## 准备凭证

需要环境变量：

- `METAST_MCP_BASE_URL`
- `METAST_MCP_KEY`
- `METAST_MCP_SECRET`

## 使用方式

```bash
python3 scripts/fetch_delivery_express_list.py
```

## 适用场景

- 用户问支持哪些快递。
- 客服需要查询快递公司名称或编码。

## 输出要求

- 用户泛问时，用中文简要列出可用快递。
- 用户问编码或默认状态时，返回接口里的具体字段。
- API 失败时报告真实错误，不要编造快递数据。

## 维护建议

- 新功能不要继续加到本 skill，统一加到 `skills/metast-mcp/`。
- `references/api.md` 只保留旧 skill 的接口说明。
