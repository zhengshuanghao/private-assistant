const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const clearButton = document.querySelector("#clear-button");
const formStatus = document.querySelector("#form-status");
const serviceStatus = document.querySelector("#service-status");
const modelStatus = document.querySelector("#model-status");
const sessionStatus = document.querySelector("#session-status");
const modelForm = document.querySelector("#model-form");
const providerSelect = document.querySelector("#provider-select");
const modelSelect = document.querySelector("#model-select");
const modelFormStatus = document.querySelector("#model-form-status");

let providerCatalog = [];
let currentSessionId = localStorage.getItem("private-assistent-session") || crypto.randomUUID();
localStorage.setItem("private-assistent-session", currentSessionId);

function appendMessage(role, text) {
  const item = document.createElement("article");
  item.className = `message ${role}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  item.appendChild(paragraph);
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
}

function resetMessages() {
  messages.innerHTML = "";
}

function setBusy(isBusy) {
  sendButton.disabled = isBusy;
  input.disabled = isBusy;
  formStatus.textContent = isBusy ? "正在发送" : "";
}

function selectedProvider() {
  return providerCatalog.find((provider) => provider.id === providerSelect.value);
}

function renderProviderOptions(defaultModel) {
  providerSelect.innerHTML = "";
  for (const provider of providerCatalog) {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = provider.name;
    providerSelect.appendChild(option);
  }
  providerSelect.value = defaultModel.provider_id;
  if (!selectedProvider() && providerCatalog.length > 0) {
    providerSelect.value = providerCatalog[0].id;
  }
  renderModelOptions(defaultModel.model);
}

function renderModelOptions(selectedModel) {
  modelSelect.innerHTML = "";
  const provider = selectedProvider();
  if (!provider) return;
  for (const model of provider.models) {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.name;
    modelSelect.appendChild(option);
  }
  if (selectedModel && provider.models.some((model) => model.id === selectedModel)) {
    modelSelect.value = selectedModel;
  }
}

function setModelStatus(slot) {
  modelStatus.textContent = `${slot.provider_id}/${slot.model}`;
}

function setSessionStatus(extra = "") {
  const shortId = currentSessionId.slice(0, 8);
  sessionStatus.textContent = extra ? `${shortId} · ${extra}` : shortId;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    serviceStatus.textContent = `在线 · v${data.version}`;
  } catch (error) {
    serviceStatus.textContent = "不可用";
  }
}

async function loadProviders() {
  try {
    const response = await fetch("/api/providers");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    providerCatalog = (data.providers || []).filter((provider) => provider.enabled);
    renderProviderOptions(data.default_model);
    setModelStatus(data.default_model);
  } catch (error) {
    modelStatus.textContent = "配置不可用";
    modelFormStatus.textContent = "无法加载模型配置";
  }
}

async function loadSessionMessages() {
  setSessionStatus("加载中");
  try {
    const response = await fetch(`/api/sessions/${encodeURIComponent(currentSessionId)}/messages`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    resetMessages();
    if (data.length === 0) {
      appendMessage("assistant", "你好，我已经准备好。当前会话会保留上下文，你可以继续多轮追问。");
    } else {
      for (const message of data) {
        appendMessage(message.role, message.content);
      }
    }
    setSessionStatus(`${data.length} 条消息`);
  } catch (error) {
    setSessionStatus("加载失败");
  }
}

providerSelect.addEventListener("change", () => {
  const provider = selectedProvider();
  renderModelOptions(provider?.models?.[0]?.id || "");
});

modelForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    provider_id: providerSelect.value,
    model: modelSelect.value,
  };
  modelFormStatus.textContent = "正在保存";
  try {
    const response = await fetch("/api/models/default", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    setModelStatus(data);
    modelFormStatus.textContent = "已保存";
  } catch (error) {
    modelFormStatus.textContent = "保存失败";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  appendMessage("user", message);
  input.value = "";
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: currentSessionId }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    currentSessionId = data.session_id || currentSessionId;
    localStorage.setItem("private-assistent-session", currentSessionId);
    appendMessage("assistant", data.reply || "没有返回内容");
    setSessionStatus(`${data.context_messages || 0} 条上下文`);
  } catch (error) {
    appendMessage("error", "请求失败，请确认本地服务仍在运行。");
  } finally {
    setBusy(false);
    input.focus();
  }
});

clearButton.addEventListener("click", async () => {
  try {
    await fetch(`/api/sessions/${encodeURIComponent(currentSessionId)}/messages`, {
      method: "DELETE",
    });
  } catch (error) {
    // Keep the UI responsive even if the local service is unavailable.
  }
  resetMessages();
  appendMessage("assistant", "对话已清空。继续输入新的任务即可。");
  setSessionStatus("0 条消息");
  input.focus();
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    form.requestSubmit();
  }
});

setSessionStatus();
checkHealth();
loadProviders();
loadSessionMessages();
