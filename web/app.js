function byId(id) {
  return document.getElementById(id);
}

const DEFAULT_SUPABASE_URL = "https://wiafjgjfdrajlxnlkray.supabase.co";
const DEFAULT_SUPABASE_ANON_KEY = "sb_publishable_EvEX2Hlp9e7SU4FcbpIrzQ_uusY6M87";

function ensureUserId() {
  const existing = localStorage.getItem("mock_user_id");
  if (existing) return existing;
  const uid = crypto.randomUUID();
  localStorage.setItem("mock_user_id", uid);
  return uid;
}

function setOutput(value) {
  byId("output").textContent = JSON.stringify(value, null, 2);
}

function getConfig() {
  const fallbackBaseUrl = window.location.origin;
  const apiBaseUrl =
    byId("apiBaseUrl").value.trim().replace(/\/+$/, "") || fallbackBaseUrl;
  const authMode = byId("authMode").value.trim() || "mock";
  const userId = byId("mockUserId").value.trim();
  const supabaseUrl = byId("supabaseUrl").value.trim().replace(/\/+$/, "");
  const supabaseAnonKey = byId("supabaseAnonKey").value.trim();
  const supabaseEmail = byId("supabaseEmail").value.trim();
  const supabasePassword = byId("supabasePassword").value;
  const supabaseAccessToken = byId("supabaseAccessToken").value.trim();

  if (authMode === "mock" && !userId) {
    throw new Error("Mock User UUID 不能为空");
  }
  if (authMode === "supabase" && !supabaseAccessToken) {
    throw new Error("Supabase 模式需要 Access Token，请先登录或粘贴 token");
  }

  return {
    apiBaseUrl,
    authMode,
    userId,
    supabaseUrl,
    supabaseAnonKey,
    supabaseEmail,
    supabasePassword,
    supabaseAccessToken,
  };
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
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
  }
  return data;
}

async function createScene() {
  const config = getConfig();
  const { apiBaseUrl } = config;
  const payload = {
    title: byId("sceneTitle").value.trim(),
    template_id: "PEER_FEEDBACK",
    counterparty_role: "PEER",
    relationship_level: "TENSE",
    goal: byId("sceneGoal").value.trim(),
    pain_points: ["对方容易防御", "我会急躁"],
    context: byId("sceneContext").value.trim(),
    power_dynamic: "PEER_LEVEL",
  };
  const data = await callApi(`${apiBaseUrl}/api/v1/scenes`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify(payload),
  });
  byId("sceneIdValue").textContent = data.scene_id || "-";
  setOutput(data);
}

async function createSession() {
  const config = getConfig();
  const { apiBaseUrl } = config;
  const sceneId = byId("sceneIdValue").textContent.trim();
  if (!sceneId || sceneId === "-") {
    throw new Error("请先创建场景");
  }
  const payload = {
    scene_id: sceneId,
    target_turns: Number(byId("targetTurns").value || 6),
  };
  const data = await callApi(`${apiBaseUrl}/api/v1/sessions`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify(payload),
  });
  byId("sessionIdInput").value = data.session_id || "";
  setOutput(data);
}

