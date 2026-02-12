function byId(id) {
  return document.getElementById(id);
}

const DEFAULT_SUPABASE_URL = "https://wiafjgjfdrajlxnlkray.supabase.co";
const DEFAULT_SUPABASE_ANON_KEY = "sb_publishable_EvEX2Hlp9e7SU4FcbpIrzQ_uusY6M87";

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

const DEV_CONTEXT = isDevContext();

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

function applyModeVisibility() {
  document.querySelectorAll("[data-dev-only]").forEach((el) => {
    el.classList.toggle("is-hidden", !DEV_CONTEXT);
  });
}

function refreshAuthModeBadge() {
  byId("currentAuthMode").textContent = byId("authMode").value || "supabase";
}

function setAuthMode(mode) {
  byId("authMode").value = mode;
  localStorage.setItem("auth_mode", mode);
  refreshAuthModeBadge();
}

function switchToMockMode(reason) {
  if (!DEV_CONTEXT) {
    throw new Error("线上已禁用 Mock 模式，请使用 Supabase 登录");
  }
  const uid = byId("mockUserId").value.trim() || crypto.randomUUID();
  byId("mockUserId").value = uid;
  localStorage.setItem("mock_user_id", uid);
  setAuthMode("mock");
  if (reason) {
    setOutput({
      warning: reason,
      next_step: "直接点击“创建场景”即可继续联调。",
      mock_user_id: uid,
    });
  }
  return uid;
}

