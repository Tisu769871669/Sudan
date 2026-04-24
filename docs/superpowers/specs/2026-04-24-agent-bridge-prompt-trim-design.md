# Agent Bridge Prompt Trim Design

## Goal

Adjust the bridge-layer prompt assembly so that:

1. Persona instructions continue to live in the main system prompt source (`soul.md` / generated system prompt), not repeated again in the bridge layer.
2. The bridge layer's first instruction explicitly tells the agent that the currently available skill is `metast-mcp`.
3. The bridge layer focuses on runtime guidance only: concise replies, do not fabricate, use knowledge hits when relevant, and fall back naturally when knowledge is insufficient.

## Current State

- `node-services/agent-bridge/src/server.js` builds the hidden bridge message in `buildAgentMessage(...)`.
- That message currently:
  - repeats persona-priority instructions such as "优先遵守苏丹人格与回复规则"
  - references "sudan skill" rather than the actual runtime skill name
  - injects the full `stylePrompt` under a persona section, which duplicates behavior already carried by the generated system prompt

## Approved Direction

Use the bridge layer only as a runtime instruction layer.

- Remove repeated persona-priority wording from the bridge preamble.
- Keep the bridge first sentence as an explicit skill notice:
  - current available skill is `metast-mcp`
  - use it first for real-time product, courier, and order queries
- Keep `stylePrompt` available only as supplemental background, not as the centerpiece of the bridge message.
- Preserve the existing history and knowledge-hit sections.

## Prompt Structure

`buildAgentMessage(...)` should be reshaped to:

1. skill availability sentence
2. hidden-context / do-not-expose instruction
3. runtime reply rules
4. optional supplemental prompt block
5. recent history
6. knowledge hits
7. current user message

Suggested wording direction:

- "当前客服可使用的 skill 为 `metast-mcp`。遇到实时商品、快递、订单查询时优先使用它。"
- keep short-reply and no-fabrication rules
- avoid wording that redefines the agent's identity when that identity already exists in the system prompt

## Files In Scope

- `node-services/agent-bridge/src/server.js`
- `node-services/agent-bridge/test/protocol.test.js`

## Verification

- add or update a test that asserts the bridge message starts with the `metast-mcp` availability guidance
- assert the bridge message no longer contains the old repeated persona-priority wording
- run `node --test` in `node-services/agent-bridge`

## Risks

- If some deployments rely on `COLLEAGUE_SKILL_FILE` without a full system prompt, removing too much bridge guidance could weaken tone consistency.
- To reduce that risk, keep `stylePrompt` as supplemental context instead of removing it entirely.

## Decision

For this change, the bridge layer should stop acting like a second persona source and become a lightweight runtime router plus response guardrail.
