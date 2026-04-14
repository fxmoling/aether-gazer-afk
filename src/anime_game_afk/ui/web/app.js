/**
 * AetherGazer AFK — Frontend logic
 *
 * Communicates with Python backend via pywebview.api.*
 * Backend pushes updates via window.appendLog() and window.updateTaskStatus()
 */

// ─── State ───

let pipelines = [];
let selectedPipelineId = null;
let currentLogFilter = "ALL";
let statusInterval = null;

// ─── Initialization ───

window.addEventListener("pywebviewready", async () => {
    await loadPipelines();
    await loadRecentLogs();
    startStatusPolling();
});

async function loadPipelines() {
    try {
        pipelines = await pywebview.api.get_pipelines();
    } catch (e) {
        pipelines = [];
    }

    const select = document.getElementById("pipeline-select");
    select.innerHTML = "";
    pipelines.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} — ${p.description}`;
        select.appendChild(opt);
    });

    if (pipelines.length > 0) {
        selectedPipelineId = pipelines[0].id;
        select.value = selectedPipelineId;
        renderTasks(pipelines[0]);
    }
}

async function loadRecentLogs() {
    try {
        const logs = await pywebview.api.get_recent_logs(200);
        logs.forEach((entry) => addLogEntry(entry));
    } catch (e) {
        // Ignore on startup
    }
}

// ─── Page switching ───

function switchPage(pageName) {
    document.querySelectorAll(".page").forEach((p) => (p.style.display = "none"));
    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));

    const page = document.getElementById("page-" + pageName);
    if (page) {
        page.style.display = "flex";
        page.classList.add("active");
    }

    const nav = document.querySelector(`.nav-item[data-page="${pageName}"]`);
    if (nav) nav.classList.add("active");
}

// ─── Pipeline selection ───

function onSelectPipeline(pipelineId) {
    selectedPipelineId = pipelineId;
    const pipeline = pipelines.find((p) => p.id === pipelineId);
    if (pipeline) renderTasks(pipeline);
}

// ─── Task rendering ───

function renderTasks(pipeline) {
    const container = document.getElementById("task-items");
    container.innerHTML = "";

    pipeline.tasks.forEach((task) => {
        const div = document.createElement("div");
        div.className = "task-item";
        div.id = `task-${task.id}`;
        if (task.status && task.status !== "pending") {
            div.classList.add(task.status);
        }

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = task.enabled;
        checkbox.style.accentColor = "#4fc3f7";
        checkbox.style.width = "16px";
        checkbox.style.height = "16px";
        checkbox.style.cursor = "pointer";
        checkbox.onchange = () => onToggleTask(task.id, checkbox.checked);

        const nameSpan = document.createElement("span");
        nameSpan.className = "task-name" + (task.safe === false ? " unsafe" : "");
        nameSpan.textContent = task.name;

        const badge = document.createElement("span");
        badge.className = `task-badge badge-${task.status || "pending"}`;
        badge.id = `badge-${task.id}`;
        badge.textContent = statusText(task.status || "pending");

        div.appendChild(checkbox);
        div.appendChild(nameSpan);
        div.appendChild(badge);
        container.appendChild(div);
    });

    updateSelectAll(pipeline);
}

function statusText(status) {
    const map = {
        pending: "● 等待",
        running: "▶ 运行中",
        success: "✔ 完成",
        failed: "✘ 失败",
        skipped: "— 跳过",
    };
    return map[status] || status;
}

function updateSelectAll(pipeline) {
    const all = document.getElementById("select-all");
    if (!pipeline) return;
    const enabledCount = pipeline.tasks.filter((t) => t.enabled).length;
    all.checked = enabledCount === pipeline.tasks.length;
    all.indeterminate = enabledCount > 0 && enabledCount < pipeline.tasks.length;
}

// ─── Task toggle ───

async function onToggleTask(taskId, enabled) {
    if (!selectedPipelineId) return;
    await pywebview.api.set_task_enabled(selectedPipelineId, taskId, enabled);

    // Update local state
    const pipeline = pipelines.find((p) => p.id === selectedPipelineId);
    if (pipeline) {
        const task = pipeline.tasks.find((t) => t.id === taskId);
        if (task) task.enabled = enabled;
        updateSelectAll(pipeline);
    }
}

async function onToggleAll(checked) {
    if (!selectedPipelineId) return;
    await pywebview.api.set_all_enabled(selectedPipelineId, checked);

    // Update local state
    const pipeline = pipelines.find((p) => p.id === selectedPipelineId);
    if (pipeline) {
        pipeline.tasks.forEach((t) => (t.enabled = checked));
        renderTasks(pipeline);
    }
}

// ─── Connection ───

async function onConnect() {
    const btn = document.getElementById("btn-connect");
    btn.disabled = true;
    btn.textContent = "连接中...";

    const result = await pywebview.api.connect();
    if (result.ok) {
        setConnected(true, result.resolution);
    } else {
        setConnected(false);
        alert(result.error || "连接失败");
    }
    btn.disabled = false;
    btn.textContent = "连接";
}

async function onDisconnect() {
    await pywebview.api.disconnect();
    setConnected(false);
}

function setConnected(connected, resolution) {
    const dot = document.getElementById("conn-dot");
    const text = document.getElementById("conn-text");
    const btnConnect = document.getElementById("btn-connect");
    const btnDisconnect = document.getElementById("btn-disconnect");
    const btnStart = document.getElementById("btn-start");

    if (connected) {
        dot.className = "dot connected";
        text.textContent = `深空之眼 — 已连接 (${resolution || "?"})`;
        btnConnect.disabled = true;
        btnDisconnect.disabled = false;
        btnStart.disabled = false;
    } else {
        dot.className = "dot disconnected";
        text.textContent = "未连接";
        btnConnect.disabled = false;
        btnDisconnect.disabled = true;
        btnStart.disabled = true;
    }
}

// ─── Execution ───

async function onStartRun() {
    if (!selectedPipelineId) return;
    const result = await pywebview.api.start_run(selectedPipelineId);
    if (result.ok) {
        setRunning(true);
    } else {
        alert(result.error || "启动失败");
    }
}

async function onStopRun() {
    const result = await pywebview.api.stop_run();
    // Immediately update UI — don't wait for polling
    if (result.ok) {
        document.getElementById("btn-stop").disabled = true;
    }
}

function setRunning(running) {
    const btnStart = document.getElementById("btn-start");
    const btnStop = document.getElementById("btn-stop");

    btnStart.disabled = running;
    btnStop.disabled = !running;
}

// ─── Status polling ───

function startStatusPolling() {
    statusInterval = setInterval(async () => {
        try {
            const status = await pywebview.api.get_status();
            updateRunStatus(status);
        } catch (e) {
            // Window may be closing
        }
    }, 1000);
}

function updateRunStatus(status) {
    const el = document.getElementById("run-status");
    const btnStart = document.getElementById("btn-start");
    const btnStop = document.getElementById("btn-stop");

    if (status.running) {
        const min = Math.floor(status.elapsed_s / 60);
        const sec = Math.floor(status.elapsed_s % 60);
        const timeStr = `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
        el.textContent = `${status.completed}/${status.total} 完成 · 运行中 ${timeStr}`;
        // Ensure stop button is always enabled while running
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        if (status.completed > 0 || status.total > 0) {
            el.textContent = `${status.completed}/${status.total} 完成`;
        } else {
            el.textContent = "";
        }
        // Only re-enable start if connected
        if (status.connected) {
            btnStart.disabled = false;
        }
        btnStop.disabled = true;
    }

    // Update connection state
    const dot = document.getElementById("conn-dot");
    if (status.connected && dot.classList.contains("disconnected")) {
        setConnected(true);
    }
}

