const test = require("node:test");
const assert = require("node:assert/strict");
const { scoreEntry, normalizeText } = require("../src/knowledge");

test("normalizeText removes punctuation and spaces", () => {
  assert.equal(normalizeText(" 黄精，适合 谁？ "), "黄精适合谁");
});

test("scoreEntry prefers clearly matching faq entries", () => {
  const query = "黄精适合哪些人群吃";
  const good = {
    question: "黄精适合哪些人群吃？",
    answer: "适合容易疲劳、腰膝酸软、经常熬夜的人群。",
    keywords: ["黄精", "人群", "熬夜"],
  };
  const weak = {
    question: "如何修改头像和用户名称？",
    answer: "进入个人中心修改头像。",
    keywords: ["头像", "用户名称"],
  };

  assert.ok(scoreEntry(query, good) > scoreEntry(query, weak));
});
