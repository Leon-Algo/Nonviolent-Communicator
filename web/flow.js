/* =========================================================
 * 橘晴 · flow.js（2026-07-18）
 * UI-delight 视图层：3 视图（首页/对练/复盘）+ 登录浮层。
 * 原则：app.js 零改动。本文件只做两件事——
 *   1) 包装 app.js 暴露到全局的函数（window.x = wrapper），
 *      保持原签名/返回值/异常向外抛，原 .catch(showError) 链路不变；
 *   2) 绑定新增的 flow 级元素（id 以 flow 开头）。
 * 加载顺序：app.js（bind 已执行完毕）之后。
 * ======================================================= */
(function () {
  "use strict";

  // vendor/agora-agent-client-toolkit/index.mjs 是 esbuild 产物，
  // 残留了两处 Node 的 process.env.NODE_ENV 引用（第 236/1869 行）。
  // 浏览器没有 process，语音启动时的动态 import 会抛 ReferenceError。
  // 在其求值前补一个最小 shim（本文件加载远早于任何语音操作）。
  if (typeof window.process === "undefined") {
    window.process = { env: { NODE_ENV: "production" } };
  }

  var ONBOARDING_DONE_KEY = "nvc_onboarding_done";
  var PAGES = ["home", "practice", "review"];

  var $ = function (id) {
    return document.getElementById(id);
  };

  // app.js 的 state 是 const（不在 window 上），经全局词法作用域读取，做防御
  var getState = function () {
    return typeof state !== "undefined" ? state : {};
  };

  var hasToken = function () {
    if (typeof window.isAuthReady === "function") {
      try {
        return Boolean(window.isAuthReady());
      } catch (err) {
        // fall through
      }
    }
    var tokenInput = $("supabaseAccessToken");
    return Boolean(tokenInput && tokenInput.value.trim());
  };

  var cap = function (s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  var currentPage = "home";

  /* ---------------------------------------------------------
   * 视图切换
   * ------------------------------------------------------- */
  function go(page, options) {
    var opts = options || {};
    if (PAGES.indexOf(page) === -1) return;
    currentPage = page;
    document.body.dataset.flowPage = page;
    for (var i = 0; i < PAGES.length; i++) {
      var el = $("page" + cap(PAGES[i]));
      if (!el) continue;
      var active = PAGES[i] === page;
      el.classList.toggle("is-active", active);
      el.setAttribute("aria-hidden", active ? "false" : "true");
    }
    window.scrollTo({ top: 0, behavior: "smooth" });

    if (page === "home") syncHome();
    if (page === "practice") {
      syncPracticeChrome();
      if (!opts.skipFocus) {
        window.setTimeout(function () {
          var input = $("messageContent");
          if (input) input.focus();
        }, 380);
      }
    }
    if (page === "review") onEnterReview();
  }

  function current() {
    return currentPage;
  }

  /* ---------------------------------------------------------
   * 首页状态（新访客 / 老用户双态）
   * ------------------------------------------------------- */
  function syncHome() {
    var returning = hasToken() || localStorage.getItem(ONBOARDING_DONE_KEY) === "1";
    var welcome = $("homeHeroWelcome");
    var compact = $("homeHeroCompact");
    if (welcome) welcome.classList.toggle("is-hidden", returning);
    if (compact) compact.classList.toggle("is-hidden", !returning);

    var s = getState();
    var resumeCard = $("flowResumeCard");
    if (resumeCard) {
      if (s.sessionId && s.turn > 0) {
        var sceneName = ($("sceneTitle") && $("sceneTitle").value.trim()) || "上次的练习";
        var meta = $("flowResumeMeta");
        if (meta) meta.textContent = sceneName + " · 已练 " + s.turn + " 轮";
        resumeCard.classList.remove("is-hidden");
      } else {
        resumeCard.classList.add("is-hidden");
      }
    }

    var loginBtn = $("flowLoginBtn");
    if (loginBtn) loginBtn.classList.toggle("is-hidden", hasToken());

    // 未登录新客没有历史可看，收起历史入口，首页更干净
    var historyDetails = $("homeHistoryDetails");
    if (historyDetails) historyDetails.classList.toggle("is-hidden", !hasToken());
  }

  /* ---------------------------------------------------------
   * 对练页外观（场景镜像 / 轮次 / 发送按钮显隐）
   * ------------------------------------------------------- */
  function syncPracticeChrome() {
    var title = $("sceneTitle") && $("sceneTitle").value.trim();
    var mirror = $("flowSceneMirror");
    if (mirror) mirror.textContent = title || "自由练习";
    var target = $("flowTargetTurns");
    if (target) target.textContent = ($("targetTurns") && $("targetTurns").value) || "6";

    var hasSession = Boolean(getState().sessionId);
    var startBtn = $("startPracticeBtn");
    var sendBtn = $("sendMessageBtn");
    if (startBtn) startBtn.classList.toggle("is-hidden", hasSession);
    if (sendBtn) sendBtn.classList.toggle("is-hidden", !hasSession);
  }

  /* ---------------------------------------------------------
   * 聊天气泡化（renderHistory 的 post-pass）
   * renderHistory 每次重建 DOM，这里只做增量标记，可重复执行。
   * ------------------------------------------------------- */
  function postProcessChat() {
    var list = $("conversationList");
    if (!list) return;

    var empty = list.querySelector(".empty");
    if (empty) {
      empty.innerHTML = "第一句话最难。<br>选一个开场句式，或者直接写下来——这里没有对错。";
    }

    var cards = list.querySelectorAll(".turn-card");
    for (var i = 0; i < cards.length; i++) {
      var ps = cards[i].querySelectorAll("p");
      for (var j = 0; j < ps.length; j++) {
        var p = ps[j];
        if (p.classList.contains("turn-head") || p.classList.contains("turn-keyline")) continue;
        var text = p.textContent || "";
        if (text.indexOf("你: ") === 0) {
          p.classList.add("bubble", "bubble-user");
          p.textContent = text.slice(3);
        } else if (text.indexOf("AI: ") === 0) {
          p.classList.add("bubble", "bubble-ai");
          p.textContent = text.slice(4);
        }
      }
    }

    // 自动滚到最新一轮；用户用“跳到轮次”回看时不打断
    var s = getState();
    var last = cards.length ? cards[cards.length - 1] : null;
    if (last) {
      var lastTurn = Number(String(last.id || "").replace("turn-card-", "")) || 0;
      var selected = Number(s.selectedTurn) || 0;
      if (selected >= lastTurn) {
        window.setTimeout(function () {
          last.scrollIntoView({ behavior: "smooth", block: "end" });
        }, 60);
      }
    }
  }

  /* ---------------------------------------------------------
   * 登录浮层
   * ------------------------------------------------------- */
  function openAuthOverlay() {
    var overlay = $("flowAuthOverlay");
    if (!overlay) return;
    overlay.classList.add("is-open");
    window.setTimeout(function () {
      var email = $("supabaseEmail");
      var pwd = $("supabasePassword");
      var target = email && !email.value.trim() ? email : pwd;
      if (target) target.focus();
    }, 280);
  }

  function closeAuthOverlay() {
    var overlay = $("flowAuthOverlay");
    if (overlay) overlay.classList.remove("is-open");
  }

  /* ---------------------------------------------------------
   * 柔性加载罩（callApi 包装，>300ms 才现身）
   * ------------------------------------------------------- */
  var LOADING_COPY = [
    ["/scenes", "在布置你的练习场景…"],
    ["/messages", "对方正在读你的话…"],
    ["/summary", "在整理你的行动卡…"],
    ["/voice", "在接通语音频道…"],
    ["/sessions", "在翻找你的练习记录…"],
    ["/auth", "在确认你的身份…"],
  ];
  var inflight = 0;
  var loadingTimer = null;

  function pickLoadingCopy(url) {
    var u = String(url || "");
    for (var i = 0; i < LOADING_COPY.length; i++) {
      if (u.indexOf(LOADING_COPY[i][0]) !== -1) return LOADING_COPY[i][1];
    }
    return "在准备你的练习空间…";
  }

  function wrapCallApi() {
    if (typeof window.callApi !== "function") return;
    var orig = window.callApi;
    window.callApi = function (url, options) {
      inflight += 1;
      if (inflight === 1) {
        loadingTimer = window.setTimeout(function () {
          if (inflight > 0) {
            var text = $("flowLoadingText");
            if (text) text.textContent = pickLoadingCopy(url);
            var mask = $("flowLoading");
            if (mask) mask.classList.add("is-visible");
          }
        }, 300);
      }
      return Promise.resolve()
        .then(function () {
          return orig(url, options);
        })
        .finally(function () {
          inflight -= 1;
          if (inflight <= 0) {
            inflight = 0;
            window.clearTimeout(loadingTimer);
            var mask = $("flowLoading");
            if (mask) mask.classList.remove("is-visible");
          }
        });
    };
  }

  /* ---------------------------------------------------------
   * 通知软化 + 自动消隐（setNotice 包装）
   * ------------------------------------------------------- */
  var NOTICE_SOFTEN = [
    ["网络连接异常", "好像有点卡，检查下网络再试一次？"],
    ["后端代理暂时不可用", "服务打了个盹，稍后再试一次？"],
    ["Token 无效或过期", "登录好像过期了，重新登录一下？"],
    ["请求过于频繁", "有点太急啦，喝口水再来？"],
    ["服务端暂时异常", "我们这边出了点状况，稍后再试试？"],
    ["当前离线或网络不可用", "现在好像离线了，连上网络后再试？"],
    ["操作失败", "这次没有成功，再试一次看看？"],
    ["请先点击“创建场景并发送第 1 轮”", "先点一次「发送」，把第一句话说出口"],
    ["已重置会话状态", "已经清好啦，说出第一句话就开始新的练习"],
    ["行动卡已生成", "行动卡写好了，连同这封信一起看看吧"],
    ["请先完成至少 1 轮练习", "先练一轮，再来领取行动卡"],
  ];
  var noticeTimer = null;

  function wrapSetNotice() {
    if (typeof window.setNotice !== "function") return;
    var orig = window.setNotice;
    window.setNotice = function (message, tone) {
      var msg = String(message || "");
      for (var i = 0; i < NOTICE_SOFTEN.length; i++) {
        if (msg.indexOf(NOTICE_SOFTEN[i][0]) !== -1) {
          msg = NOTICE_SOFTEN[i][1];
          break;
        }
      }
      var result = orig(msg, tone);
      window.clearTimeout(noticeTimer);
      var dwell = tone === "success" ? 3200 : 6000;
      noticeTimer = window.setTimeout(function () {
        var bar = $("noticeBar");
        if (bar) bar.classList.add("is-hidden");
      }, dwell);
      return result;
    };
  }

  /* ---------------------------------------------------------
   * 包装：登录拦截点 → 浮层
   * ------------------------------------------------------- */
  function wrapFocusAuthPanel() {
    window.focusAuthPanel = function () {
      openAuthOverlay();
    };
  }

  /* ---------------------------------------------------------
   * 包装：登录/注册成功 → 记 flag、关浮层、去该去的地方
   * ------------------------------------------------------- */
  function wrapAuthSuccess(fnName) {
    if (typeof window[fnName] !== "function") return;
    var orig = window[fnName];
    window[fnName] = function () {
      var self = this;
      var args = arguments;
      return Promise.resolve()
        .then(function () {
          return orig.apply(self, args);
        })
        .then(function () {
          if (!hasToken()) return; // 如注册触发邮件频控：留在浮层
          localStorage.setItem(ONBOARDING_DONE_KEY, "1");
          closeAuthOverlay();
          if (getState().sessionId) {
            go("practice", { skipFocus: true });
          } else {
            go("home");
          }
        });
      // 异常继续向上抛，bind() 里的 .catch(showError) 原样生效
    };
  }

  /* ---------------------------------------------------------
   * 包装：历史会话续练 → 对练页
   * ------------------------------------------------------- */
  function wrapContinueSession() {
    if (typeof window.continueSessionFromHistory !== "function") return;
    var orig = window.continueSessionFromHistory;
    window.continueSessionFromHistory = function (sessionId) {
      var self = this;
      return Promise.resolve()
        .then(function () {
          return orig.call(self, sessionId);
        })
        .then(function (result) {
          go("practice", { skipFocus: true });
          return result;
        });
    };
  }

  /* ---------------------------------------------------------
   * 包装：renderHistory → 气泡 post-pass + 外观同步
   * ------------------------------------------------------- */
  function wrapRenderHistory() {
    if (typeof window.renderHistory !== "function") return;
    var orig = window.renderHistory;
    window.renderHistory = function () {
      var result = orig.apply(this, arguments);
      postProcessChat();
      syncPracticeChrome();
      return result;
    };
  }

  /* ---------------------------------------------------------
   * 包装：showError → 401/过期时自动唤起登录浮层
   * ------------------------------------------------------- */
  function wrapShowError() {
    if (typeof window.showError !== "function") return;
    var orig = window.showError;
    window.showError = function (err) {
      orig.call(this, err);
      var msg = String((err && err.message) || err || "");
      var details = {};
      if (typeof window.getErrorDetails === "function") {
        try {
          details = window.getErrorDetails(err) || {};
        } catch (e) {
          details = {};
        }
      }
      var code = String(details.errorCode || "").toUpperCase();
      if (
        details.status === 401 ||
        code === "UNAUTHORIZED" ||
        msg.indexOf("invalid or expired access token") !== -1
      ) {
        openAuthOverlay();
      }
    };
  }

  /* ---------------------------------------------------------
   * 复盘页：自动生成行动卡 + 写信
   * ------------------------------------------------------- */
  function onEnterReview() {
    ensureReviewMaterial()
      .then(function () {
        var s = getState();
        var hasMaterial = s.sessionId && (s.turn > 0 || (s.history && s.history.length > 0));
        if (hasMaterial && !s.summary && typeof window.generateSummary === "function") {
          return Promise.resolve(window.generateSummary()).catch(function () {
            /* 失败时保留手动按钮，不打断页面 */
          });
        }
        return null;
      })
      .then(function () {
        renderLetter();
      });
  }

  // 语音对练刚结束时，轮次只存在后端（本地 turn=0/history 为空）：
  // 先把会话内容拉回来，再生成行动卡和信。
  function ensureReviewMaterial() {
    var s = getState();
    var hasLocal = s.sessionId && (s.turn > 0 || (s.history && s.history.length > 0));
    if (hasLocal || !s.sessionId || typeof window.loadSessionHistory !== "function") {
      return Promise.resolve();
    }
    return Promise.resolve(window.loadSessionHistory(s.sessionId)).catch(function () {
      /* 拉取失败就按空素材渲染，信里会引导用户回去练习 */
    });
  }

  function renderLetter() {
    var body = $("flowLetterBody");
    if (!body) return;
    var s = getState();
    var scene = ($("sceneTitle") && $("sceneTitle").value.trim()) || "这段对话";
    var turns = s.turn || (s.history && s.history.length) || 0;
    var summary = s.summary;

    body.innerHTML = "";
    var add = function (text) {
      var p = document.createElement("p");
      p.textContent = text;
      body.appendChild(p);
    };

    if (!turns && !summary) {
      add("亲爱的你：");
      add("这里会有一封写给你的信。等你完成几轮练习，我会把你想说的话、你的进步，都认真地收进来。");
      add("先回到对练页，把第一句话说出来吧。");
      return;
    }

    var scores = (s.history || [])
      .map(function (h) {
        return h && h.feedback && typeof h.feedback.overall_score === "number"
          ? h.feedback.overall_score
          : null;
      })
      .filter(function (v) {
        return v !== null;
      });
    var best = scores.length ? Math.max.apply(null, scores) : null;

    add("亲爱的你：");
    add(
      "在「" +
        scene +
        "」里，你认真练了 " +
        turns +
        " 轮。愿意在开口之前先练一遍，这本身就是一种温柔——对对方，也对自己。"
    );
    if (best !== null) {
      add(
        "你最好的一句话拿到了 " +
          best +
          " 分。能看到自己的表达一轮一轮变得更清楚、更柔软，是很了不起的事。"
      );
    }
    if (summary && summary.opening_line) {
      add("如果只想带走一句话，试试这句开场：「" + summary.opening_line + "」");
    }
    if (summary && summary.risk_triggers && summary.risk_triggers.length) {
      add(
        "也记得照顾好自己：聊到「" +
          summary.risk_triggers[0] +
          "」这类话题时最容易激动，先深呼吸三秒，再开口。"
      );
    }
    add("愿你在真实的对话里，也能像在这里一样，被好好听见。");
  }

  /* ---------------------------------------------------------
   * flow 级元素绑定（全部是新 id，不碰 app.js 的绑定）
   * ------------------------------------------------------- */
  function bindFlowControls() {
    var on = function (id, fn) {
      var el = $(id);
      if (el) el.addEventListener("click", fn);
    };

    on("flowStartBtn", function () {
      go("practice");
    });
    on("flowBackHomeBtn", function () {
      go("home");
    });
    on("flowResumeBtn", function () {
      go("practice", { skipFocus: true });
    });
    on("flowFinishBtn", function () {
      go("review");
    });
    on("flowAgainBtn", function () {
      var resetBtn = $("newSessionBtn");
      if (resetBtn) resetBtn.click(); // 复用 app.js 的重置逻辑
      go("home");
    });
    on("flowLoginBtn", function () {
      openAuthOverlay();
    });
    on("flowGotoCardBtn", function () {
      var card = $("reviewPanel");
      if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    on("flowAuthCloseBtn", function () {
      closeAuthOverlay();
    });

    // 浮层：遮罩点击 / Esc 关闭
    var overlay = $("flowAuthOverlay");
    if (overlay) {
      overlay.addEventListener("click", function (event) {
        if (event.target === overlay) closeAuthOverlay();
      });
    }
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeAuthOverlay();
    });

    // “已登录，去对练”（app.js 自身还有校验与提示，这里只做导航）
    var gotoBtn = $("gotoPracticeFromAuthBtn");
    if (gotoBtn) {
      gotoBtn.addEventListener("click", function () {
        if (!hasToken()) return;
        closeAuthOverlay();
        go("practice");
      });
    }

    // 场景 chips：设置隐藏 select 并派发 change，复用 applyTemplatePreset
    var chips = document.querySelectorAll(".chip[data-preset]");
    var presetSelect = $("templatePreset");
    var activateChip = function (value) {
      for (var i = 0; i < chips.length; i++) {
        chips[i].classList.toggle("is-active", chips[i].dataset.preset === value);
      }
    };
    for (var i = 0; i < chips.length; i++) {
      chips[i].addEventListener("click", function () {
        var value = this.dataset.preset;
        if (presetSelect) {
          presetSelect.value = value;
          presetSelect.dispatchEvent(new Event("change", { bubbles: true }));
        }
        activateChip(value);
        syncPracticeChrome();
      });
    }
    if (presetSelect) activateChip(presetSelect.value);

    // 场景名 / 轮次镜像
    var sceneTitleInput = $("sceneTitle");
    if (sceneTitleInput) {
      sceneTitleInput.addEventListener("input", syncPracticeChrome);
    }
    var targetTurnsInput = $("targetTurns");
    if (targetTurnsInput) {
      targetTurnsInput.addEventListener("input", syncPracticeChrome);
    }
  }

  /* ---------------------------------------------------------
   * 开发者面板：默认隐藏，仅 ?dev=1 时显示。
   * app.js 的 applyModeVisibility 在 localhost 会把它放出来，
   * 这里在其之后执行，重新按用户视角收口。
   * ------------------------------------------------------- */
  function applyDevPanelVisibility() {
    var dev = new URLSearchParams(window.location.search).get("dev") === "1";
    var blocks = document.querySelectorAll("[data-dev-only]");
    for (var i = 0; i < blocks.length; i++) {
      blocks[i].classList.toggle("is-hidden", !dev);
    }
    // 包裹容器一并收起，避免留下一截空白
    var shell = document.querySelector(".shell");
    if (shell) shell.classList.toggle("is-hidden", !dev);
  }

  /* ---------------------------------------------------------
   * 首次路由：老用户跳过欢迎页
   * ------------------------------------------------------- */
  function initRoute() {
    var s = getState();
    if (hasToken() && s.sessionId && s.turn > 0) {
      // 有未完成的练习：直接回到对练页
      go("practice", { skipFocus: true });
      return;
    }
    go("home");
  }

  /* ---------------------------------------------------------
   * 初始化（app.js 的 bind() 已同步执行完毕）
   * ------------------------------------------------------- */
  wrapFocusAuthPanel();
  wrapAuthSuccess("loginSupabase");
  wrapAuthSuccess("signupSupabase");
  wrapContinueSession();
  wrapRenderHistory();
  wrapShowError();
  wrapCallApi();
  wrapSetNotice();
  bindFlowControls();
  applyDevPanelVisibility();
  initRoute();
  // bind() 的首次 renderHistory 早于包装执行，这里补一次 post-pass
  postProcessChat();
  syncPracticeChrome();
})();
