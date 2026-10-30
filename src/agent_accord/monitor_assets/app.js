/**
 * Render the live, read-only Agent Accord monitor from same-origin SQLite snapshots.
 * All register fields use textContent. Polls never overlap, acknowledge messages,
 * or mutate cards. The UI retains its last snapshot and labels connection failures.
 */
"use strict";

const view = { snapshot: null, agent: "", filter: "open", search: "", selected: null, busy: false };

/** @param {string} id - Element ID. @returns {HTMLElement} Matching UI element. */
function byId(id) { return document.getElementById(id); }

/**
 * Create a text-only element; register content never becomes executable markup.
 * @param {string} tag - HTML element name controlled by this module.
 * @param {string} className - Optional CSS classes.
 * @param {string|number} text - Untrusted text to display literally.
 * @returns {HTMLElement} A detached element.
 */
function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = String(text);
  return node;
}

/** @param {string} timestamp - ISO date. @returns {string} Human-readable elapsed time. */
function ago(timestamp) {
  const seconds = Math.max(0, Math.floor((Date.now() - Date.parse(timestamp)) / 1000));
  if (!Number.isFinite(seconds)) return "Unknown time";
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/** @param {string} timestamp - ISO date. @returns {string} Localized full timestamp. */
function fullTime(timestamp) { return new Date(timestamp).toLocaleString(); }

/** @param {string} agent - Agent identity. @returns {string} Compact identity initials. */
function initials(agent) { return agent.slice(0, 2).toUpperCase(); }

/** @param {Object} task - Published card. @returns {string} State, including stale ownership. */
function label(task) {
  return task.state === "done" ? "Completed" : task.stale ? `${task.state === "paused" ? "Paused · " : ""}Stale` : task.state === "active" ? "Active" : "Paused";
}

/** @param {Object} task - Published card. @returns {HTMLElement} Visible state label. */
function badge(task) { return element("span", `badge ${task.state} ${task.stale && task.state !== "done" ? "stale" : ""}`, label(task)); }

/** @param {string} title - Empty-state title. @param {string} text - Hint. @returns {HTMLElement} Empty state. */
function empty(title, text) {
  const box = element("div", "empty");
  box.append(element("strong", "", title), element("p", "", text));
  return box;
}

/**
 * Apply agent, status, and text filters to a card without hiding other owners in storage.
 * @param {Object} task - Full task record.
 * @returns {boolean} Whether this card belongs in the current board view.
 */
function matches(task) {
  if (view.agent && task.agent !== view.agent) return false;
  if (view.filter === "open" && task.state === "done") return false;
  if (!["open", "all"].includes(view.filter) && task.state !== view.filter) return false;
  return JSON.stringify([task.id, task.agent, task.effective_summary, task.evidence, task.claims]).toLowerCase().includes(view.search);
}

/** @param {Event} event - Agent button activation. @returns {void} Updates the filtered view. */
function chooseAgent(event) {
  view.agent = event.currentTarget.dataset.agent || "";
  render();
}

/** Render agent summaries from checkpoints. @returns {void} Updates roster controls. */
function renderAgents() {
  const agents = new Map();
  for (const task of view.snapshot.tasks) {
    const info = agents.get(task.agent) || { open: 0, done: 0, latest: task.updated_at };
    if (task.state === "done") info.done += 1; else info.open += 1;
    if (task.updated_at > info.latest) info.latest = task.updated_at;
    agents.set(task.agent, info);
  }
  byId("agent-count").textContent = agents.size;
  byId("agents").replaceChildren();
  byId("all-agents").classList.toggle("selected", !view.agent);
  byId("all-agents").setAttribute("aria-pressed", String(!view.agent));
  for (const name of [...agents.keys()].sort()) {
    const info = agents.get(name);
    const button = element("button", `agent-button ${view.agent === name ? "selected" : ""}`);
    button.type = "button";
    button.dataset.agent = name;
    button.setAttribute("aria-pressed", String(view.agent === name));
    const text = element("span", "agent-label", name);
    text.append(element("small", "", info.open ? `${info.open} open · ${ago(info.latest)}` : `Last card ${ago(info.latest)}`));
    button.append(element("span", "avatar", initials(name)), text, element("span", "agent-amount", info.open));
    button.addEventListener("click", chooseAgent);
    byId("agents").append(button);
  }
}

/** @param {Event} event - Task card activation. @returns {void} Opens the full task dialog. */
function openDetails(event) {
  view.selected = event.currentTarget.dataset.task;
  renderDetails();
  byId("details").showModal();
}

/** Render evidence and ownership previews. @returns {void} Updates the filtered card board. */
function renderCards() {
  if (!view.snapshot) return;
  const cards = byId("cards");
  cards.replaceChildren();
  let visible = 0;
  for (const task of view.snapshot.tasks) {
    if (!matches(task)) continue;
    visible += 1;
    const card = element("button", "task-card");
    card.type = "button";
    card.dataset.task = task.id;
    card.setAttribute("aria-label", `Open ${task.agent} task: ${task.effective_summary}`);
    card.addEventListener("click", openDetails);
    const top = element("span", "card-top");
    const agent = element("span", "card-agent");
    agent.append(element("span", "avatar mini-avatar", initials(task.agent)), element("span", "", task.agent));
    top.append(agent, badge(task));
    card.append(top, element("span", "card-title", task.effective_summary));
    const paths = element("span", "card-paths");
    for (const claim of task.claims.slice(0, 2)) paths.append(element("span", "path-tag", claim.path + (claim.kind === "directory" ? "/" : "")));
    if (task.claims.length > 2) paths.append(element("span", "path-tag", `+${task.claims.length - 2} more`));
    if (!task.claims.length) paths.append(element("span", "", "No claimed paths"));
    card.append(paths);
    const footer = element("span", "card-footer");
    const time = element("span", "", `${task.id} · ${ago(task.updated_at)}`);
    time.title = fullTime(task.updated_at);
    footer.append(time, element("span", task.evidence ? "evidence-mark" : "", task.evidence ? "Evidence published ↗" : "View details ↗"));
    card.append(footer);
    cards.append(card);
  }
  byId("card-count").textContent = visible;
  if (!visible) cards.append(empty(view.snapshot.tasks.length ? "No cards match this view" : "Your workspace is ready",
    view.snapshot.tasks.length ? "Try another status, agent, or search." : "Cards appear here when an agent registers its first task."));
}

/**
 * Build activity only from stored records; previous checkpoints are not reconstructed.
 * @returns {Array<Object>} Latest available timestamped published events.
 */
function activityEvents() {
  const events = [];
  for (const task of view.snapshot.tasks) {
    if (view.agent && task.agent !== view.agent) continue;
    events.push({ time: task.started_at, who: task.agent, action: "opened a card", text: task.id });
    if (task.updated_at !== task.started_at || task.state !== "active") events.push({ time: task.updated_at, who: task.agent,
      action: task.state === "done" ? "completed a card" : task.state === "paused" ? "published a paused card" : "updated a card",
      text: task.state === "done" ? task.summary : task.effective_summary });
    for (const correction of task.corrections) events.push({ time: correction.created_at, who: "Correction",
      action: `published for ${task.id}`, text: correction.revised_summary });
  }
  for (const message of view.snapshot.messages) {
    if (view.agent && message.from_agent !== view.agent && message.to_agent !== view.agent) continue;
    events.push({ time: message.created_at, who: message.from_agent, action: `messaged ${message.to_agent}`, text: message.body });
  }
  events.sort(compareEvents);
  return events.slice(0, 12);
}

/** @param {Object} a - First event. @param {Object} b - Second event. @returns {number} Newest-first order. */
function compareEvents(a, b) { return b.time.localeCompare(a.time); }

/** Render activity without consuming inboxes. @returns {void} Updates activity and messages. */
function renderActivity() {
  byId("activity").replaceChildren();
  const events = activityEvents();
  for (const event of events) {
    const item = element("li");
    item.append(element("strong", "", `${event.who} ${event.action}`), element("p", "", event.text.slice(0, 120)));
    const time = element("time", "", ago(event.time));
    time.dateTime = event.time;
    time.title = fullTime(event.time);
    item.append(time);
    byId("activity").append(item);
  }
  if (!events.length) byId("activity").append(element("li", "muted", "No published activity yet."));
  byId("message-note").textContent = "Shows card creation, the latest card checkpoint, corrections, and recent messages. Earlier checkpoint changes are not retained by the register.";
  byId("messages").replaceChildren();
  let count = 0;
  for (const message of view.snapshot.messages) {
    if (view.agent && message.from_agent !== view.agent && message.to_agent !== view.agent) continue;
    count += 1;
    const box = element("article", "message");
    const top = element("div", "section-heading");
    top.append(element("strong", "", `${message.from_agent} → ${message.to_agent}`),
      element("span", `badge ${message.read_at ? "done" : "active"}`, message.read_at ? "Acknowledged" : "Unread"));
    box.append(top, element("p", "", message.body), element("small", "", `${fullTime(message.created_at)}${message.to_task ? " · Task " + message.to_task : " · Agent-wide"}`));
    byId("messages").append(box);
  }
  byId("unread-count").textContent = `${view.snapshot.unread_count} unread`;
  if (!count) byId("messages").append(empty("No coordination messages", "Queued notes between agents will appear here."));
  if (view.snapshot.message_count > view.snapshot.messages.length) byId("messages").append(element("p", "muted", "Showing the latest 200 stored messages. Unread count covers the whole register."));
}

/** @param {string} heading - Section title. @param {string} text - Record text. @returns {HTMLElement} Detail section. */
function detailSection(heading, text) {
  const section = element("section", "detail-section");
  section.append(element("h3", "", heading), element("p", "", text));
  return section;
}

/** Render a task's corrections and ownership. @returns {void} Updates the details dialog. */
function renderDetails() {
  let task = null;
  for (const candidate of view.snapshot.tasks) if (candidate.id === view.selected) task = candidate;
  if (!task) return;
  const content = byId("detail-content");
  content.replaceChildren();
  const title = element("h2", "detail-title", task.effective_summary);
  title.id = "details-title";
  content.append(badge(task), title, element("p", "detail-meta", `${task.agent} · ${task.id}\nOpened ${fullTime(task.started_at)}\nLast checkpoint ${fullTime(task.updated_at)}`));
  content.append(detailSection("Verification evidence", task.evidence || "No verification evidence published."));
  const claims = detailSection(task.state === "done" ? "Released paths · retained history" : "Owned paths · retained while paused or stale", "");
  const list = element("ul");
  for (const claim of task.claims) list.append(element("li", "", `${claim.path}${claim.kind === "directory" ? "/" : ""} · ${claim.kind}`));
  if (!task.claims.length) list.append(element("li", "", "No paths claimed"));
  claims.append(list);
  content.append(claims);
  if (task.session_ref) content.append(detailSection("Session reference", task.session_ref));
  if (task.corrections.length) {
    content.append(detailSection("Original completion summary", task.summary));
    for (const correction of task.corrections) content.append(detailSection(`Correction · ${fullTime(correction.created_at)} · author task ${correction.from_task}`, correction.revised_summary));
  }
}

/** Refresh metrics and retain keyboard focus. @returns {void} Updates all snapshot views. */
function render() {
  if (!view.snapshot) return;
  const focusedTask = document.activeElement?.dataset.task;
  const focusedAgent = document.activeElement?.dataset.agent;
  const path = view.snapshot.repo;
  byId("project-name").textContent = path.split(/[\\/]/).filter(Boolean).pop() || path;
  byId("project-path").textContent = path;
  let working = 0, claims = 0, attention = 0, done = 0;
  for (const task of view.snapshot.tasks) {
    if (task.state === "done") done += 1;
    else {
      claims += task.claims.length;
      if (task.state === "active") working += 1;
      if (task.state === "paused" || task.stale) attention += 1;
    }
  }
  byId("working-count").textContent = working;
  byId("claims-count").textContent = claims;
  byId("attention-count").textContent = attention;
  byId("done-count").textContent = done;
  byId("sample-time").textContent = `Updated ${fullTime(view.snapshot.sampled_at)} · Refreshes every 3s`;
  renderAgents(); renderCards(); renderActivity(); renderDetails();
  if (focusedTask || focusedAgent) {
    for (const button of document.querySelectorAll("[data-task], [data-agent]")) {
      if ((focusedTask && button.dataset.task === focusedTask) || (focusedAgent && button.dataset.agent === focusedAgent)) {
        button.focus({ preventScroll: true });
        break;
      }
    }
  }
}

/**
 * Poll once without overlapping requests, retaining and labeling the last good view on errors.
 * @returns {Promise<void>} Resolves after the snapshot or connection state is rendered.
 */
async function refresh() {
  if (view.busy) return;
  view.busy = true;
  byId("refresh").disabled = true;
  try {
    const response = await fetch("/api/snapshot", { cache: "no-store", signal: AbortSignal.timeout(12000) });
    if (!response.ok) throw new Error("Register is unavailable");
    view.snapshot = await response.json();
    byId("error-banner").hidden = true;
    byId("connection-dot").className = "connection-dot online";
    byId("connection-label").textContent = view.snapshot.store_exists ? "Connected · 3s refresh" : "Waiting for first card";
    render();
  } catch (error) {
    byId("connection-dot").className = "connection-dot offline";
    byId("connection-label").textContent = "Disconnected";
    byId("error-banner").textContent = "Cannot refresh the register. Keep the monitor terminal open and check its selected project and store. " + (view.snapshot ? "The last successful snapshot is shown below." : "Retrying automatically.");
    byId("error-banner").hidden = false;
  } finally {
    view.busy = false;
    byId("refresh").disabled = false;
  }
}

/** @param {Event} event - Status filter activation. @returns {void} Updates status and cards. */
function chooseFilter(event) {
  view.filter = event.currentTarget.dataset.filter;
  for (const button of document.querySelectorAll("[data-filter]")) {
    const selected = button.dataset.filter === view.filter;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  }
  renderCards();
}

/** @param {Event} event - Search input change. @returns {void} Filters the visible cards. */
function searchCards(event) { view.search = event.target.value.toLowerCase().trim(); if (view.snapshot) renderCards(); }

/** Close the task dialog. @returns {void} Restores focus to its surviving card when possible. */
function closeDetails() {
  const taskId = view.selected;
  byId("details").close();
  view.selected = null;
  for (const button of document.querySelectorAll("[data-task]")) {
    if (button.dataset.task === taskId) { button.focus(); break; }
  }
}

/** Toggle browser theme with optional storage. @returns {void} Updates the color theme. */
function toggleTheme() {
  const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem("accord-theme", theme); } catch (error) { /* Theme still works without storage. */ }
}

/** Initialize controls and polling. @returns {void} Starts read-only refresh every three seconds. */
function start() {
  let theme = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  try { theme = localStorage.getItem("accord-theme") || theme; } catch (error) { /* Use OS preference. */ }
  document.documentElement.dataset.theme = theme;
  byId("theme").addEventListener("click", toggleTheme);
  byId("refresh").addEventListener("click", refresh);
  byId("all-agents").addEventListener("click", chooseAgent);
  byId("search").addEventListener("input", searchCards);
  byId("close-details").addEventListener("click", closeDetails);
  for (const button of document.querySelectorAll("[data-filter]")) button.addEventListener("click", chooseFilter);
  refresh();
  setInterval(refresh, 3000);
}

start();
