const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const indexHtml = fs.readFileSync(path.join(repoRoot, "web", "index.html"), "utf8");
const appJs = fs.readFileSync(path.join(repoRoot, "web", "app.js"), "utf8");

const requiredDomIds = [
  "practiceModeTextBtn",
  "practiceModeVoiceBtn",
  "voicePracticeBlock",
  "voiceStatusText",
  "voiceChannelValue",
  "voiceStartBtn",
  "voiceStopBtn",
  "voiceTranscriptList",
];

const requiredAppSnippets = [
  "const voiceState =",
  "function setPracticeMode(",
  "async function startVoicePractice(",
  "async function stopVoicePractice(",
  "async function initializeVoiceClient(",
  "async function loadAgoraAgentToolkit(",
  "async function syncVoiceTranscriptTurns(",
  "AgoraVoiceAIEvents.TRANSCRIPT_UPDATED",
  "/api/v1/voice/sessions",
  "/transcripts",
  "/stop",
];

const requiredVendorFiles = [
  "web/vendor/agora/agora-rtc-sdk-ng/AgoraRTC_N-production.js",
  "web/vendor/agora/agora-rtm/agora-rtm.js",
  "web/vendor/agora/agora-agent-client-toolkit/index.mjs",
];

const missing = [];

requiredDomIds.forEach((id) => {
  if (!indexHtml.includes(`id="${id}"`)) {
    missing.push(`missing DOM id: ${id}`);
  }
});

requiredAppSnippets.forEach((snippet) => {
  if (!appJs.includes(snippet)) {
    missing.push(`missing app contract: ${snippet}`);
  }
});

requiredVendorFiles.forEach((relativePath) => {
  if (!fs.existsSync(path.join(repoRoot, relativePath))) {
    missing.push(`missing vendor asset: ${relativePath}`);
  }
});

if (missing.length) {
  console.error(missing.join("\n"));
  process.exit(1);
}

console.log("voice pwa contract ok");