async function sendMessage() {
  const config = getConfig();
  const { apiBaseUrl } = config;
  const sessionId = byId("sessionIdInput").value.trim();
  if (!sessionId) {
    throw new Error("请先创建会话或填写 session_id");
  }
  const payload = {
    client_message_id: crypto.randomUUID(),
    content: byId("messageContent").value.trim(),
  };
  const data = await callApi(`${apiBaseUrl}/api/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: authHeaders(config),
    body: JSON.stringify(payload),
  });
  setOutput(data);
}

async function loginSupabase() {
  const config = getConfig();
  if (!config.supabaseUrl) {
    throw new Error("请填写 Supabase URL");
  }
  if (!config.supabaseAnonKey) {
    throw new Error("请填写 Supabase Anon Key");
  }
  if (!config.supabaseEmail || !config.supabasePassword) {
    throw new Error("请填写 Supabase 邮箱和密码");
  }

  const url = `${config.supabaseUrl}/auth/v1/token?grant_type=password`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: config.supabaseAnonKey,
    },
    body: JSON.stringify({
      email: config.supabaseEmail,
      password: config.supabasePassword,
    }),
  });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok || !data.access_token) {
    throw new Error(`Supabase 登录失败: ${JSON.stringify(data)}`);
  }

  byId("supabaseAccessToken").value = data.access_token;
  localStorage.setItem("supabase_access_token", data.access_token);
  setOutput({
    ok: true,
    message: "已获取 Supabase Access Token",
    token_type: data.token_type,
    expires_in: data.expires_in,
    refresh_token_exists: Boolean(data.refresh_token),
  });
}

function showError(err) {
  setOutput({ error: String(err?.message || err) });
}

function saveConfig() {
  localStorage.setItem("api_base_url", byId("apiBaseUrl").value.trim());
  localStorage.setItem("auth_mode", byId("authMode").value.trim() || "mock");
  localStorage.setItem("mock_user_id", byId("mockUserId").value.trim());
  localStorage.setItem("supabase_url", byId("supabaseUrl").value.trim());
  localStorage.setItem("supabase_anon_key", byId("supabaseAnonKey").value.trim());
  localStorage.setItem("supabase_email", byId("supabaseEmail").value.trim());
  localStorage.setItem("supabase_access_token", byId("supabaseAccessToken").value.trim());
  setOutput({ ok: true, message: "配置已保存到浏览器本地 localStorage" });
}

function bind() {
  const savedApiRaw = localStorage.getItem("api_base_url");
  const shouldForceProxy =
    !savedApiRaw ||
    /nvc-practice-api\.vercel\.app|api\.leonalgo\.site/.test(savedApiRaw);
  const savedApi = shouldForceProxy ? window.location.origin : savedApiRaw;
  if (shouldForceProxy) {
    localStorage.setItem("api_base_url", window.location.origin);
  }
  const authMode = localStorage.getItem("auth_mode") || "mock";
  const savedUid = localStorage.getItem("mock_user_id") || ensureUserId();
  const savedSupabaseUrl = localStorage.getItem("supabase_url") || DEFAULT_SUPABASE_URL;
  const savedSupabaseAnonKey =
    localStorage.getItem("supabase_anon_key") || DEFAULT_SUPABASE_ANON_KEY;
  const savedSupabaseEmail = localStorage.getItem("supabase_email") || "";
  const savedSupabaseAccessToken = localStorage.getItem("supabase_access_token") || "";
  byId("apiBaseUrl").value = savedApi || window.location.origin;
  byId("authMode").value = authMode;
  byId("mockUserId").value = savedUid;
  byId("supabaseUrl").value = savedSupabaseUrl;
  byId("supabaseAnonKey").value = savedSupabaseAnonKey;
  byId("supabaseEmail").value = savedSupabaseEmail;
  byId("supabaseAccessToken").value = savedSupabaseAccessToken;

  byId("newUserBtn").addEventListener("click", () => {
    if (byId("authMode").value === "supabase") {
      setOutput({ error: "当前是 Supabase 模式，不需要生成 mock 用户" });
      return;
    }
    const uid = crypto.randomUUID();
    byId("mockUserId").value = uid;
    localStorage.setItem("mock_user_id", uid);
    setOutput({ ok: true, message: "已生成新 mock 用户", user_id: uid });
  });
  byId("supabaseLoginBtn").addEventListener("click", () => loginSupabase().catch(showError));
  byId("clearTokenBtn").addEventListener("click", () => {
    byId("supabaseAccessToken").value = "";
    localStorage.removeItem("supabase_access_token");
    setOutput({ ok: true, message: "已清空 Supabase Access Token" });
  });
  byId("useProxyBtn").addEventListener("click", () => {
    byId("apiBaseUrl").value = window.location.origin;
    localStorage.setItem("api_base_url", window.location.origin);
    setOutput({
      ok: true,
      message: "已切换为同域代理模式",
      api_base_url: window.location.origin,
    });
  });
  byId("saveConfigBtn").addEventListener("click", saveConfig);
  byId("createSceneBtn").addEventListener("click", () => createScene().catch(showError));
  byId("createSessionBtn").addEventListener("click", () => createSession().catch(showError));
  byId("sendMessageBtn").addEventListener("click", () => sendMessage().catch(showError));
}

bind();
