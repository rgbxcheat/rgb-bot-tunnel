(function () {

"use strict";

let API_BASE = "";
let currentTaskIndex = 0;
let busy = false;
let countdownTimer = null;
let remainingSeconds = 0;

const TASK_LINKS = {
    youtube: "https://www.youtube.com/@RGBXCHEAT",
    whatsapp: "https://chat.whatsapp.com/BmMZFU6DidFK7Uaa6RmgWV?s=cl&p=a&mlu=4&ilr=4",
    telegram: "https://t.me/rgbxcheat"
};

const TASKS = [
    {
        id: "youtube",
        name: "YouTube",
        desc: "Subscribe to RGBXCHEAT",
        icon: "YT"
    },
    {
        id: "whatsapp",
        name: "WhatsApp",
        desc: "Join the RGB community",
        icon: "WA"
    },
    {
        id: "telegram",
        name: "Telegram",
        desc: "Join the RGB channel",
        icon: "TG"
    }
];

const completed = new Set();

const taskList = document.getElementById("taskList");
const getKeyButton = document.getElementById("getKey");
const taskStatus = document.getElementById("taskStatus");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");

function setStatus(text, success) {
    taskStatus.textContent = text;

    if (success) {
        taskStatus.classList.add("success");
    } else {
        taskStatus.classList.remove("success");
    }
}

function updateProgress() {
    const count = completed.size;
    const percent = (count / TASKS.length) * 100;

    progressBar.style.width = percent + "%";
    progressText.textContent = count + " / " + TASKS.length;
}

function stopCountdown() {
    if (countdownTimer !== null) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
}

function syncState(state) {
    if (!state) return;

    completed.clear();

    if (state.tasks) {
        TASKS.forEach(function (task) {
            if (state.tasks[task.id] === true) {
                completed.add(task.id);
            }
        });
    }

    if (typeof state.step === "number") {
        currentTaskIndex = Math.max(
            0,
            Math.min(state.step, TASKS.length)
        );
    } else {
        currentTaskIndex = completed.size;
    }

    if (completed.size >= TASKS.length) {
        currentTaskIndex = TASKS.length;
    }

    if (state.waiting === true && currentTaskIndex < TASKS.length) {
        remainingSeconds = Number(state.waiting_seconds || 0);
        busy = true;
    } else {
        remainingSeconds = 0;
    }
}

function getCurrentButton() {
    if (currentTaskIndex >= TASKS.length) {
        return null;
    }

    return taskList.querySelector(
        '.btn[data-task="' + TASKS[currentTaskIndex].id + '"]'
    );
}

function renderTasks() {

    taskList.innerHTML = "";

    TASKS.forEach(function (task, index) {

        const row = document.createElement("div");
        row.className = "task";

        const icon = document.createElement("div");
        icon.className = "icon";
        icon.textContent = task.icon;

        const info = document.createElement("div");
        info.className = "info";

        const name = document.createElement("div");
        name.className = "name";
        name.textContent = task.name;

        const desc = document.createElement("div");
        desc.className = "desc";
        desc.textContent = task.desc;

        info.appendChild(name);
        info.appendChild(desc);

        const action = document.createElement("div");
        action.className = "action";

        if (completed.has(task.id)) {

            const done = document.createElement("span");
            done.className = "done";
            done.textContent = "DONE";

            action.appendChild(done);

        } else {

            const button = document.createElement("button");

            button.className = "btn";
            button.type = "button";
            button.dataset.task = task.id;

            if (index < currentTaskIndex) {

                button.disabled = true;
                button.textContent = "DONE";

            } else if (index > currentTaskIndex) {

                button.disabled = true;
                button.textContent = "LOCKED";

            } else if (busy) {

                button.disabled = true;

                if (remainingSeconds > 0) {
                    button.textContent = remainingSeconds + "s";
                } else {
                    button.disabled = false;
                    button.textContent = "FINISH";
                }

            } else {

                button.disabled = false;
                button.textContent = "OPEN";

                button.addEventListener("click", function () {
                    startTask(index);
                });
            }

            action.appendChild(button);
        }

        row.appendChild(icon);
        row.appendChild(info);
        row.appendChild(action);

        taskList.appendChild(row);
    });

    updateProgress();

    getKeyButton.disabled =
        completed.size !== TASKS.length || busy;

    if (completed.size === TASKS.length) {

        setStatus(
            "ALL TASKS COMPLETED — GET YOUR CODE",
            true
        );

    } else if (busy && remainingSeconds > 0) {

        const current = TASKS[currentTaskIndex];

        if (current) {
            setStatus(
                "WAIT " + remainingSeconds + " SECONDS...",
                false
            );
        }

    } else if (busy) {

        const current = TASKS[currentTaskIndex];

        if (current) {
            setStatus(
                "TIME COMPLETE — PRESS FINISH",
                true
            );
        }

    } else {

        const current = TASKS[currentTaskIndex];

        if (current) {
            setStatus(
                "NEXT TASK: " + current.name,
                false
            );
        }
    }
}

async function loadTunnel() {

    const response = await fetch(
        "current_tunnel.json?t=" + Date.now(),
        {
            cache: "no-store"
        }
    );

    if (!response.ok) {
        throw new Error("TUNNEL_CONFIG_ERROR");
    }

    const data = await response.json();

    if (!data.base_url) {
        throw new Error("SERVER_URL_MISSING");
    }

    API_BASE = data.base_url.replace(/\/+$/, "");
}

async function api(path, options) {

    const response = await fetch(
        API_BASE + path,
        Object.assign(
            {
                credentials: "include",
                cache: "no-store"
            },
            options || {}
        )
    );

    let data = {};

    try {
        data = await response.json();
    } catch (e) {
        throw new Error("INVALID_SERVER_RESPONSE");
    }

    if (!response.ok || data.success === false) {

        const error = new Error(
            data.error || "SERVER_ERROR"
        );

        error.data = data;
        error.status = response.status;

        throw error;
    }

    return data;
}

async function startSession() {

    const data = await api(
        "/api/tasks/start",
        {
            method: "POST"
        }
    );

    syncState(data);

    renderTasks();

    if (
        data.waiting === true &&
        currentTaskIndex < TASKS.length
    ) {
        startCountdown(
            currentTaskIndex,
            Number(data.waiting_seconds || 0)
        );
    }
}

async function refreshState() {

    const data = await api(
        "/api/tasks/status"
    );

    syncState(data);

    renderTasks();

    if (
        data.waiting === true &&
        currentTaskIndex < TASKS.length
    ) {
        startCountdown(
            currentTaskIndex,
            Number(data.waiting_seconds || 0)
        );
    }
}

async function openTask(task) {

    return await api(
        "/api/tasks/open",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                task: task.id
            })
        }
    );
}

