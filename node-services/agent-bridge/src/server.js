const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn, spawnSync } = require("node:child_process");
const { createKnowledgeStore } = require("./knowledge");

const ROOT_DIR = path.resolve(__dirname, "..");
const ENV_PATH = path.join(ROOT_DIR, ".env");

loadDotEnv(ENV_PATH);

const config = {
  port: Number(process.env.PORT || 9070),
  token: process.env.AGENT_BRIDGE_TOKEN || "",
  openclawBin: process.env.OPENCLAW_BIN || "openclaw",
  defaultAgentId: process.env.DEFAULT_AGENT_ID || "main",
  timeoutSeconds: Number(process.env.AGENT_TIMEOUT_SECONDS || 120),
  forceLocal: process.env.OPENCLAW_FORCE_LOCAL === "1",
  knowledgeFile: process.env.KNOWLEDGE_FILE
    ? path.resolve(ROOT_DIR, process.env.KNOWLEDGE_FILE)
    : path.resolve(ROOT_DIR, "../../knowledge/faq.json"),
  systemPromptFile: process.env.SYSTEM_PROMPT_FILE
    ? path.resolve(ROOT_DIR, process.env.SYSTEM_PROMPT_FILE)
    : path.resolve(ROOT_DIR, "../../build/generated/system_prompt.md"),
  kbTopK: Number(process.env.KB_TOP_K || 3),
  kbMinScore: Number(process.env.KB_MIN_SCORE || 3),
  maxHistoryMessages: Number(process.env.MAX_HISTORY_MESSAGES || 8),
  logLevel: process.env.LOG_LEVEL || "info",
};

config.openclawBin = resolveExecutable(config.openclawBin);

const knowledgeStore = createKnowledgeStore(config.knowledgeFile);
const systemPromptStore = createTextFileStore(config.systemPromptFile);

function loadDotEnv(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }
  const raw = fs.readFileSync(filePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.trim().startsWith("#")) {
      continue;
    }
    const index = line.indexOf("=");
    if (index === -1) {
      continue;
    }
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim();
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

function log(level, message, extra = undefined) {
  const weights = { error: 0, warn: 1, info: 2, debug: 3 };
  if ((weights[level] ?? 2) > (weights[config.logLevel] ?? 2)) {
    return;
  }
  const payload = extra ? ` ${JSON.stringify(extra)}` : "";
  console.log(`[agent-bridge] ${level}: ${message}${payload}`);
}

function createTextFileStore(filePath) {
  const absolutePath = path.resolve(filePath);
  let cachedMtimeMs = 0;
  let cachedValue = "";

  function read() {
    const stats = fs.statSync(absolutePath);
    if (stats.mtimeMs !== cachedMtimeMs) {
      cachedValue = fs.readFileSync(absolutePath, "utf8").trim();
      cachedMtimeMs = stats.mtimeMs;
    }
    return cachedValue;
  }

  return {
    absolutePath,
    read,
  };
}

function resolveExecutable(input) {
  if (!input || path.isAbsolute(input)) {
    return input;
  }

  const locator = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(locator, [input], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.status === 0) {
    const foundList = result.stdout
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    if (foundList.length) {
      if (process.platform === "win32") {
        const cmdShim = foundList.find((item) => item.toLowerCase().endsWith(".cmd"));
        if (cmdShim) {
          return cmdShim;
        }
      }
      return foundList[0];
    }
  }
  return input;
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 1024 * 1024) {
        reject(createHttpError(413, "Request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!raw) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(createHttpError(400, "Invalid JSON body"));
      }
    });
    req.on("error", (error) => reject(error));
  });
}

function createHttpError(statusCode, message) {
  const error = new Error(message);
  error.statusCode = statusCode;
  return error;
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload, null, 2);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function authenticate(req) {
  if (!config.token) {
    return true;
  }
  const auth = req.headers.authorization || "";
  return auth === `Bearer ${config.token}`;
}

function normalizeMessage(item) {
  if (!item || typeof item !== "object") {
    return null;
  }
  const role = String(item.role || "").trim() || "user";
  const text = [item.text, item.content, item.message]
    .find((value) => typeof value === "string" && value.trim())
    ?.trim();
  if (!text) {
    return null;
  }
  return { role, text };
}

