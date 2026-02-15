function byId(id) {
  return document.getElementById(id);
}

const DEFAULT_SUPABASE_URL = "https://wiafjgjfdrajlxnlkray.supabase.co";
const DEFAULT_SUPABASE_ANON_KEY = "sb_publishable_EvEX2Hlp9e7SU4FcbpIrzQ_uusY6M87";
const RUNTIME_STATE_KEY = "runtime_state_v2";
const HISTORY_VIEW_STATE_KEY = "history_view_state_v1";
const HISTORY_DEFAULT_LIMIT = 10;
const PWA_ENABLED_KEY = "pwa_enabled_v1";
const PWA_DEFAULT_ENABLED = true;
const HISTORY_LIST_SNAPSHOT_KEY = "history_list_snapshot_v1";
const HISTORY_DETAIL_SNAPSHOT_PREFIX = "history_detail_snapshot_v1:";
const HISTORY_SNAPSHOT_MAX_ITEMS = 20;

function resolvePwaEnabled() {
  const query = new URLSearchParams(window.location.search);
  const queryValue = query.get("pwa");
  if (queryValue === "0") return false;
  if (queryValue === "1") return true;

  const storedValue = localStorage.getItem(PWA_ENABLED_KEY);
  if (storedValue === "0") return false;
  if (storedValue === "1") return true;
  return PWA_DEFAULT_ENABLED;
}

const TEMPLATE_PRESETS = {
  peer_delay: {
    title: "和同事沟通延期风险",
    goal: "确认新的里程碑并明确责任",
    context: "这个需求已经两次延期，影响发布节奏。",
    template_id: "PEER_FEEDBACK",
    counterparty_role: "PEER",
    relationship_level: "TENSE",
    power_dynamic: "PEER_LEVEL",
    pain_points: ["对方容易防御", "我会急躁"],
  },
  manager_alignment: {
    title: "和上级对齐当前优先级",
    goal: "明确本周最重要目标并重新分配任务",
    context: "我当前并行任务过多，多个项目都在催进度，需要和上级重新对齐优先级。",
    template_id: "MANAGER_ALIGNMENT",
    counterparty_role: "MANAGER",
    relationship_level: "NEUTRAL",
    power_dynamic: "COUNTERPART_HIGHER",
    pain_points: ["担心被认为效率低", "不敢明确边界"],
  },
  cross_team_conflict: {
    title: "跨团队交付边界冲突",
    goal: "澄清双方职责和依赖时间点",
    context: "跨团队接口交付时间反复变化，双方都认为责任在对方。",
    template_id: "CROSS_TEAM_CONFLICT",
    counterparty_role: "OTHER",
    relationship_level: "TENSE",
    power_dynamic: "PEER_LEVEL",
    pain_points: ["语气容易升级", "目标容易跑偏"],
  },
  custom: {
    title: "自定义沟通场景",
    goal: "说清我的需要并提出可执行请求",
    context: "请输入你真实遇到的沟通背景。",
    template_id: "CUSTOM",
    counterparty_role: "OTHER",
    relationship_level: "NEUTRAL",
    power_dynamic: "PEER_LEVEL",
    pain_points: ["表达不够具体"],
  },
};

const DEV_CONTEXT = isDevContext();
const pwa = {
  enabled: resolvePwaEnabled(),
  deferredInstallPrompt: null,
  registration: null,
  updateReady: false,
  networkBarTimer: null,
  isReloadingForUpdate: false,
};

const state = {
  sceneId: "",
  sessionId: "",
  turn: 0,
  selectedTurn: 0,
  lastUserMessageId: "",
  history: [],
  summary: null,
  reflection: null,
  reflectionId: "",
  historyOffset: 0,
  historyTotal: 0,
  historyLimit: HISTORY_DEFAULT_LIMIT,
};

function isDevContext() {
  const host = window.location.hostname || "";
  const query = new URLSearchParams(window.location.search);
  return (
    query.get("dev") === "1" ||
    host === "localhost" ||
    host === "127.0.0.1" ||
    host.endsWith(".local")
  );
}

function ensureUserId() {
  const existing = localStorage.getItem("mock_user_id");
  if (existing) return existing;
  const uid = crypto.randomUUID();
  localStorage.setItem("mock_user_id", uid);
  return uid;
}

function normalizeApiBaseUrl(raw) {
  return raw.trim().replace(/\/+$/, "");
}

function parseJson(text, fallback = {}) {
  try {
    return text ? JSON.parse(text) : fallback;
  } catch {
    return fallback;
  }
}

function isOfflineLikeError(error) {
  const message = String(error?.message || error || "");
  const normalized = message.toLowerCase();
  return (
    normalized.includes("offline") ||
    normalized.includes("failed to fetch") ||
    normalized.includes("networkerror") ||
    normalized.includes("service unavailable")
  );
}

function persistHistoryListSnapshot(items, meta = {}) {
  const normalizedItems = Array.isArray(items) ? items.slice(0, HISTORY_SNAPSHOT_MAX_ITEMS) : [];
  const payload = {
    items: normalizedItems,
    total: Number(meta.total || normalizedItems.length),
    limit: Number(meta.limit || normalizedItems.length),
    offset: Number(meta.offset || 0),
    updated_at: new Date().toISOString(),
  };
  localStorage.setItem(HISTORY_LIST_SNAPSHOT_KEY, JSON.stringify(payload));
}

function loadHistoryListSnapshot() {
  const raw = localStorage.getItem(HISTORY_LIST_SNAPSHOT_KEY);
  if (!raw) return null;
  const parsed = parseJson(raw, null);
  if (!parsed || typeof parsed !== "object") return null;
  return parsed;
}

function persistHistoryDetailSnapshot(sessionId, payload) {
  if (!sessionId || !payload || typeof payload !== "object") return;
  localStorage.setItem(
    `${HISTORY_DETAIL_SNAPSHOT_PREFIX}${sessionId}`,
    JSON.stringify({
      ...payload,
      _snapshot_saved_at: new Date().toISOString(),
    })
  );
}

function loadHistoryDetailSnapshot(sessionId) {
  if (!sessionId) return null;
  const raw = localStorage.getItem(`${HISTORY_DETAIL_SNAPSHOT_PREFIX}${sessionId}`);
  if (!raw) return null;
  const parsed = parseJson(raw, null);
  if (!parsed || typeof parsed !== "object") return null;
  return parsed;
}

function persistPwaEnabled(enabled) {
  localStorage.setItem(PWA_ENABLED_KEY, enabled ? "1" : "0");
}

function setPwaModeBadge(text) {
  const el = byId("pwaModeValue");
  if (!el) return;
  el.textContent = text;
}

function setPwaNetworkBar(text, tone = "offline", options = {}) {
  const { autoHideMs = 0 } = options;
  const bar = byId("pwaNetworkBar");
  if (!bar) return;
  bar.textContent = text;
  bar.classList.remove("is-hidden", "is-online");
  if (tone === "online") {
    bar.classList.add("is-online");
  }
  if (pwa.networkBarTimer) {
    window.clearTimeout(pwa.networkBarTimer);
    pwa.networkBarTimer = null;
  }
  if (autoHideMs > 0) {
    pwa.networkBarTimer = window.setTimeout(() => {
      bar.classList.add("is-hidden");
      pwa.networkBarTimer = null;
    }, autoHideMs);
  }
}

function hidePwaNetworkBar() {
  const bar = byId("pwaNetworkBar");
  if (!bar) return;
  if (pwa.networkBarTimer) {
    window.clearTimeout(pwa.networkBarTimer);
    pwa.networkBarTimer = null;
  }
  bar.classList.add("is-hidden");
}

function updatePwaActionButtons() {
  const installBtn = byId("installAppBtn");
  const updateBtn = byId("updateAppBtn");
  if (installBtn) {
    const canInstall = pwa.enabled && Boolean(pwa.deferredInstallPrompt);
    installBtn.classList.toggle("is-hidden", !canInstall);
  }
  if (updateBtn) {
    const hasUpdate = pwa.enabled && pwa.updateReady;
    updateBtn.classList.toggle("is-hidden", !hasUpdate);
  }
}

function refreshPwaModeBadge() {
  if (!pwa.enabled) {
    setPwaModeBadge("DISABLED");
    return;
  }
  if (!("serviceWorker" in navigator)) {
    setPwaModeBadge("UNSUPPORTED");
    return;
  }
  setPwaModeBadge("ENABLED");
}