function getConfig(options = {}) {
  const { requireAuthToken = true, requireMockUser = true } = options;
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

  if (authMode === "mock" && requireMockUser && !userId) {
    throw new Error("Mock User UUID 不能为空");
  }
  if (authMode === "supabase" && requireAuthToken && !supabaseAccessToken) {
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
  const config = getConfig({ requireAuthToken: true });
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
  const config = getConfig({ requireAuthToken: true });
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
  const config = getConfig({ requireAuthToken: true });
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

async function fetchSupabasePasswordToken(config) {
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
  return data;
}

function persistSupabaseSession(config, session, message) {
  byId("supabaseAccessToken").value = session.access_token;
  setAuthMode("supabase");
  localStorage.setItem("supabase_email", config.supabaseEmail);
  localStorage.setItem("supabase_access_token", session.access_token);
  setOutput({
    ok: true,
    message,
    token_type: session.token_type,
    expires_in: session.expires_in,
    refresh_token_exists: Boolean(session.refresh_token),
  });
}

async function loginSupabase() {
  const config = getConfig({ requireAuthToken: false, requireMockUser: false });
  setAuthMode("supabase");
  if (!config.supabaseUrl) {
    throw new Error("请填写 Supabase URL");
  }
  if (!config.supabaseAnonKey) {
    throw new Error("请填写 Supabase Anon Key");
  }
  if (!config.supabaseEmail || !config.supabasePassword) {
    throw new Error("请填写 Supabase 邮箱和密码");
  }
  const data = await fetchSupabasePasswordToken(config);
  persistSupabaseSession(config, data, "已获取 Supabase Access Token");
}

async function signupSupabase() {
  const config = getConfig({ requireAuthToken: false, requireMockUser: false });
  setAuthMode("supabase");
  if (!config.supabaseUrl) {
    throw new Error("请填写 Supabase URL");
  }
  if (!config.supabaseAnonKey) {
    throw new Error("请填写 Supabase Anon Key");
  }
  if (!config.supabaseEmail || !config.supabasePassword) {
    throw new Error("请填写注册邮箱和密码");
  }

  const signupUrl = `${config.supabaseUrl}/auth/v1/signup`;
  const signupRes = await fetch(signupUrl, {
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
  const signupText = await signupRes.text();
  let signupData = {};
  try {
    signupData = signupText ? JSON.parse(signupText) : {};
  } catch {
    signupData = { raw: signupText };
  }

  if (!signupRes.ok) {
    if (
      signupRes.status === 429 ||
      signupData?.error_code === "over_email_send_rate_limit" ||
      String(signupData?.msg || "").includes("email rate limit exceeded")
    ) {
      try {
        const loginData = await fetchSupabasePasswordToken(config);
        persistSupabaseSession(
          config,
          loginData,
          "注册触发邮件限流，但检测到该邮箱可直接登录，已自动登录。"
        );
        return;
      } catch {
        if (!DEV_CONTEXT) {
          setOutput({
            error: "注册触发邮件限流，且该邮箱当前无法直接登录。",
            hint: "请稍后重试，或更换邮箱继续；开发期可用 ?dev=1 开启 Mock 快测。",
          });
          return;
        }
        switchToMockMode(
          "Supabase 注册触发邮件限流，且当前邮箱无法直接登录。已切到 Mock 模式。若要继续真实注册，请在 Supabase 控制台临时关闭 Email Confirm 后再试。"
        );
        return;
      }
    }
    throw new Error(`注册失败: ${JSON.stringify(signupData)}`);
  }

  if (signupData.access_token) {
    byId("supabaseAccessToken").value = signupData.access_token;
    setAuthMode("supabase");
    localStorage.setItem("supabase_email", config.supabaseEmail);
    localStorage.setItem("supabase_access_token", signupData.access_token);
    setOutput({
      ok: true,
      message: "注册成功，已自动登录",
      expires_in: signupData.expires_in,
    });
    return;
  }

  // Some Supabase projects require email verification before login.
  await loginSupabase();
}

function showError(err) {
  const msg = String(err?.message || err);
  const authMode = byId("authMode")?.value || "supabase";
  if (authMode === "mock" && msg.includes("\"error_code\":\"UNAUTHORIZED\"")) {
    setOutput({
      error: msg,
      hint: "当前后端可能关闭了 Mock 鉴权（MOCK_AUTH_ENABLED=false）。开发联调请开启它，或改用 Supabase 登录模式。",
    });
    return;
  }
  if (msg.includes("invalid or expired access token") && authMode === "supabase") {
    if (!DEV_CONTEXT) {
      setOutput({
        error: msg,
        hint: "Supabase token 无效或过期，请重新点击“登录并获取 Token”。",
      });
      return;
    }
    const uid = switchToMockMode();
    setOutput({
      error: msg,
      hint: "Supabase token 无效或过期，已自动切换到 Mock 模式让你不中断测试。",
      mock_user_id: uid,
      next_step: "可继续创建场景/会话；也可重新登录后再切回 Supabase。",
    });
    return;
  }
  setOutput({ error: msg });
}

function saveConfig() {
  localStorage.setItem("api_base_url", byId("apiBaseUrl").value.trim());
  setAuthMode(byId("authMode").value.trim() || "supabase");
  localStorage.setItem("mock_user_id", byId("mockUserId").value.trim());
  localStorage.setItem("supabase_url", byId("supabaseUrl").value.trim());
  localStorage.setItem("supabase_anon_key", byId("supabaseAnonKey").value.trim());
  localStorage.setItem("supabase_email", byId("supabaseEmail").value.trim());
  localStorage.setItem("supabase_access_token", byId("supabaseAccessToken").value.trim());
  setOutput({ ok: true, message: "配置已保存到浏览器本地 localStorage" });
}

function bind() {
  applyModeVisibility();
  const savedApiRaw = localStorage.getItem("api_base_url");
  const shouldForceProxy =
    !savedApiRaw ||
    /nvc-practice-api\.vercel\.app|api\.leonalgo\.site/.test(savedApiRaw);
  const savedApi = shouldForceProxy ? window.location.origin : savedApiRaw;
  if (shouldForceProxy) {
    localStorage.setItem("api_base_url", window.location.origin);
  }
  const authMode = DEV_CONTEXT
    ? localStorage.getItem("auth_mode") || "supabase"
    : "supabase";
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
  if (!DEV_CONTEXT) {
    setAuthMode("supabase");
  }
  refreshAuthModeBadge();

  if (DEV_CONTEXT) {
    byId("newUserBtn").addEventListener("click", () => {
      const uid = switchToMockMode();
      setOutput({ ok: true, message: "已生成新 mock 用户", user_id: uid });
    });
    byId("useMockModeBtn").addEventListener("click", () => {
      const uid = switchToMockMode();
      setOutput({ ok: true, message: "已切换到 Mock 模式", user_id: uid });
    });
    byId("useSupabaseModeBtn").addEventListener("click", () => {
      setAuthMode("supabase");
      setOutput({ ok: true, message: "已切换到 Supabase 模式，请先登录获取 token" });
    });
    byId("authMode").addEventListener("change", () => {
      setAuthMode(byId("authMode").value || "supabase");
    });
  }
  byId("supabaseLoginBtn").addEventListener("click", () => loginSupabase().catch(showError));
  byId("supabaseSignupBtn").addEventListener("click", () => signupSupabase().catch(showError));
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
