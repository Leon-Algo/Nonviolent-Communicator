function byId(id) {
  return document.getElementById(id);
}

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
  const userId = byId("mockUserId").value.trim();
  if (!userId) {
    throw new Error("Mock User UUID 不能为空");
  }
  return { apiBaseUrl, userId };
}

function authHeaders(userId) {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer mock_${userId}`,
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
  const { apiBaseUrl, userId } = getConfig();
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
    headers: authHeaders(userId),
    body: JSON.stringify(payload),
  });
  byId("sceneIdValue").textContent = data.scene_id || "-";
  setOutput(data);
}

async function createSession() {
  const { apiBaseUrl, userId } = getConfig();
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
    headers: authHeaders(userId),
    body: JSON.stringify(payload),
  });
  byId("sessionIdInput").value = data.session_id || "";
  setOutput(data);
}

async function sendMessage() {
  const { apiBaseUrl, userId } = getConfig();
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
    headers: authHeaders(userId),
    body: JSON.stringify(payload),
  });
  setOutput(data);
}

function showError(err) {
  setOutput({ error: String(err?.message || err) });
}

function saveConfig() {
  localStorage.setItem("api_base_url", byId("apiBaseUrl").value.trim());
  localStorage.setItem("mock_user_id", byId("mockUserId").value.trim());
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
  const savedUid = localStorage.getItem("mock_user_id") || ensureUserId();
  byId("apiBaseUrl").value = savedApi || window.location.origin;
  byId("mockUserId").value = savedUid;

  byId("newUserBtn").addEventListener("click", () => {
    const uid = crypto.randomUUID();
    byId("mockUserId").value = uid;
    localStorage.setItem("mock_user_id", uid);
    setOutput({ ok: true, message: "已生成新 mock 用户", user_id: uid });
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