function extractConversation(payload) {
  const conversationId =
    String(
      payload.conversationId ||
        payload.conversation_id ||
        payload.sessionId ||
        payload.session_id ||
        ""
    ).trim();
  if (!conversationId) {
    throw createHttpError(400, "conversationId or conversation_id is required");
  }

  const nestedContent = payload.content;
  const topLevelMessageList = Array.isArray(payload.messageList)
    ? payload.messageList
    : [];
  const nestedMessageList =
    nestedContent && typeof nestedContent === "object" && Array.isArray(nestedContent.messageList)
      ? nestedContent.messageList
      : [];
  const history = [...topLevelMessageList, ...nestedMessageList]
    .map(normalizeMessage)
    .filter(Boolean)
    .slice(-config.maxHistoryMessages);

  let userMessage = [payload.message, payload.content, nestedContent?.message]
    .find((value) => typeof value === "string" && value.trim())
    ?.trim();

  if (!userMessage) {
    const lastUser = [...history].reverse().find((item) => item.role === "user");
    userMessage = lastUser?.text || "";
  }

  if (!userMessage) {
    throw createHttpError(400, "message or content is required");
  }

  return {
    conversationId,
    history,
    userMessage,
  };
}

function buildSessionId(agentId, conversationId) {
  const trimmed = String(conversationId).trim();
  const sanitized = trimmed.replace(/[^a-zA-Z0-9:_-]/g, "_");
  const base = sanitized.slice(0, 80);
  const hash = crypto.createHash("sha1").update(trimmed).digest("hex").slice(0, 10);
  return `bridge:${agentId}:${base || "session"}:${hash}`;
}

function formatHistory(history) {
  if (!history.length) {
    return "无额外历史消息。";
  }
  return history
    .map((item, index) => `${index + 1}. ${item.role}: ${item.text}`)
    .join("\n");
}

function formatKnowledgeHits(hits) {
  if (!hits.length) {
    return "无命中知识条目。";
  }
  return hits
    .map((item, index) => {
      return [
        `条目 ${index + 1}`,
        `问题：${item.question}`,
        `答案：${item.answer}`,
        `分类：${item.category || ""}`,
        `关键词：${Array.isArray(item.keywords) ? item.keywords.join("、") : ""}`,
      ].join("\n");
    })
    .join("\n\n");
}

function buildAgentMessage({ systemPrompt, userMessage, history, knowledgeHits }) {
  return [
    "以下是桥接层提供的隐藏上下文，请直接回复用户，不要提到“桥接层”“上下文”“资料来源”这类字眼。",
    "你必须优先遵守下方“苏丹人格与回复规则”。如果它与当前 agent 的默认身份冲突，以这份规则为准。",
    "回复务必更口语、更短。优先 1 到 3 句话，能短就短。",
    "除非用户明确追问，不要一次讲太多，不要写成长段说明文。",
    "如果知识命中不相关，请忽略，不要硬答。",
    "如果知识不足，请自然兜底并引导人工或进一步描述。",
    "",
    "【苏丹人格与回复规则】",
    systemPrompt || "未提供额外人格规则。",
    "",
    "【最近消息】",
    formatHistory(history),
    "",
    "【命中的知识条目】",
    formatKnowledgeHits(knowledgeHits),
    "",
    "【用户本轮消息】",
    userMessage,
  ].join("\n");
}

function runOpenClawAgent({ agentId, sessionId, message }) {
  return new Promise((resolve, reject) => {
    const args = [
      "agent",
      "--agent",
      agentId,
      "--session-id",
      sessionId,
      "--message",
      message,
      "--timeout",
      String(config.timeoutSeconds),
    ];

    if (config.forceLocal) {
      args.push("--local");
    }

    const env = {
      ...process.env,
      OPENCLAW_HIDE_BANNER: "1",
      OPENCLAW_SUPPRESS_NOTES: "1",
      NO_COLOR: "1",
    };

    const child =
      process.platform === "win32"
        ? spawn(config.openclawBin, args, {
            cwd: ROOT_DIR,
            env,
            shell: config.openclawBin.toLowerCase().endsWith(".cmd"),
            windowsHide: true,
          })
        : spawn(
            "bash",
            [
              "-lc",
              [
                "source ~/.profile >/dev/null 2>&1 || true",
                "source ~/.bashrc >/dev/null 2>&1 || true",
                "exec " + shellJoin([config.openclawBin, ...args]),
              ].join("; "),
            ],
            {
              cwd: ROOT_DIR,
              env,
              windowsHide: true,
            }
          );

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", (error) => reject(error));
    child.on("close", (code) => {
      if (code !== 0) {
        reject(
          createHttpError(
            502,
            `openclaw agent failed with code ${code}: ${(stderr || stdout).trim() || "unknown error"}`
          )
        );
        return;
      }
      resolve(parseAgentOutput(stdout, stderr));
    });
  });
}

