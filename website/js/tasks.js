(() => {
    "use strict";

    const TASKS = [
        {
            id: "youtube",
            name: "WATCH YOUTUBE",
            description: "Open the required YouTube video",
            url: "https://youtu.be/b2VcUiifl_A?si=W78IyU_XgiX9n87F"
        },
        {
            id: "youtube_like",
            name: "LIKE YOUTUBE VIDEO",
            description: "Open the YouTube video",
            url: "https://youtu.be/b2VcUiifl_A?si=W78IyU_XgiX9n87F"
        },
        {
            id: "whatsapp",
            name: "WHATSAPP",
            description: "Open WhatsApp",
            url: "https://wa.me/"
        },
        {
            id: "telegram",
            name: "TELEGRAM",
            description: "Open Telegram",
            url: "https://t.me/"
        }
    ];

    const taskList = document.getElementById("taskList");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    const getKey = document.getElementById("getKey");
    const taskStatus = document.getElementById("taskStatus");

    function setStatus(text, success) {
        if (!taskStatus) return;

        taskStatus.textContent = text;
        taskStatus.classList.toggle("success", Boolean(success));
    }

    function openTask(task) {
        if (!task || !task.url) return;

        window.location.href = task.url;
    }

    function renderTasks() {
        if (!taskList) return;

        taskList.innerHTML = "";

        TASKS.forEach((task, index) => {
            const row = document.createElement("div");
            row.className = "task";

            const icon = document.createElement("div");
            icon.className = "icon";
            icon.textContent = String(index + 1);

            const info = document.createElement("div");
            info.className = "info";

            const name = document.createElement("div");
            name.className = "name";
            name.textContent = task.name;

            const description = document.createElement("div");
            description.className = "desc";
            description.textContent = task.description;

            info.appendChild(name);
            info.appendChild(description);

            const action = document.createElement("div");
            action.className = "action";

            const button = document.createElement("button");
            button.type = "button";
            button.className = "btn";
            button.textContent = "OPEN";

            button.addEventListener("click", function () {
                openTask(task);
            });

            action.appendChild(button);

            row.appendChild(icon);
            row.appendChild(info);
            row.appendChild(action);

            taskList.appendChild(row);
        });

        if (progressBar) {
            progressBar.style.width = "100%";
        }

        if (progressText) {
            progressText.textContent =
                TASKS.length + " / " + TASKS.length;
        }

        if (getKey) {
            getKey.disabled = false;
        }

        setStatus("TASKS READY", true);
    }

    if (getKey) {
        getKey.disabled = false;

        getKey.addEventListener("click", function () {
            window.location.href = "get-key.html";
        });
    }

    renderTasks();
})();