function refreshPwaNetworkState({ showOnlineHint = false } = {}) {
  if (!pwa.enabled) {
    hidePwaNetworkBar();
    return;
  }
  if (!navigator.onLine) {
    setPwaNetworkBar("当前离线，可浏览缓存页面；提交数据需恢复网络。", "offline");
    return;
  }
  if (showOnlineHint) {
    setPwaNetworkBar("网络已恢复，可继续在线练习。", "online", { autoHideMs: 2800 });
    return;
  }
  hidePwaNetworkBar();
}

function bindPwaRuntimeSignals() {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    pwa.deferredInstallPrompt = event;
    updatePwaActionButtons();
  });

  window.addEventListener("appinstalled", () => {
    pwa.deferredInstallPrompt = null;
    updatePwaActionButtons();
    setNotice("应用已安装，可从桌面直接打开。", "success");
  });

  window.addEventListener("offline", () => refreshPwaNetworkState());
  window.addEventListener("online", () => refreshPwaNetworkState({ showOnlineHint: true }));
}

function markPwaUpdateReady() {
  pwa.updateReady = true;
  updatePwaActionButtons();
  setPwaNetworkBar("检测到新版本，可点击“更新版本”完成切换。", "online");
}

function bindServiceWorkerUpdateEvents(registration) {
  if (!registration) return;
  if (registration.waiting) {
    markPwaUpdateReady();
  }
  registration.addEventListener("updatefound", () => {
    const worker = registration.installing;
    if (!worker) return;
    worker.addEventListener("statechange", () => {
      if (worker.state === "installed" && navigator.serviceWorker.controller) {
        markPwaUpdateReady();
      }
    });
  });
}

async function unregisterAllServiceWorkers() {
  if (!("serviceWorker" in navigator)) return 0;
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.map((item) => item.unregister()));
  return registrations.length;
}

async function registerPwaServiceWorker() {
  if (!pwa.enabled) return;
  if (!("serviceWorker" in navigator)) return;
  const registration = await navigator.serviceWorker.register("./sw.js", { scope: "./" });
  pwa.registration = registration;
  bindServiceWorkerUpdateEvents(registration);
}

async function applyPwaUpdate() {
  if (!pwa.registration) {
    throw new Error("尚未获取 Service Worker 注册信息");
  }
  if (!pwa.registration.waiting) {
    await pwa.registration.update();
  }
  if (!pwa.registration.waiting) {
    setPwaNetworkBar("当前已经是最新版本。", "online", { autoHideMs: 2600 });
    pwa.updateReady = false;
    updatePwaActionButtons();
    return;
  }
  pwa.registration.waiting.postMessage({ type: "SKIP_WAITING" });
}

async function promptPwaInstall() {
  const prompt = pwa.deferredInstallPrompt;
  if (!prompt) {
    throw new Error("当前环境暂不支持安装提示");
  }
  await prompt.prompt();
  pwa.deferredInstallPrompt = null;
  updatePwaActionButtons();
}

async function setPwaEnabled(enabled) {
  persistPwaEnabled(enabled);
  pwa.enabled = enabled;
  refreshPwaModeBadge();
  updatePwaActionButtons();
}

async function initPwaRuntime() {
  bindPwaRuntimeSignals();
  refreshPwaModeBadge();
  updatePwaActionButtons();
  refreshPwaNetworkState();

  if (!pwa.enabled) {
    await unregisterAllServiceWorkers().catch(() => {});
    return;
  }
  if (!("serviceWorker" in navigator)) {
    setPwaNetworkBar("当前浏览器不支持 Service Worker，无法启用离线能力。", "offline");
    return;
  }

  await registerPwaServiceWorker();
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (pwa.isReloadingForUpdate) return;
    pwa.isReloadingForUpdate = true;
    window.location.reload();
  });
}

function setOutput(value) {
  byId("output").textContent = JSON.stringify(value, null, 2);
}

function setNotice(message, tone = "info") {
  const el = byId("noticeBar");
  el.textContent = message;
  el.classList.remove("is-hidden", "is-success", "is-warning", "is-error");
  if (tone === "success") {
    el.classList.add("is-success");
  } else if (tone === "warning") {
    el.classList.add("is-warning");
  } else if (tone === "error") {
    el.classList.add("is-error");
  }
}

function clearNotice() {
  const el = byId("noticeBar");
  el.textContent = "";
  el.classList.add("is-hidden");
  el.classList.remove("is-success", "is-warning", "is-error");
}

function applyModeVisibility() {
  document.querySelectorAll("[data-dev-only]").forEach((el) => {
    el.classList.toggle("is-hidden", !DEV_CONTEXT);
  });
}

function refreshAuthModeBadge() {
  const mode = byId("authMode")?.value || "supabase";
  byId("currentAuthMode").textContent = mode;
}

function setAuthMode(mode) {
  const normalized = mode === "mock" ? "mock" : "supabase";
  byId("authMode").value = normalized;
  localStorage.setItem("auth_mode", normalized);
  refreshAuthModeBadge();
  updateStepState();
}

function updateStepState() {
  const stepAuth = byId("stepAuth");
  const stepPractice = byId("stepPractice");
  const stepReview = byId("stepReview");

  const mode = byId("authMode").value || "supabase";
  const authDone = mode === "mock" || Boolean(byId("supabaseAccessToken").value.trim());
  const practiceDone = Boolean(state.sessionId && state.turn > 0);
  const reviewDone = Boolean(state.summary || state.reflectionId);

  stepAuth.classList.toggle("is-done", authDone);
  stepPractice.classList.toggle("is-done", practiceDone);
  stepReview.classList.toggle("is-done", reviewDone);

  stepAuth.classList.remove("is-active");
  stepPractice.classList.remove("is-active");
  stepReview.classList.remove("is-active");

  if (!authDone) {
    stepAuth.classList.add("is-active");
  } else if (!practiceDone) {
    stepPractice.classList.add("is-active");
  } else {
    stepReview.classList.add("is-active");
  }
}

function updateRuntimeMeta() {
  byId("sceneIdValue").textContent = state.sceneId || "-";
  byId("sessionIdValue").textContent = state.sessionId || "-";
  byId("currentTurnValue").textContent = String(state.turn || 0);
}

function persistRuntimeState() {
  localStorage.setItem(
    RUNTIME_STATE_KEY,
    JSON.stringify({
      sceneId: state.sceneId,
      sessionId: state.sessionId,
      turn: state.turn,
      selectedTurn: state.selectedTurn,
      lastUserMessageId: state.lastUserMessageId,
      history: state.history,
      summary: state.summary,
      reflection: state.reflection,
      reflectionId: state.reflectionId,
    })
  );
}

function hydrateRuntimeState() {
  const raw = localStorage.getItem(RUNTIME_STATE_KEY);
  if (!raw) return;
  const parsed = parseJson(raw, null);
  if (!parsed || typeof parsed !== "object") return;

  state.sceneId = parsed.sceneId || "";
  state.sessionId = parsed.sessionId || "";
  state.turn = Number(parsed.turn || 0);
  state.selectedTurn = Number(parsed.selectedTurn || 0);
  state.lastUserMessageId = parsed.lastUserMessageId || "";
  state.history = Array.isArray(parsed.history) ? parsed.history : [];
  state.summary = parsed.summary || null;
  state.reflection = parsed.reflection || null;
  state.reflectionId = parsed.reflectionId || "";
}

function resetRuntimeState() {
  state.sceneId = "";
  state.sessionId = "";
  state.turn = 0;
  state.selectedTurn = 0;
  state.lastUserMessageId = "";
  state.history = [];
  state.summary = null;
  state.reflection = null;
  state.reflectionId = "";
  persistRuntimeState();
  renderHistory();
  renderSummary();
  renderReflectionMeta();
  applyReflectionToForm(null);
  clearFeedbackPanel();
  updateRuntimeMeta();
  updateStepState();
}

function getConfig(options = {}) {
  const { requireAuthToken = true, requireMockUser = true } = options;
  const apiBaseUrl = normalizeApiBaseUrl(byId("apiBaseUrl").value || window.location.origin);
  const authMode = DEV_CONTEXT ? byId("authMode").value || "supabase" : "supabase";
  const userId = byId("mockUserId").value.trim();

  const config = {
    apiBaseUrl,
    authMode,
    userId,
    supabaseUrl: normalizeApiBaseUrl(byId("supabaseUrl").value || ""),
    supabaseAnonKey: byId("supabaseAnonKey").value.trim(),
    supabaseEmail: byId("supabaseEmail").value.trim(),
    supabasePassword: byId("supabasePassword").value,
    supabaseAccessToken: byId("supabaseAccessToken").value.trim(),
  };

  if (config.authMode === "mock" && requireMockUser && !config.userId) {
    throw new Error("Mock User UUID 不能为空");
  }
  if (config.authMode === "supabase" && requireAuthToken && !config.supabaseAccessToken) {
    throw new Error("请先登录获取 Access Token");
  }

  return config;
}

