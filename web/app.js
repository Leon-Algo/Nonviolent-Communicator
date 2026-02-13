function byId(id) {
  return document.getElementById(id);
}

const DEFAULT_SUPABASE_URL = "https://wiafjgjfdrajlxnlkray.supabase.co";
const DEFAULT_SUPABASE_ANON_KEY = "sb_publishable_EvEX2Hlp9e7SU4FcbpIrzQ_uusY6M87";
const RUNTIME_STATE_KEY = "runtime_state_v2";

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

const state = {
  sceneId: "",
  sessionId: "",
  turn: 0,
  lastUserMessageId: "",
  history: [],
  summary: null,
  reflectionId: "",
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
      lastUserMessageId: state.lastUserMessageId,
      history: state.history,
      summary: state.summary,
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
  state.lastUserMessageId = parsed.lastUserMessageId || "";
  state.history = Array.isArray(parsed.history) ? parsed.history : [];
  state.summary = parsed.summary || null;
  state.reflectionId = parsed.reflectionId || "";
}

function resetRuntimeState() {
  state.sceneId = "";
  state.sessionId = "";
  state.turn = 0;
  state.lastUserMessageId = "";
  state.history = [];
  state.summary = null;
  state.reflectionId = "";
  persistRuntimeState();
  renderHistory();
  renderSummary();
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

function formatOfnr(dimension) {
  if (!dimension) return "-";
  const status = dimension.status || "UNKNOWN";
  const suggestion = dimension.suggestion || "";
  return `${status} · ${suggestion}`;
}

function renderHistory() {
  const container = byId("conversationList");
  container.innerHTML = "";

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
}

function renderProgress(progress) {
  if (!progress) return;
  byId("progressPracticeCount").textContent = String(progress.practice_count ?? "-");
  byId("progressSummaryCount").textContent = String(progress.summary_count ?? "-");
  byId("progressRealCount").textContent = String(progress.real_world_used_count ?? "-");
  byId("progressOutcome").textContent = Number(progress.avg_outcome_score ?? 0).toFixed(2);
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
  persistRuntimeState();
  updateStepState();
  setNotice("复盘已提交。", "success");
  setOutput(data);
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

function showError(err) {
  const msg = String(err?.message || err);
  const mode = byId("authMode").value || "supabase";

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
  updateRuntimeMeta();
  renderHistory();
  renderSummary();
  byId("progressWeekStart").value = getCurrentWeekStart();
  syncOutcomeState();
  updateStepState();

  byId("templatePreset").addEventListener("change", applyTemplatePreset);
  byId("usedInRealWorld").addEventListener("change", syncOutcomeState);

  byId("supabaseSignupBtn").addEventListener("click", () => signupSupabase().catch(showError));
  byId("supabaseLoginBtn").addEventListener("click", () => loginSupabase().catch(showError));

  byId("clearTokenBtn").addEventListener("click", () => {
    byId("supabaseAccessToken").value = "";
    localStorage.removeItem("supabase_access_token");
    updateStepState();
    setNotice("已清空 Access Token。", "success");
  });

  byId("saveConfigBtn").addEventListener("click", saveConfig);

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
}

bind();