function shellJoin(parts) {
  return parts.map(shellEscape).join(" ");
}

function shellEscape(value) {
  const input = String(value ?? "");
  if (!input) {
    return "''";
  }
  return `'${input.replace(/'/g, `'\"'\"'`)}'`;
}

function parseAgentOutput(stdout, stderr) {
  const combined = [stdout, stderr]
    .filter(Boolean)
    .join("\n")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const mediaUrls = [];
  const replyLines = [];

  for (const line of combined) {
    if (line.startsWith("MEDIA:")) {
      mediaUrls.push(line.slice("MEDIA:".length).trim());
      continue;
    }
    if (
      line.startsWith("🦞") ||
      line.startsWith("[gateway]") ||
      line.startsWith("[plugins]") ||
      line.startsWith("Docs: ") ||
      line.startsWith("Start with:")
    ) {
      continue;
    }
    replyLines.push(line);
  }

  return {
    reply: replyLines.join("\n").trim(),
    mediaUrls,
    rawStdout: stdout.trim(),
    rawStderr: stderr.trim(),
  };
}

function matchRoute(req) {
  const url = new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`);
  if (req.method === "GET" && url.pathname === "/health") {
    return { type: "health", url };
  }
  if (req.method === "POST" && url.pathname === "/api/agents/chat") {
    return { type: "chat", agentId: config.defaultAgentId, url };
  }

  const match = /^\/api\/agents\/([^/]+)\/chat$/.exec(url.pathname);
  if (req.method === "POST" && match) {
    return {
      type: "chat",
      agentId: decodeURIComponent(match[1]),
      url,
    };
  }
  return null;
}

async function handleChat(req, res, agentId) {
  if (!authenticate(req)) {
    sendJson(res, 401, { error: "Unauthorized" });
    return;
  }

  const payload = await readJsonBody(req);
  const { conversationId, history, userMessage } = extractConversation(payload);
  const sessionId = buildSessionId(agentId, conversationId);
  const knowledgeHits = knowledgeStore.search(userMessage, {
    topK: config.kbTopK,
    minScore: config.kbMinScore,
  });
  const systemPrompt = systemPromptStore.read();
  const message = buildAgentMessage({
    systemPrompt,
    userMessage,
    history,
    knowledgeHits,
  });

  log("info", "handling chat request", {
    agentId,
    conversationId,
    sessionId,
    knowledgeHits: knowledgeHits.length,
  });

  const result = await runOpenClawAgent({
    agentId,
    sessionId,
    message,
  });

  sendJson(res, 200, {
    agentId,
    conversationId,
    sessionId,
    reply: result.reply,
    mediaUrls: result.mediaUrls,
    knowledgeHits: knowledgeHits.map((item) => ({
      id: item.id,
      question: item.question,
      score: item.score,
      category: item.category,
    })),
  });
}

const server = http.createServer(async (req, res) => {
  try {
    const route = matchRoute(req);
    if (!route) {
      sendJson(res, 404, { error: "Not found" });
      return;
    }

    if (route.type === "health") {
      sendJson(res, 200, {
        ok: true,
        service: "sudan-agent-bridge",
        defaultAgentId: config.defaultAgentId,
        knowledgeFile: knowledgeStore.absolutePath,
        systemPromptFile: systemPromptStore.absolutePath,
        openclawBin: config.openclawBin,
      });
      return;
    }

    await handleChat(req, res, route.agentId);
  } catch (error) {
    const statusCode = error.statusCode || 500;
    log("error", "request failed", {
      message: error.message,
      statusCode,
    });
    sendJson(res, statusCode, {
      error: error.message || "Internal server error",
    });
  }
});

server.listen(config.port, () => {
  log("info", "agent bridge listening", {
    port: config.port,
    defaultAgentId: config.defaultAgentId,
    knowledgeFile: knowledgeStore.absolutePath,
  });
});