function authHeaders(config) {
  if (config.authMode === "supabase") {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.supabaseAccessToken}`,
    };
  }
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer mock_${config.userId}`,
  };
}

async function callApi(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  const data = parseJson(text, text ? { raw: text } : {});

  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
  }
  return data;
}

function getCurrentPreset() {
  const key = byId("templatePreset").value;
  return TEMPLATE_PRESETS[key] || TEMPLATE_PRESETS.peer_delay;
}

function applyTemplatePreset() {
  const key = byId("templatePreset").value;
  const preset = TEMPLATE_PRESETS[key] || TEMPLATE_PRESETS.peer_delay;
  if (key !== "custom") {
    byId("sceneTitle").value = preset.title;
    byId("sceneGoal").value = preset.goal;
    byId("sceneContext").value = preset.context;
  }
}

async function createScene(config) {
  const preset = getCurrentPreset();
  const payload = {
    title: byId("sceneTitle").value.trim(),
    template_id: preset.template_id,
    counterparty_role: preset.counterparty_role,
    relationship_level: preset.relationship_level,
    goal: byId("sceneGoal").value.trim(),
    pain_points: preset.pain_points,
    context: byId("sceneContext").value.trim(),
    power_dynamic: preset.power_dynamic,
  };

  if (!payload.title || !payload.goal || !payload.context) {
    throw new Error("请先完整填写场景标题、目标和背景");
  }

  return callApi(`${config.apiBaseUrl}/api/v1/scenes`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify(payload),
  });
}

async function createSession(config, sceneId) {
  const targetTurns = Number(byId("targetTurns").value || 6);
  return callApi(`${config.apiBaseUrl}/api/v1/sessions`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify({ scene_id: sceneId, target_turns: targetTurns }),
  });
}

async function sendSessionMessage(config, sessionId, content) {
  return callApi(`${config.apiBaseUrl}/api/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify({
      client_message_id: crypto.randomUUID(),
      content,
    }),
  });
}

function renderFeedback(messageResponse) {
  if (!messageResponse) return;
  byId("assistantReply").textContent = messageResponse.assistant_message?.content || "-";
  byId("feedbackOverall").textContent = String(messageResponse.feedback?.overall_score ?? "-");
  byId("feedbackRisk").textContent = messageResponse.feedback?.risk_level || "-";
  byId("nextSentence").textContent = messageResponse.feedback?.next_best_sentence || "-";

  const ofnr = messageResponse.feedback?.ofnr;
  byId("ofnrObservation").textContent = formatOfnr(ofnr?.observation);
  byId("ofnrFeeling").textContent = formatOfnr(ofnr?.feeling);
  byId("ofnrNeed").textContent = formatOfnr(ofnr?.need);
  byId("ofnrRequest").textContent = formatOfnr(ofnr?.request);
}

function clearFeedbackPanel() {
  byId("assistantReply").textContent = "发送一条消息后，这里会显示对方回复。";
  byId("feedbackOverall").textContent = "-";
  byId("feedbackRisk").textContent = "-";
  byId("nextSentence").textContent = "-";
  byId("ofnrObservation").textContent = "-";
  byId("ofnrFeeling").textContent = "-";
  byId("ofnrNeed").textContent = "-";
  byId("ofnrRequest").textContent = "-";
}

function formatOfnr(dimension) {
  if (!dimension) return "-";
  const status = dimension.status || "UNKNOWN";
  const suggestion = dimension.suggestion || "";
  return `${status} · ${suggestion}`;
}

function renderHistory() {
  const container = byId("conversationList");
  container.innerHTML = "";
  renderTurnJumpOptions();

  if (!state.history.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "还没有会话记录。";
    container.appendChild(empty);
    return;
  }

  state.history.forEach((item) => {
    const card = document.createElement("article");
    card.className = "turn-card";
    card.id = `turn-card-${item.turn}`;
    if (state.selectedTurn === item.turn) {
      card.classList.add("is-highlight");
    }

    const head = document.createElement("p");
    head.className = "turn-head";
    head.textContent = `第 ${item.turn} 轮 · 分数 ${item.feedback?.overall_score ?? "-"} · 风险 ${item.feedback?.risk_level || "-"}`;

    const userLine = document.createElement("p");
    userLine.textContent = `你: ${item.user}`;

    const assistantLine = document.createElement("p");
    assistantLine.textContent = `AI: ${item.assistant}`;

    card.appendChild(head);
    card.appendChild(userLine);
    card.appendChild(assistantLine);
    const nextBest = item.feedback?.next_best_sentence || "";
    if (nextBest) {
      const keyLine = document.createElement("p");
      keyLine.className = "turn-keyline";
      keyLine.innerHTML = "<strong>关键句建议:</strong> ";
      const textNode = document.createElement("span");
      textNode.textContent = nextBest;
      keyLine.appendChild(textNode);
      card.appendChild(keyLine);
    }
    container.appendChild(card);
  });
}

function renderSummary() {
  const summary = state.summary;
  byId("summaryOpening").textContent = summary?.opening_line || "-";
  byId("summaryRequest").textContent = summary?.request_line || "-";
  byId("summaryFallback").textContent = summary?.fallback_line || "-";
  byId("summaryRisks").textContent = Array.isArray(summary?.risk_triggers)
    ? summary.risk_triggers.join("、") || "-"
    : "-";
  byId("summaryMeta").textContent = summary?.created_at
    ? `生成时间: ${formatDateTime(summary.created_at)}`
    : "尚未生成";
  updateShareTemplatePreview();
}

function renderReflectionMeta() {
  const reflection = state.reflection;
  if (!reflection) {
    byId("reflectionMeta").textContent = "尚未提交复盘";
    return;
  }

  const used = reflection.used_in_real_world ? "已用于真实对话" : "未用于真实对话";
  const score =
    reflection.outcome_score === null || reflection.outcome_score === undefined
      ? "无评分"
      : `评分 ${reflection.outcome_score}/5`;
  const time = reflection.created_at ? ` · ${formatDateTime(reflection.created_at)}` : "";
  byId("reflectionMeta").textContent = `${used} · ${score}${time}`;
}

function renderProgress(progress) {
  if (!progress) return;
  byId("progressPracticeCount").textContent = String(progress.practice_count ?? "-");
  byId("progressSummaryCount").textContent = String(progress.summary_count ?? "-");
  byId("progressRealCount").textContent = String(progress.real_world_used_count ?? "-");
  byId("progressOutcome").textContent = Number(progress.avg_outcome_score ?? 0).toFixed(2);
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatNowForFilename() {
  const date = new Date();
  const pad = (num) => String(num).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(
    date.getHours()
  )}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

function buildSummaryMarkdown() {
  const summary = state.summary;
  if (!summary) return "";
  const risks =
    Array.isArray(summary.risk_triggers) && summary.risk_triggers.length
      ? summary.risk_triggers.map((item) => `- ${item}`).join("\n")
      : "- 无";
  return [
    "# NVC 行动卡",
    "",
    `- 生成时间: ${formatDateTime(summary.created_at)}`,
    `- 场景ID: ${state.sceneId || "-"}`,
    `- 会话ID: ${state.sessionId || "-"}`,
    "",
    "## 开场句",
    summary.opening_line || "-",
    "",
    "## 请求句",
    summary.request_line || "-",
    "",
    "## 兜底句",
    summary.fallback_line || "-",
    "",
    "## 风险提醒",
    risks,
    "",
  ].join("\n");
}

function buildSummaryRiskLines(summary) {
  if (!summary || !Array.isArray(summary.risk_triggers) || !summary.risk_triggers.length) {
    return ["无"];
  }
  return summary.risk_triggers.map((item) => String(item || "").trim()).filter(Boolean);
}

function buildSummaryShareTemplate(type = "peer") {
  const summary = state.summary;
  if (!summary) return "";
  const riskLines = buildSummaryRiskLines(summary);
  const riskLine = riskLines.length ? riskLines.join(" / ") : "无";
  const createdAt = formatDateTime(summary.created_at);
  const sceneTitle = byId("sceneTitle").value.trim() || "未命名场景";

  if (type === "manager") {
    return [
      "【沟通对齐简报】",
      `场景: ${sceneTitle}`,
      `时间: ${createdAt}`,
      "",
      `观察: ${summary.opening_line || "-"}`,
      `请求: ${summary.request_line || "-"}`,
      `备选: ${summary.fallback_line || "-"}`,
      `风险提醒: ${riskLine}`,
      "",
      "我会先按上面的开场句沟通，再根据现场反馈调整。",
    ].join("\n");
  }

  if (type === "self") {
    return [
      "【今日 NVC 复盘卡】",
      `场景: ${sceneTitle}`,
      `时间: ${createdAt}`,
      "",
      `1) 开场句: ${summary.opening_line || "-"}`,
      `2) 请求句: ${summary.request_line || "-"}`,
      `3) 兜底句: ${summary.fallback_line || "-"}`,
      `4) 风险提醒: ${riskLine}`,
      "",
      "明日执行检查: 是否先说观察事实，再表达感受与需要。"
    ].join("\n");
  }

  return [
    "【沟通准备卡】",
    `场景: ${sceneTitle}`,
    `时间: ${createdAt}`,
    "",
    `开场: ${summary.opening_line || "-"}`,
    `请求: ${summary.request_line || "-"}`,
    `兜底: ${summary.fallback_line || "-"}`,
    `风险提醒: ${riskLine}`,
    "",
    "如果你方便，我们按这个版本先快速对齐。"
  ].join("\n");
}

function updateShareTemplatePreview() {
  const preview = byId("shareTemplatePreview");
  if (!preview) return;
  if (!state.summary) {
    preview.value = "生成行动卡后，这里会出现可直接分享的文案模板。";
    return;
  }
  const type = byId("shareTemplateType")?.value || "peer";
  preview.value = buildSummaryShareTemplate(type);
}

async function copyText(text) {
  if (!navigator.clipboard || !window.isSecureContext) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    return;
  }
  await navigator.clipboard.writeText(text);
}

function downloadText(filename, content, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mimeType });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(href);
}

function downloadBlob(filename, blob) {
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(href);
}

function escapeForHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeForXml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function splitTextForSvg(value, maxChars = 26, maxLines = 3) {
  const source = String(value || "").replace(/\s+/g, " ").trim();
  if (!source) return ["-"];
  const lines = [];
  let cursor = 0;
  while (cursor < source.length && lines.length < maxLines) {
    lines.push(source.slice(cursor, cursor + maxChars));
    cursor += maxChars;
  }
  if (cursor < source.length && lines.length) {
    const last = lines[lines.length - 1];
    lines[lines.length - 1] = `${last.slice(0, Math.max(0, maxChars - 1))}…`;
  }
  return lines;
}

function buildSummaryPrintHtml() {
  const summary = state.summary;
  if (!summary) return "";
  const riskItems = buildSummaryRiskLines(summary);
  const sceneTitle = byId("sceneTitle").value.trim() || "未命名场景";
  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <title>NVC 行动卡</title>
    <style>
      body { font-family: "Noto Sans SC", "PingFang SC", sans-serif; margin: 24px; color: #1c2d3a; }
      h1 { margin: 0 0 10px; font-size: 24px; }
      .meta { color: #496075; margin-bottom: 16px; font-size: 13px; }
      .card { border: 2px solid #1f3548; padding: 14px; margin-top: 8px; }
      .label { font-weight: 700; margin-bottom: 4px; color: #1f3548; }
      .line { margin: 0 0 10px; line-height: 1.6; white-space: pre-wrap; }
      ul { margin: 0; padding-left: 20px; }
      li { line-height: 1.6; }
    </style>
  </head>
  <body>
    <h1>NVC 行动卡</h1>
    <p class="meta">场景: ${escapeForHtml(sceneTitle)} | 生成时间: ${escapeForHtml(
      formatDateTime(summary.created_at)
    )}</p>
    <section class="card">
      <p class="label">开场句</p>
      <p class="line">${escapeForHtml(summary.opening_line || "-")}</p>
      <p class="label">请求句</p>
      <p class="line">${escapeForHtml(summary.request_line || "-")}</p>
      <p class="label">兜底句</p>
      <p class="line">${escapeForHtml(summary.fallback_line || "-")}</p>
      <p class="label">风险提醒</p>
      <ul>${riskItems.map((item) => `<li>${escapeForHtml(item)}</li>`).join("")}</ul>
    </section>
  </body>
</html>`;
}

