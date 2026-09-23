let API_BASE = "";

const TASK_LINKS = {
    youtube: "https://www.youtube.com/@RGBXCHEAT",
    whatsapp: "https://chat.whatsapp.com/BmMZFU6DidFK7Uaa6RmgWV?s=cl&p=a&mlu=4&ilr=4",
    telegram: "https://t.me/rgbxcheat"
};

const tasks = [
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

const list = document.getElementById("taskList");
const getKey = document.getElementById("getKey");
const taskStatus = document.getElementById("taskStatus");

function render() {
    list.innerHTML = "";

    tasks.forEach(task => {
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
            button.textContent = "OPEN";

            button.addEventListener("click", () => {
                startTask(task, button);
            });

            action.appendChild(button);
        }

        row.appendChild(icon);
        row.appendChild(info);
        row.appendChild(action);

        list.appendChild(row);
    });

    const allDone = completed.size === tasks.length;

    getKey.disabled = !allDone;

    if (allDone) {
        taskStatus.textContent =
            "ALL TASKS COMPLETED — GET YOUR CODE";
        taskStatus.classList.add("success");
    } else {
        taskStatus.textContent =
            completed.size + " / " + tasks.length + " TASKS COMPLETED";
        taskStatus.classList.remove("success");
    }
}

async function startTask(task, button) {
    const url = TASK_LINKS[task.id];

    if (!url) {
        taskStatus.textContent = "TASK LINK NOT CONFIGURED";
        return;
    }

    window.open(url, "_blank", "noopener,noreferrer");

    button.disabled = true;

    let remaining = 5;
    button.textContent = "WAIT " + remaining + "s";

    const timer = setInterval(() => {
        remaining--;

        if (remaining > 0) {
            button.textContent = "WAIT " + remaining + "s";
        }
    }, 1000);

    await new Promise(resolve => {
        setTimeout(resolve, 5000);
    });

    clearInterval(timer);

    try {
        const response = await fetch(
            API_BASE + "/api/tasks/complete",
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    task: task.id
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "TASK_ERROR");
        }

        completed.add(task.id);
        render();

    } catch (error) {
        console.error(error);

        button.disabled = false;
        button.textContent = "OPEN";

        taskStatus.textContent =
            "VERIFICATION FAILED — PLEASE TRY AGAIN";
    }
}

getKey.addEventListener("click", async () => {
    if (completed.size !== tasks.length) {
        return;
    }

    try {
        const response = await fetch(
            API_BASE + "/api/tasks/status",
            {
                credentials: "include"
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "SESSION_ERROR");
        }

        if (
            data.tasks &&
            data.tasks.youtube &&
            data.tasks.whatsapp &&
            data.tasks.telegram
        ) {
            window.location.href = "get-key.html";
        } else {
            throw new Error("TASKS_NOT_COMPLETED");
        }

    } catch (error) {
        console.error(error);

        taskStatus.textContent =
            "SERVER VERIFICATION FAILED — PLEASE TRY AGAIN";
    }
});

async function startTaskSession() {
    try {
        const response = await fetch(
            API_BASE + "/api/tasks/start",
            {
                method: "POST",
                credentials: "include"
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "SESSION_START_FAILED");
        }

        console.log("RGB task session started");

    } catch (error) {
        console.error(error);

        taskStatus.textContent =
            "SERVER CONNECTION FAILED — PLEASE REFRESH";
    }
}

async function loadApiBase() {
    try {
        const response = await fetch(
            "current_tunnel.json?ts=" + Date.now(),
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error("REGISTRY_ERROR");
        }

        const config = await response.json();

        if (!config.base_url) {
            throw new Error("NO_TUNNEL_URL");
        }

        API_BASE = config.base_url.replace(/\/+$/, "");

        render();

        await startTaskSession();

    } catch (error) {
        console.error(error);

        taskStatus.textContent =
            "SERVER CONNECTION FAILED — PLEASE TRY AGAIN";

        getKey.disabled = true;
    }
}

render();
loadApiBase();
