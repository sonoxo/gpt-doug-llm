"use strict";
const $ = (selector) => document.querySelector(selector);
const messages = [];
const messageBox = $("#messages");
const model = $("#model");
const status = $("#status");
const engine = $("#engine");
const form = $("#composer");
const prompt = $("#prompt");
const send = $("#send");
let defaultModel = "qwen2.5:3b";

function append(role, content) {
  const section = document.createElement("div");
  section.className = "message " + role;
  const tag = document.createElement("span");
  tag.className = "who";
  tag.textContent = role === "user" ? "OPERATOR" : "GPT-SONOXO";
  const body = document.createElement("div");
  body.textContent = content; // Model output is always plain text, never trusted HTML.
  section.append(tag, body);
  messageBox.append(section);
  messageBox.scrollTop = messageBox.scrollHeight;
  return section;
}

async function setup() {
  try {
    const [health, models, graph] = await Promise.all([
      fetch("/api/health").then((r) => r.json()),
      fetch("/api/models").then((r) => r.json()),
      fetch("/api/ontology").then((r) => r.json()),
    ]);
    defaultModel = models.default || health.model;
    const names = models.models.length ? models.models : [defaultModel];
    for (const name of names) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      model.append(option);
    }
    if (names.includes(defaultModel)) model.value = defaultModel;
    status.textContent = health.blocked ? "AI STOP ACTIVE" :
                         models.connected ? "LOCAL ENGINE LINKED" : "OLLAMA OFFLINE";
    engine.textContent = health.blocked ? "STOPPED BY OPERATOR" :
                         models.connected ? String(models.models.length) + " model(s) detected" :
                         "Ollama offline — install and start Ollama";
    engine.className = models.connected && !health.blocked ? "engine online" : "engine offline";
    for (const node of graph.nodes) {
      const line = document.createElement("div");
      line.className = "node";
      const name = document.createElement("span");
      name.textContent = node.label;
      const type = document.createElement("em");
      type.textContent = node.kind;
      line.append(name, type);
      $("#graph").append(line);
    }
  } catch (error) {
    status.textContent = "LOCAL API ERROR";
    engine.textContent = String(error);
  }
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = prompt.value.trim();
  if (!content || send.disabled) return;
  prompt.value = "";
  messages.push({role:"user",content});
  while (messages.length > 16) messages.shift();
  append("user", content);
  send.disabled = true;
  const pending = append("assistant", "Processing with local inference…");
  try {
    const response = await fetch("/api/chat", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({model:model.value,messages}),
    });
    const result = await response.json();
    pending.remove();
    if (!response.ok) {
      append("assistant", "REQUEST ERROR: " + (result.error || response.status));
    } else {
      append("assistant", result.reply);
      messages.push({role:"assistant",content:result.reply.slice(0,4096)});
    }
  } catch (error) {
    pending.remove();
    append("assistant", "NETWORK ERROR: " + String(error));
  } finally {
    send.disabled = false;
    prompt.focus();
  }
});
prompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
$("#clear").addEventListener("click", () => {
  messages.length = 0;
  messageBox.replaceChildren();
  append("assistant", "Local conversation cleared. No history is saved by this app.");
});
setup();