function buildSummarySvg() {
  const summary = state.summary;
  if (!summary) return "";
  const sceneTitle = byId("sceneTitle").value.trim() || "未命名场景";
  const riskItems = buildSummaryRiskLines(summary);

  const sections = [
    { label: "开场句", value: summary.opening_line || "-" },
    { label: "请求句", value: summary.request_line || "-" },
    { label: "兜底句", value: summary.fallback_line || "-" },
    { label: "风险提醒", value: riskItems.join(" / ") || "-" },
  ];

  const lines = [];
  let y = 148;
  sections.forEach((section) => {
    lines.push(
      `<text x="72" y="${y}" font-size="30" font-weight="700" fill="#173245">${escapeForXml(
        section.label
      )}</text>`
    );
    y += 48;
    splitTextForSvg(section.value, 28, section.label === "风险提醒" ? 4 : 3).forEach((line) => {
      lines.push(
        `<text x="96" y="${y}" font-size="28" fill="#1f3548">${escapeForXml(line)}</text>`
      );
      y += 42;
    });
    y += 24;
  });

  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">
  <defs>
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f5f0dc"/>
      <stop offset="100%" stop-color="#d9ecdf"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="900" fill="url(#cardBg)"/>
  <rect x="34" y="34" width="1132" height="832" rx="24" fill="#ffffff" stroke="#1f3548" stroke-width="4"/>
  <text x="72" y="92" font-size="44" font-weight="700" fill="#1f3548">NVC 行动卡</text>
  <text x="72" y="126" font-size="22" fill="#436074">场景: ${escapeForXml(
    sceneTitle
  )} · 时间: ${escapeForXml(formatDateTime(summary.created_at))}</text>
  ${lines.join("\n  ")}
</svg>`;
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("图片渲染失败"));
    img.src = url;
  });
}

function exportSummaryAsPdf() {
  if (!state.summary) {
    throw new Error("请先生成行动卡");
  }
  const html = buildSummaryPrintHtml();
  const popup = window.open("", "_blank", "noopener,noreferrer");
  if (!popup) {
    throw new Error("浏览器拦截了弹窗，请允许弹窗后重试");
  }
  popup.document.open();
  popup.document.write(html);
  popup.document.close();
  popup.focus();
  setTimeout(() => {
    popup.print();
  }, 180);
}

async function exportSummaryAsImage() {
  if (!state.summary) {
    throw new Error("请先生成行动卡");
  }
  const svg = buildSummarySvg();
  const svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const svgUrl = URL.createObjectURL(svgBlob);
  try {
    const image = await loadImage(svgUrl);
    const canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = 900;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("当前浏览器不支持图片导出");
    }
    context.fillStyle = "#f8f7f2";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    const pngBlob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("生成图片失败"));
            return;
          }
          resolve(blob);
        },
        "image/png",
        1
      );
    });
    const filename = `nvc_action_card_${formatNowForFilename()}.png`;
    downloadBlob(filename, pngBlob);
  } finally {
    URL.revokeObjectURL(svgUrl);
  }
}

function setHighlightedText(element, content, keyword) {
  const source = String(content || "");
  const query = String(keyword || "").trim();
  element.innerHTML = "";
  if (!source) return;
  if (!query) {
    element.textContent = source;
    return;
  }

  const lowerSource = source.toLocaleLowerCase();
  const lowerQuery = query.toLocaleLowerCase();
  let cursor = 0;
  while (cursor < source.length) {
    const hit = lowerSource.indexOf(lowerQuery, cursor);
    if (hit < 0) {
      element.appendChild(document.createTextNode(source.slice(cursor)));
      break;
    }

    if (hit > cursor) {
      element.appendChild(document.createTextNode(source.slice(cursor, hit)));
    }

    const mark = document.createElement("mark");
    mark.textContent = source.slice(hit, hit + query.length);
    element.appendChild(mark);
    cursor = hit + query.length;
  }
}

function getBoundedHistoryLimit(raw) {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return HISTORY_DEFAULT_LIMIT;
  return Math.min(Math.max(parsed, 1), 50);
}

function persistHistoryViewState() {
  const filters = getHistoryFilters();
  const payload = {
    ...filters,
    limit: getBoundedHistoryLimit(byId("historyLimit").value || HISTORY_DEFAULT_LIMIT),
    offset: state.historyOffset,
  };
  localStorage.setItem(HISTORY_VIEW_STATE_KEY, JSON.stringify(payload));
}

function hydrateHistoryViewState() {
  const raw = localStorage.getItem(HISTORY_VIEW_STATE_KEY);
  if (!raw) return;
  const parsed = parseJson(raw, null);
  if (!parsed || typeof parsed !== "object") return;

  byId("historyLimit").value = String(getBoundedHistoryLimit(parsed.limit ?? HISTORY_DEFAULT_LIMIT));
  byId("historyState").value = typeof parsed.state === "string" ? parsed.state : "";
  byId("historyKeyword").value = typeof parsed.keyword === "string" ? parsed.keyword : "";
  byId("historyCreatedFrom").value =
    typeof parsed.created_from === "string" ? parsed.created_from : "";
  byId("historyCreatedTo").value =
    typeof parsed.created_to === "string" ? parsed.created_to : "";

  const parsedOffset = Number(parsed.offset ?? 0);
  state.historyOffset = Number.isFinite(parsedOffset) ? Math.max(0, parsedOffset) : 0;
  state.historyLimit = getBoundedHistoryLimit(parsed.limit ?? HISTORY_DEFAULT_LIMIT);
}

function getHistoryFilters() {
  return {
    state: byId("historyState").value.trim(),
    keyword: byId("historyKeyword").value.trim(),
    created_from: byId("historyCreatedFrom").value || "",
    created_to: byId("historyCreatedTo").value || "",
  };
}

function updateHistoryFilterHint(filters) {
  const chips = [];
  if (filters.state) chips.push(`状态:${filters.state}`);
  if (filters.keyword) chips.push(`关键词:${filters.keyword}`);
  if (filters.created_from) chips.push(`开始:${filters.created_from}`);
  if (filters.created_to) chips.push(`结束:${filters.created_to}`);
  byId("historyFilterHint").textContent = `当前筛选: ${chips.length ? chips.join(" / ") : "全部"}`;
}

function renderHistoryPagination(total, limit, offset) {
  const normalizedTotal = Math.max(0, Number(total || 0));
  const normalizedLimit = getBoundedHistoryLimit(limit || HISTORY_DEFAULT_LIMIT);
  const normalizedOffset = Math.max(0, Number(offset || 0));
  const totalPages = Math.max(1, Math.ceil(normalizedTotal / normalizedLimit));
  const currentPage = normalizedTotal === 0 ? 1 : Math.floor(normalizedOffset / normalizedLimit) + 1;

  state.historyTotal = normalizedTotal;
  state.historyLimit = normalizedLimit;
  state.historyOffset = normalizedOffset;

  byId("historyPageMeta").textContent = `第 ${currentPage}/${totalPages} 页 · 共 ${normalizedTotal} 条`;
  byId("historyPrevBtn").disabled = normalizedOffset <= 0;
  byId("historyNextBtn").disabled =
    normalizedTotal === 0 || normalizedOffset + normalizedLimit >= normalizedTotal;
}

function renderTurnJumpOptions() {
  const select = byId("turnJumpSelect");
  select.innerHTML = "";

  const fallback = document.createElement("option");
  fallback.value = "";
  fallback.textContent = "最新一轮";
  select.appendChild(fallback);

  if (!state.history.length) {
    select.disabled = true;
    return;
  }

  state.history.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.turn);
    option.textContent = `第 ${item.turn} 轮`;
    select.appendChild(option);
  });

  const latestTurn = state.history[state.history.length - 1].turn;
  const hasSelected = state.history.some((item) => item.turn === state.selectedTurn);
  const targetTurn = hasSelected ? state.selectedTurn : latestTurn;
  state.selectedTurn = targetTurn;
  select.value = String(targetTurn);
  select.disabled = false;
}

function jumpToTurn(rawTurn, options = {}) {
  if (!state.history.length) return;
  const { smooth = true } = options;
  const normalized = String(rawTurn ?? "").trim();
  const parsed = Number(normalized);
  const fallbackTurn = state.history[state.history.length - 1].turn;
  state.selectedTurn = normalized && Number.isInteger(parsed) ? parsed : fallbackTurn;
  renderHistory();
  persistRuntimeState();
  const target = byId(`turn-card-${state.selectedTurn}`);
  if (target) {
    target.scrollIntoView({ block: "nearest", behavior: smooth ? "smooth" : "auto" });
  }
}

function applyReflectionToForm(reflection) {
  if (!reflection) {
    byId("usedInRealWorld").value = "true";
    byId("outcomeScore").value = "";
    byId("blockerNote").value = "";
    syncOutcomeState();
    return;
  }

  byId("usedInRealWorld").value = reflection.used_in_real_world ? "true" : "false";
  byId("outcomeScore").value =
    reflection.outcome_score === null || reflection.outcome_score === undefined
      ? ""
      : String(reflection.outcome_score);
  byId("blockerNote").value = reflection.blocker_note || "";
  syncOutcomeState();
}

function buildHistorySessionCard(item, keyword = "") {
  const card = document.createElement("article");
  card.className = "history-session-card";

  const head = document.createElement("p");
  head.className = "history-session-head";
  head.textContent = `${formatDateTime(item.created_at)} · ${item.state} · ${item.current_turn}/${item.target_turns} 轮`;

  const title = document.createElement("p");
  title.className = "history-session-title";
  setHighlightedText(title, item.scene_title || "未命名场景", keyword);

  const snippet = document.createElement("p");
  snippet.className = "history-session-snippet";
  setHighlightedText(snippet, item.last_user_message || "本会话尚无用户消息", keyword);

  const actions = document.createElement("div");
  actions.className = "history-session-actions";

  const loadBtn = document.createElement("button");
  loadBtn.type = "button";
  loadBtn.className = "tone-ghost";
  loadBtn.textContent = "回看会话";
  loadBtn.addEventListener("click", () => loadSessionHistory(item.session_id).catch(showError));

  if (item.state === "ACTIVE") {
    const continueBtn = document.createElement("button");
    continueBtn.type = "button";
    continueBtn.textContent = "继续练习";
    continueBtn.addEventListener("click", () =>
      continueSessionFromHistory(item.session_id).catch(showError)
    );
    actions.appendChild(continueBtn);
  }

  actions.appendChild(loadBtn);
  card.appendChild(head);
  card.appendChild(title);
  card.appendChild(snippet);
  card.appendChild(actions);
  return card;
}

function renderSessionHistoryList(items, keyword = "") {
  const container = byId("historySessionList");
  container.innerHTML = "";

  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "暂无历史会话，完成一次练习后这里会出现记录。";
    container.appendChild(empty);
    return;
  }

  const riskGroups = {
    HIGH: [],
    MEDIUM: [],
    LOW: [],
    NONE: [],
  };

  items.forEach((item) => {
    const key = item.last_risk_level || "NONE";
    if (!Object.prototype.hasOwnProperty.call(riskGroups, key)) {
      riskGroups.NONE.push(item);
      return;
    }
    riskGroups[key].push(item);
  });

  const groupOrder = [
    { key: "HIGH", label: "高风险会话" },
    { key: "MEDIUM", label: "中风险会话" },
    { key: "LOW", label: "低风险会话" },
    { key: "NONE", label: "未评估会话" },
  ];

  groupOrder.forEach((group) => {
    const groupedItems = riskGroups[group.key];
    if (!groupedItems.length) return;

    const wrapper = document.createElement("section");
    wrapper.className = "history-risk-group";

    const head = document.createElement("p");
    head.className = "history-risk-head";
    head.textContent = `${group.label} (${groupedItems.length})`;
    wrapper.appendChild(head);

    groupedItems.forEach((item) => {
      wrapper.appendChild(buildHistorySessionCard(item, keyword));
    });
    container.appendChild(wrapper);
  });
}

function persistSupabaseSession(config, session, message) {
  byId("supabaseAccessToken").value = session.access_token;
  setAuthMode("supabase");
  localStorage.setItem("supabase_email", config.supabaseEmail);
  localStorage.setItem("supabase_access_token", session.access_token);
  setNotice(message, "success");
  setOutput({
    ok: true,
    token_type: session.token_type,
    expires_in: session.expires_in,
  });
}

async function fetchSupabasePasswordToken(config) {
  const res = await fetch(`${config.supabaseUrl}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: config.supabaseAnonKey,
    },
    body: JSON.stringify({ email: config.supabaseEmail, password: config.supabasePassword }),
  });
  const text = await res.text();
  const data = parseJson(text, text ? { raw: text } : {});
  if (!res.ok || !data.access_token) {
    throw new Error(`Supabase 登录失败: ${JSON.stringify(data)}`);
  }
  return data;
}