async function completeTask(task) {

    return await api(
        "/api/tasks/complete",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                task: task.id
            })
        }
    );
}

function startCountdown(index, seconds) {

    stopCountdown();

    if (index !== currentTaskIndex) {
        return;
    }

    remainingSeconds = Math.max(
        0,
        Number(seconds || 0)
    );

    busy = true;

    renderTasks();

    if (remainingSeconds <= 0) {
        showFinishButton(index);
        return;
    }

    countdownTimer = setInterval(
        async function () {

            remainingSeconds--;

            if (remainingSeconds > 0) {

                renderTasks();

                return;
            }

            stopCountdown();

            remainingSeconds = 0;

            renderTasks();

            setStatus(
                "TIME COMPLETE — PRESS FINISH",
                true
            );

        },
        1000
    );
}

function showFinishButton(index) {

    if (index !== currentTaskIndex) {
        return;
    }

    remainingSeconds = 0;
    busy = true;

    renderTasks();

    const button = getCurrentButton();

    if (button) {

        button.disabled = false;
        button.textContent = "FINISH";

        button.onclick = function () {
            finishTask(index);
        };
    }

    setStatus(
        "TIME COMPLETE — PRESS FINISH",
        true
    );
}

async function startTask(index) {

    if (busy) {
        return;
    }

    if (index !== currentTaskIndex) {
        return;
    }

    const task = TASKS[index];

    if (!task || completed.has(task.id)) {
        return;
    }

    const url = TASK_LINKS[task.id];

    if (!url) {
        setStatus(
            "TASK LINK NOT CONFIGURED",
            false
        );
        return;
    }

    /*
     * Open the tab immediately from the user click.
     * This avoids browser popup blocking after await.
     */
    const popup = window.open(
        "about:blank",
        "_blank"
    );

    busy = true;
    remainingSeconds = 5;

    renderTasks();

    try {

        const data = await openTask(task);

        if (popup && !popup.closed) {
            popup.location.href = url;
        } else {
            window.open(url, "_blank");
        }

        remainingSeconds = Number(
            data.waiting_seconds !== undefined
                ? data.waiting_seconds
                : 5
        );

        startCountdown(
            index,
            remainingSeconds
        );

    } catch (error) {

        if (popup && !popup.closed) {
            popup.close();
        }

        busy = false;
        remainingSeconds = 0;

        stopCountdown();

        await refreshState();

        setStatus(
            error.message || "TASK ERROR",
            false
        );
    }
}

async function finishTask(index) {

    if (index !== currentTaskIndex) {
        return;
    }

    if (remainingSeconds > 0) {
        return;
    }

    const task = TASKS[index];

    if (!task) {
        return;
    }

    busy = true;
    stopCountdown();

    renderTasks();

    setStatus(
        "VERIFYING " + task.name + "...",
        false
    );

    try {

        const data = await completeTask(task);

        syncState(data);

        busy = false;
        remainingSeconds = 0;

        renderTasks();

        if (completed.size < TASKS.length) {

            const next = TASKS[currentTaskIndex];

            if (next) {
                setStatus(
                    "FINISHED — NEXT TASK: " + next.name,
                    true
                );
            }

        } else {

            setStatus(
                "ALL TASKS COMPLETED — GET YOUR CODE",
                true
            );
        }

    } catch (error) {

        busy = false;
        remainingSeconds = 0;

        stopCountdown();

        await refreshState();

        setStatus(
            error.message || "TASK ERROR",
            false
        );
    }
}

getKeyButton.addEventListener(
    "click",
    async function () {

        if (completed.size !== TASKS.length) {
            return;
        }

        getKeyButton.disabled = true;

        setStatus(
            "GENERATING YOUR CODE...",
            false
        );

        try {

            const data = await api(
                "/api/get-key",
                {
                    method: "POST"
                }
            );

            if (data.success && data.key) {

                window.location.href =
                    "get-key.html?key=" +
                    encodeURIComponent(data.key);

            } else {

                throw new Error(
                    data.error || "GET_KEY_ERROR"
                );
            }

        } catch (error) {

            getKeyButton.disabled = false;

            setStatus(
                error.message || "GET KEY ERROR",
                false
            );
        }
    }
);

async function init() {

    try {

        setStatus(
            "CONNECTING TO SERVER...",
            false
        );

        await loadTunnel();
        await startSession();

    } catch (error) {

        console.error(error);

        stopCountdown();

        busy = false;
        remainingSeconds = 0;

        setStatus(
            "SERVER CONNECTION ERROR",
            false
        );
    }
}

init();

})();