// ─── Python → JS push functions ───

/**
 * Called by Python: window.evaluate_js('window.appendLog({...})')
 */
window.appendLog = function (entry) {
    addLogEntry(entry);
};

/**
 * Called by Python: window.evaluate_js('window.updateTaskStatus("mail","success")')
 */
window.updateTaskStatus = function (taskId, status) {
    // Update local state
    const pipeline = pipelines.find((p) => p.id === selectedPipelineId);
    if (pipeline) {
        const task = pipeline.tasks.find((t) => t.id === taskId);
        if (task) task.status = status;
    }

    // Update DOM
    const item = document.getElementById(`task-${taskId}`);
    if (item) {
        item.className = "task-item";
        if (status !== "pending") item.classList.add(status);
    }

    const badge = document.getElementById(`badge-${taskId}`);
    if (badge) {
        badge.className = `task-badge badge-${status}`;
        badge.textContent = statusText(status);
    }
};

/**
 * Called by Python when pipeline run completes
 */
window.onRunComplete = function () {
    setRunning(false);
    // Refresh pipeline data to sync all task statuses
    loadPipelines();
};

// ─── Log management ───

function addLogEntry(entry) {
    const output = document.getElementById("log-output");
    const div = document.createElement("div");
    div.className = `log-entry log-${entry.level}`;
    div.dataset.level = entry.level;
    div.textContent = `[${entry.time}] ${entry.level.padEnd(7)} ${entry.message}`;

    // Apply current filter
    if (currentLogFilter !== "ALL" && entry.level !== currentLogFilter) {
        div.style.display = "none";
    }

    output.appendChild(div);

    // Limit DOM entries to 1000
    while (output.children.length > 1000) {
        output.removeChild(output.firstChild);
    }

    // Auto-scroll
    if (document.getElementById("auto-scroll").checked) {
        output.scrollTop = output.scrollHeight;
    }
}

function filterLogs(level) {
    currentLogFilter = level;
    const entries = document.querySelectorAll("#log-output .log-entry");
    entries.forEach((el) => {
        if (level === "ALL" || el.dataset.level === level) {
            el.style.display = "";
        } else {
            el.style.display = "none";
        }
    });
}

function clearLogs() {
    document.getElementById("log-output").innerHTML = "";
}