async function loginSupabase() {
  const config = getConfig({ requireAuthToken: false, requireMockUser: false });
  setAuthMode("supabase");

  if (!config.supabaseUrl) throw new Error("请填写 Supabase URL");
  if (!config.supabaseAnonKey) throw new Error("请填写 Supabase Anon Key");
  if (!config.supabaseEmail || !config.supabasePassword) throw new Error("请填写邮箱和密码");

  const session = await fetchSupabasePasswordToken(config);
  persistSupabaseSession(config, session, "登录成功，已获取 Access Token。");
  await fetchSessionHistoryList({ silent: true });
}

async function signupSupabase() {
  const config = getConfig({ requireAuthToken: false, requireMockUser: false });
  setAuthMode("supabase");

  if (!config.supabaseUrl) throw new Error("请填写 Supabase URL");
  if (!config.supabaseAnonKey) throw new Error("请填写 Supabase Anon Key");
  if (!config.supabaseEmail || !config.supabasePassword) throw new Error("请填写注册邮箱和密码");

  const res = await fetch(`${config.supabaseUrl}/auth/v1/signup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: config.supabaseAnonKey,
    },
    body: JSON.stringify({ email: config.supabaseEmail, password: config.supabasePassword }),
  });

  const text = await res.text();
  const data = parseJson(text, text ? { raw: text } : {});

  if (!res.ok) {
    if (
      res.status === 429 ||
      data.error_code === "over_email_send_rate_limit" ||
      String(data.msg || "").includes("email rate limit exceeded")
    ) {
      setNotice("注册触发邮件频控，请稍后再试，或直接使用已有账号登录。", "warning");
      setOutput({ error: data });
      return;
    }
    throw new Error(`注册失败: ${JSON.stringify(data)}`);
  }

  if (data.access_token) {
    persistSupabaseSession(config, data, "注册成功，已自动登录。");
    await fetchSessionHistoryList({ silent: true });
    return;
  }

  await loginSupabase();
}

function switchToMockMode(reason) {
  if (!DEV_CONTEXT) {
    throw new Error("线上环境已禁用 Mock 模式");
  }
  const uid = byId("mockUserId").value.trim() || crypto.randomUUID();
  byId("mockUserId").value = uid;
  localStorage.setItem("mock_user_id", uid);
  setAuthMode("mock");
  if (reason) {
    setNotice(reason, "warning");
  }
  return uid;
}

function saveConfig() {
  localStorage.setItem("api_base_url", byId("apiBaseUrl").value.trim());
  localStorage.setItem("mock_user_id", byId("mockUserId").value.trim());
  localStorage.setItem("supabase_url", byId("supabaseUrl").value.trim());
  localStorage.setItem("supabase_anon_key", byId("supabaseAnonKey").value.trim());
  localStorage.setItem("supabase_email", byId("supabaseEmail").value.trim());
  localStorage.setItem("supabase_access_token", byId("supabaseAccessToken").value.trim());
  setAuthMode(byId("authMode").value || "supabase");
  setNotice("配置已保存到浏览器本地。", "success");
}

function loadConfig() {
  const savedApiRaw = localStorage.getItem("api_base_url");
  const shouldForceProxy =
    !savedApiRaw || /nvc-practice-api\.vercel\.app|api\.leonalgo\.site/.test(savedApiRaw);
  const savedApi = shouldForceProxy ? window.location.origin : savedApiRaw;

  if (shouldForceProxy) {
    localStorage.setItem("api_base_url", window.location.origin);
  }

  byId("apiBaseUrl").value = savedApi || window.location.origin;
  byId("mockUserId").value = localStorage.getItem("mock_user_id") || ensureUserId();
  byId("supabaseUrl").value = localStorage.getItem("supabase_url") || DEFAULT_SUPABASE_URL;
  byId("supabaseAnonKey").value =
    localStorage.getItem("supabase_anon_key") || DEFAULT_SUPABASE_ANON_KEY;
  byId("supabaseEmail").value = localStorage.getItem("supabase_email") || "";
  byId("supabaseAccessToken").value = localStorage.getItem("supabase_access_token") || "";

  if (DEV_CONTEXT) {
    byId("authMode").value = localStorage.getItem("auth_mode") || "supabase";
  } else {
    byId("authMode").value = "supabase";
    setAuthMode("supabase");
  }

  refreshAuthModeBadge();
}

function getCurrentWeekStart() {
  const now = new Date();
  const day = (now.getDay() + 6) % 7;
  now.setHours(0, 0, 0, 0);
  now.setDate(now.getDate() - day);
  return now.toISOString().slice(0, 10);
}

function syncOutcomeState() {
  const used = byId("usedInRealWorld").value === "true";
  const score = byId("outcomeScore");
  score.disabled = !used;
  if (!used) {
    score.value = "";
  }
}

async function sendPracticeTurn({ createFresh = false } = {}) {
  clearNotice();
  const config = getConfig({ requireAuthToken: true });
  const content = byId("messageContent").value.trim();
  if (!content) {
    throw new Error("请输入你要练习的发言");
  }

  if (createFresh) {
    resetRuntimeState();
  }

  if (!state.sessionId) {
    const sceneData = await createScene(config);
    state.sceneId = sceneData.scene_id;

    const sessionData = await createSession(config, state.sceneId);
    state.sessionId = sessionData.session_id;
    state.turn = sessionData.current_turn || 0;
  }

  const messageData = await sendSessionMessage(config, state.sessionId, content);
  state.turn = messageData.turn;
  state.selectedTurn = messageData.turn;
  state.lastUserMessageId = messageData.user_message_id;
  state.history.push({
    turn: messageData.turn,
    user: content,
    assistant: messageData.assistant_message?.content || "",
    feedback: messageData.feedback || null,
  });

  if (state.history.length > 30) {
    state.history = state.history.slice(-30);
  }

  persistRuntimeState();
  updateRuntimeMeta();
  renderFeedback(messageData);
  renderHistory();
  updateStepState();

  setNotice(
    createFresh ? "第 1 轮已开始，可继续输入下一句。" : `已完成第 ${state.turn} 轮练习。`,
    "success"
  );
  setOutput(messageData);
  fetchSessionHistoryList({ silent: true }).catch(() => {});
}

async function generateSummary() {
  clearNotice();
  const config = getConfig({ requireAuthToken: true });
  if (!state.sessionId) {
    throw new Error("请先完成至少 1 轮练习");
  }

  const data = await callApi(`${config.apiBaseUrl}/api/v1/sessions/${state.sessionId}/summary`, {
    method: "POST",
    headers: authHeaders(config),
  });

  state.summary = data;
  persistRuntimeState();
  renderSummary();
  updateStepState();
  setNotice("行动卡已生成。", "success");
  setOutput(data);
  fetchSessionHistoryList({ silent: true }).catch(() => {});
}

async function submitReflection() {
  clearNotice();
  const config = getConfig({ requireAuthToken: true });
  if (!state.sessionId) {
    throw new Error("请先完成练习会话");
  }

  const used = byId("usedInRealWorld").value === "true";
  const outcomeRaw = byId("outcomeScore").value.trim();
  const outcome = outcomeRaw ? Number(outcomeRaw) : null;
  if (used && !outcome) {
    throw new Error("已用于真实对话时，请填写 1-5 的效果评分");
  }

  const blockerNote = byId("blockerNote").value.trim() || null;

  const payload = {
    session_id: state.sessionId,
    used_in_real_world: used,
    outcome_score: outcome,
    blocker_code: null,
    blocker_note: blockerNote,
  };

  const data = await callApi(`${config.apiBaseUrl}/api/v1/reflections`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify(payload),
  });

  state.reflectionId = data.reflection_id;
  state.reflection = {
    reflection_id: data.reflection_id,
    used_in_real_world: payload.used_in_real_world,
    outcome_score: payload.outcome_score,
    blocker_code: payload.blocker_code,
    blocker_note: payload.blocker_note,
    created_at: data.created_at,
  };
  persistRuntimeState();
  renderReflectionMeta();
  updateStepState();
  setNotice("复盘已提交。", "success");
  setOutput(data);
  fetchSessionHistoryList({ silent: true }).catch(() => {});
}

async function fetchWeeklyProgress() {
  clearNotice();
  const config = getConfig({ requireAuthToken: true });
  const weekStart = byId("progressWeekStart").value || getCurrentWeekStart();

  const data = await callApi(
    `${config.apiBaseUrl}/api/v1/progress/weekly?week_start=${encodeURIComponent(weekStart)}`,
    {
      method: "GET",
      headers: authHeaders(config),
    }
  );

  renderProgress(data);
  setNotice("周进度已更新。", "success");
  setOutput(data);
}

function resetHistoryFilters() {
  byId("historyState").value = "";
  byId("historyKeyword").value = "";
  byId("historyCreatedFrom").value = "";
  byId("historyCreatedTo").value = "";
  state.historyOffset = 0;
  updateHistoryFilterHint(getHistoryFilters());
  persistHistoryViewState();
}

async function fetchSessionHistoryList(options = {}) {
  const {
    silent = false,
    setOutputPanel = false,
    resetOffset = false,
    offsetOverride = null,
    _retry = false,
  } = options;
  const config = getConfig({ requireAuthToken: true });
  const boundedLimit = getBoundedHistoryLimit(byId("historyLimit").value || HISTORY_DEFAULT_LIMIT);
  if (resetOffset) {
    state.historyOffset = 0;
  }
  if (Number.isInteger(offsetOverride) && offsetOverride >= 0) {
    state.historyOffset = offsetOverride;
  }
  const filters = getHistoryFilters();

  if (filters.created_from && filters.created_to && filters.created_from > filters.created_to) {
    throw new Error("开始日期不能晚于结束日期");
  }

  const query = new URLSearchParams({
    limit: String(boundedLimit),
    offset: String(state.historyOffset),
  });
  if (filters.state) query.set("state", filters.state);
  if (filters.keyword) query.set("keyword", filters.keyword);
  if (filters.created_from) query.set("created_from", filters.created_from);
  if (filters.created_to) query.set("created_to", filters.created_to);

  let data;
  try {
    data = await callApi(
      `${config.apiBaseUrl}/api/v1/sessions?${query.toString()}`,
      {
        method: "GET",
        headers: authHeaders(config),
      }
    );
  } catch (error) {
    const filtersEnabled = Boolean(
      filters.state || filters.keyword || filters.created_from || filters.created_to
    );
    if (!filtersEnabled && isOfflineLikeError(error)) {
      const snapshot = loadHistoryListSnapshot();
      if (snapshot && Array.isArray(snapshot.items) && snapshot.items.length > 0) {
        const snapshotItems = snapshot.items;
        const snapshotTotal = Number(snapshot.total || snapshotItems.length);
        state.historyOffset = 0;
        state.historyTotal = snapshotTotal;
        state.historyLimit = getBoundedHistoryLimit(
          snapshot.limit || byId("historyLimit").value || HISTORY_DEFAULT_LIMIT
        );
        updateHistoryFilterHint(filters);
        renderHistoryPagination(snapshotTotal, state.historyLimit, state.historyOffset);
        renderSessionHistoryList(snapshotItems, "");
        if (!silent) {
          const updatedAt = snapshot.updated_at ? formatDateTime(snapshot.updated_at) : "未知";
          setNotice(`当前离线，已展示本地快照（更新于 ${updatedAt}）。`, "warning");
        }
        if (setOutputPanel) {
          setOutput({ offline_snapshot: true, ...snapshot });
        }
        return {
          items: snapshotItems,
          total: snapshotTotal,
          offset: 0,
          limit: state.historyLimit,
          offline_snapshot: true,
        };
      }
    }
    throw error;
  }

  const items = Array.isArray(data.items) ? data.items : [];
  const total = Number(data.total || 0);
  const currentOffset = Number(data.offset ?? state.historyOffset);

  if (!_retry && total > 0 && items.length === 0 && currentOffset > 0) {
    const fallbackOffset = Math.max(0, Math.floor((total - 1) / boundedLimit) * boundedLimit);
    return fetchSessionHistoryList({
      ...options,
      offsetOverride: fallbackOffset,
      silent: true,
      _retry: true,
    });
  }

  state.historyOffset = Number.isFinite(currentOffset) ? Math.max(0, currentOffset) : 0;
  state.historyTotal = total;
  state.historyLimit = boundedLimit;
  persistHistoryViewState();
  if (
    !filters.state &&
    !filters.keyword &&
    !filters.created_from &&
    !filters.created_to &&
    state.historyOffset === 0
  ) {
    persistHistoryListSnapshot(items, {
      total,
      limit: boundedLimit,
      offset: state.historyOffset,
    });
  }
  updateHistoryFilterHint(filters);
  renderHistoryPagination(total, boundedLimit, state.historyOffset);
  renderSessionHistoryList(items, filters.keyword);
  if (!silent) {
    const currentPage = total === 0 ? 1 : Math.floor(state.historyOffset / boundedLimit) + 1;
    setNotice(`历史会话已刷新，共 ${total} 条（第 ${currentPage} 页）。`, "success");
  }
  if (setOutputPanel) {
    setOutput({
      ...data,
      paging: {
        offset: state.historyOffset,
        limit: boundedLimit,
        total,
      },
    });
  }
  return { ...data, items, total };
}

function applySessionHistoryPayload(data, options = {}) {
  const { source = "remote" } = options;
  state.sceneId = data.scene.scene_id;
  state.sessionId = data.session_id;
  state.turn = data.current_turn || 0;
  state.selectedTurn = data.current_turn || 0;
  state.summary = data.summary || null;
  state.reflection = data.reflection || null;
  state.reflectionId = data.reflection?.reflection_id || "";
  state.history = (data.turns || []).map((turn) => ({
    turn: turn.turn,
    user: turn.user_content || "",
    assistant: turn.assistant_content || "",
    feedback: turn.feedback || null,
  }));
  state.lastUserMessageId =
    data.turns && data.turns.length ? data.turns[data.turns.length - 1].user_message_id : "";

  byId("sceneTitle").value = data.scene.title || byId("sceneTitle").value;
  byId("sceneGoal").value = data.scene.goal || byId("sceneGoal").value;
  byId("sceneContext").value = data.scene.context || byId("sceneContext").value;

  renderHistory();
  renderSummary();
  renderReflectionMeta();
  updateRuntimeMeta();
  updateStepState();
  applyReflectionToForm(data.reflection);
  if (state.history.length > 0) {
    const last = state.history[state.history.length - 1];
    renderFeedback({
      assistant_message: { content: last.assistant },
      feedback: last.feedback || null,
    });
  } else {
    clearFeedbackPanel();
  }

  persistRuntimeState();
  if (source === "snapshot") {
    setNotice("当前离线，已加载本地会话快照。", "warning");
  } else {
    setNotice("会话已加载，可继续回看或继续练习。", "success");
  }
  setOutput(data);
}

async function loadSessionHistory(sessionId) {
  clearNotice();
  const config = getConfig({ requireAuthToken: true });
  try {
    const data = await callApi(`${config.apiBaseUrl}/api/v1/sessions/${sessionId}/history`, {
      method: "GET",
      headers: authHeaders(config),
    });
    persistHistoryDetailSnapshot(sessionId, data);
    applySessionHistoryPayload(data, { source: "remote" });
    return;
  } catch (error) {
    if (isOfflineLikeError(error)) {
      const snapshot = loadHistoryDetailSnapshot(sessionId);
      if (snapshot && snapshot.scene && Array.isArray(snapshot.turns)) {
        applySessionHistoryPayload(snapshot, { source: "snapshot" });
        return;
      }
    }
    throw error;
  }
}

async function continueSessionFromHistory(sessionId) {
  await loadSessionHistory(sessionId);
  byId("messageContent").focus();
  byId("messageContent").scrollIntoView({ behavior: "smooth", block: "center" });
  setNotice("已切换到该会话，可直接输入下一句继续练习。", "success");
}

function showError(err) {
  const msg = String(err?.message || err);
  const mode = byId("authMode").value || "supabase";

  if (isOfflineLikeError(err)) {
    setNotice("当前离线或网络不可用，请恢复网络后重试。", "warning");
    setOutput({ error: msg, hint: "离线状态下可先查看本地缓存内容。" });
    return;
  }

  if (msg.includes("invalid or expired access token") && mode === "supabase") {
    setNotice("Token 无效或过期，请重新登录获取。", "warning");
    setOutput({ error: msg, hint: "点击“登录并获取 Token”后重试。" });
    return;
  }

  if (msg.includes("401") && mode === "mock" && !DEV_CONTEXT) {
    setNotice("线上环境不支持 Mock 鉴权，请切换 Supabase 登录。", "error");
    setOutput({ error: msg });
    return;
  }

  setNotice("操作失败，请查看下方错误详情。", "error");
  setOutput({ error: msg });
}

function bind() {
  applyModeVisibility();
  loadConfig();
  hydrateRuntimeState();
  hydrateHistoryViewState();
  updateHistoryFilterHint(getHistoryFilters());
  renderHistoryPagination(state.historyTotal, state.historyLimit, state.historyOffset);
  updateRuntimeMeta();
  renderHistory();
  renderSummary();
  renderReflectionMeta();
  byId("progressWeekStart").value = getCurrentWeekStart();
  syncOutcomeState();
  applyReflectionToForm(state.reflection);
  updateStepState();
  initPwaRuntime().catch((err) => {
    setPwaModeBadge("ERROR");
    setPwaNetworkBar(`PWA 初始化失败: ${String(err?.message || err)}`, "offline");
  });

  byId("templatePreset").addEventListener("change", applyTemplatePreset);
  byId("usedInRealWorld").addEventListener("change", syncOutcomeState);
  byId("installAppBtn").addEventListener("click", () =>
    promptPwaInstall()
      .then(() => setNotice("安装流程已触发。", "success"))
      .catch(showError)
  );
  byId("updateAppBtn").addEventListener("click", () =>
    applyPwaUpdate()
      .then(() => setNotice("正在更新到新版本。", "success"))
      .catch(showError)
  );

  byId("supabaseSignupBtn").addEventListener("click", () => signupSupabase().catch(showError));
  byId("supabaseLoginBtn").addEventListener("click", () => loginSupabase().catch(showError));

  byId("clearTokenBtn").addEventListener("click", () => {
    byId("supabaseAccessToken").value = "";
    localStorage.removeItem("supabase_access_token");
    state.historyOffset = 0;
    state.historyTotal = 0;
    persistHistoryViewState();
    renderHistoryPagination(0, getBoundedHistoryLimit(byId("historyLimit").value), 0);
    renderSessionHistoryList([]);
    updateStepState();
    setNotice("已清空 Access Token。", "success");
  });

  byId("saveConfigBtn").addEventListener("click", saveConfig);
  byId("refreshHistoryBtn").addEventListener("click", () =>
    fetchSessionHistoryList({ silent: false, setOutputPanel: true, resetOffset: true }).catch(showError)
  );
  byId("resetHistoryFiltersBtn").addEventListener("click", () => {
    resetHistoryFilters();
    fetchSessionHistoryList({ silent: false, setOutputPanel: true, resetOffset: true }).catch(
      showError
    );
  });
  byId("historyPrevBtn").addEventListener("click", () => {
    const nextOffset = Math.max(0, state.historyOffset - state.historyLimit);
    fetchSessionHistoryList({
      silent: false,
      setOutputPanel: true,
      offsetOverride: nextOffset,
    }).catch(showError);
  });
  byId("historyNextBtn").addEventListener("click", () => {
    const nextOffset = state.historyOffset + state.historyLimit;
    fetchSessionHistoryList({
      silent: false,
      setOutputPanel: true,
      offsetOverride: nextOffset,
    }).catch(showError);
  });
  byId("historyLimit").addEventListener("change", () => {
    byId("historyLimit").value = String(getBoundedHistoryLimit(byId("historyLimit").value));
    fetchSessionHistoryList({ silent: false, setOutputPanel: true, resetOffset: true }).catch(
      showError
    );
  });
  byId("turnJumpSelect").addEventListener("change", (event) => {
    jumpToTurn(event.target.value);
  });
  byId("continuePracticeBtn").addEventListener("click", () => {
    if (!state.sessionId) {
      setNotice("请先创建会话或从历史记录加载会话。", "warning");
      return;
    }
    byId("messageContent").focus();
    byId("messageContent").scrollIntoView({ behavior: "smooth", block: "center" });
    setNotice("已定位到输入框，可继续当前会话。", "success");
  });
  byId("historyKeyword").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      fetchSessionHistoryList({ silent: false, setOutputPanel: true, resetOffset: true }).catch(
        showError
      );
    }
  });

  byId("startPracticeBtn").addEventListener("click", () =>
    sendPracticeTurn({ createFresh: true }).catch(showError)
  );
  byId("sendMessageBtn").addEventListener("click", () =>
    sendPracticeTurn({ createFresh: false }).catch(showError)
  );

  byId("newSessionBtn").addEventListener("click", () => {
    resetRuntimeState();
    setNotice("已重置会话状态。点击“创建场景并发送第 1 轮”开始新的练习。", "success");
  });

  byId("generateSummaryBtn").addEventListener("click", () => generateSummary().catch(showError));
  byId("copySummaryBtn").addEventListener("click", async () => {
    if (!state.summary) {
      setNotice("请先生成行动卡。", "warning");
      return;
    }
    try {
      await copyText(buildSummaryMarkdown());
      setNotice("行动卡内容已复制。", "success");
    } catch (error) {
      showError(error);
    }
  });
  byId("exportSummaryBtn").addEventListener("click", () => {
    if (!state.summary) {
      setNotice("请先生成行动卡。", "warning");
      return;
    }
    const filename = `nvc_action_card_${formatNowForFilename()}.md`;
    downloadText(filename, buildSummaryMarkdown(), "text/markdown;charset=utf-8");
    setNotice("行动卡已导出为 Markdown。", "success");
  });
  byId("exportSummaryPdfBtn").addEventListener("click", () => {
    try {
      exportSummaryAsPdf();
      setNotice("已打开打印窗口，可另存为 PDF。", "success");
    } catch (error) {
      showError(error);
    }
  });
  byId("exportSummaryImageBtn").addEventListener("click", () =>
    exportSummaryAsImage()
      .then(() => setNotice("行动卡已导出为 PNG 图片。", "success"))
      .catch(showError)
  );
  byId("shareTemplateType").addEventListener("change", updateShareTemplatePreview);
  byId("copyShareTemplateBtn").addEventListener("click", async () => {
    if (!state.summary) {
      setNotice("请先生成行动卡。", "warning");
      return;
    }
    try {
      await copyText(buildSummaryShareTemplate(byId("shareTemplateType").value || "peer"));
      setNotice("分享模板已复制。", "success");
    } catch (error) {
      showError(error);
    }
  });
  byId("downloadShareTemplateBtn").addEventListener("click", () => {
    if (!state.summary) {
      setNotice("请先生成行动卡。", "warning");
      return;
    }
    const templateType = byId("shareTemplateType").value || "peer";
    const filename = `nvc_share_template_${templateType}_${formatNowForFilename()}.txt`;
    downloadText(filename, buildSummaryShareTemplate(templateType), "text/plain;charset=utf-8");
    setNotice("分享模板已导出。", "success");
  });
  byId("submitReflectionBtn").addEventListener("click", () => submitReflection().catch(showError));
  byId("weeklyProgressBtn").addEventListener("click", () => fetchWeeklyProgress().catch(showError));

  if (DEV_CONTEXT) {
    byId("newUserBtn").addEventListener("click", () => {
      const uid = switchToMockMode("已切换到 Mock 模式，可直接联调 API。");
      setOutput({ ok: true, mock_user_id: uid });
    });
    byId("useMockModeBtn").addEventListener("click", () => {
      const uid = switchToMockMode("已切换到 Mock 模式。");
      setOutput({ ok: true, mock_user_id: uid });
    });
    byId("useSupabaseModeBtn").addEventListener("click", () => {
      setAuthMode("supabase");
      setNotice("已切回 Supabase 模式。", "success");
    });
    byId("authMode").addEventListener("change", () => {
      setAuthMode(byId("authMode").value || "supabase");
    });
    byId("enablePwaBtn").addEventListener("click", async () => {
      await setPwaEnabled(true);
      setNotice("已启用 PWA，页面将刷新。", "success");
      window.location.reload();
    });
    byId("disablePwaBtn").addEventListener("click", async () => {
      await setPwaEnabled(false);
      await unregisterAllServiceWorkers();
      setNotice("已禁用 PWA 并清理 Service Worker，页面将刷新。", "success");
      window.location.reload();
    });
    byId("unregisterSwBtn").addEventListener("click", () =>
      unregisterAllServiceWorkers()
        .then((count) => setNotice(`已清理 ${count} 个 Service Worker 注册。`, "success"))
        .catch(showError)
    );
  }

  byId("useProxyBtn").addEventListener("click", () => {
    byId("apiBaseUrl").value = window.location.origin;
    localStorage.setItem("api_base_url", window.location.origin);
    setNotice("已切换为同域代理。", "success");
  });

  if (!state.history.length) {
    const demoPreset = getCurrentPreset();
    byId("sceneTitle").value = demoPreset.title;
    byId("sceneGoal").value = demoPreset.goal;
    byId("sceneContext").value = demoPreset.context;
  }

  const mode = byId("authMode").value || "supabase";
  const hasToken = Boolean(byId("supabaseAccessToken").value.trim());
  if (mode === "mock" || hasToken) {
    fetchSessionHistoryList({ silent: true }).catch(() => {});
  } else {
    renderHistoryPagination(0, getBoundedHistoryLimit(byId("historyLimit").value), 0);
    renderSessionHistoryList([]);
  }
}

bind();
