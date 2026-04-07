const fs = require("node:fs");
const path = require("node:path");

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[`~!@#$%^&*()_\-+=\[\]{}\\|;:'",.<>/?！？。，、；：“”‘’（）【】《》\s]+/g, "");
}

function cjkBigrams(input) {
  const chars = Array.from(normalizeText(input));
  const result = [];
  for (let index = 0; index < chars.length - 1; index += 1) {
    result.push(chars[index] + chars[index + 1]);
  }
  return result;
}

function overlapCount(a, b) {
  const left = new Set(a);
  let count = 0;
  for (const item of b) {
    if (left.has(item)) {
      count += 1;
    }
  }
  return count;
}

function scoreEntry(query, entry) {
  const question = normalizeText(entry.question);
  const answer = normalizeText(entry.answer);
  const normalizedQuery = normalizeText(query);
  let score = 0;

  if (!normalizedQuery) {
    return 0;
  }

  if (question.includes(normalizedQuery)) {
    score += 8;
  }
  if (normalizedQuery.includes(question) && question.length >= 4) {
    score += 6;
  }

  const keywords = Array.isArray(entry.keywords) ? entry.keywords : [];
  for (const keyword of keywords) {
    const normalizedKeyword = normalizeText(keyword);
    if (normalizedKeyword && normalizedQuery.includes(normalizedKeyword)) {
      score += 3;
    }
  }

  const queryBigrams = cjkBigrams(normalizedQuery);
  score += overlapCount(queryBigrams, cjkBigrams(question));
  score += Math.floor(overlapCount(queryBigrams, cjkBigrams(answer)) / 2);

  return score;
}

function loadKnowledgeFile(absolutePath) {
  const raw = fs.readFileSync(absolutePath, "utf8");
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`Knowledge file must be a JSON array: ${absolutePath}`);
  }
  return parsed;
}

function createKnowledgeStore(filePath) {
  const absolutePath = path.resolve(filePath);
  let cachedMtimeMs = 0;
  let cachedEntries = [];

  function ensureLoaded() {
    const stats = fs.statSync(absolutePath);
    if (stats.mtimeMs !== cachedMtimeMs) {
      cachedEntries = loadKnowledgeFile(absolutePath);
      cachedMtimeMs = stats.mtimeMs;
    }
    return cachedEntries;
  }

  function search(query, options = {}) {
    const entries = ensureLoaded();
    const topK = Number(options.topK || 3);
    const minScore = Number(options.minScore || 3);

    return entries
      .map((entry) => ({
        ...entry,
        score: scoreEntry(query, entry),
      }))
      .filter((entry) => entry.score >= minScore)
      .sort((left, right) => right.score - left.score)
      .slice(0, topK);
  }

  return {
    absolutePath,
    search,
  };
}

module.exports = {
  createKnowledgeStore,
  normalizeText,
  scoreEntry,
};
