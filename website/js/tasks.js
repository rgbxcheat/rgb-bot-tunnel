(function () {

"use strict";

let API_BASE = "";

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

let busy = false;

const taskList = document.getElementById("taskList");
const getKeyButton = document.getElementById("getKey");
const taskStatus = document.getElementById("taskStatus");


function setStatus(text, success) {

    taskStatus.textContent = text;

    if (success) {
        taskStatus.classList.add("success");
    } else {
        taskStatus.classList.remove("success");
    }
}


function renderTasks() {

    taskList.innerHTML = "";

    TASKS.forEach(function (task) {

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
            button.textContent = "OPEN";

            button.addEventListener("click", function () {
                startTask(task, button);
            });

            action.appendChild(button);
        }

        row.appendChild(icon);
        row.appendChild(info);
        row.appendChild(action);

        taskList.appendChild(row);
    });


    const allCompleted =
        completed.size === TASKS.length;

    getKeyButton.disabled =
        !allCompleted || busy;


    if (allCompleted) {

        setStatus(
            "ALL TASKS COMPLETED — GET YOUR CODE",
            true
        );

    } else {

        setStatus(
            completed.size +
            " / " +
            TASKS.length +
            " TASKS COMPLETED",
            false
        );
    }
}


async function startTask(task, button) {

    if (busy || completed.has(task.id)) {
        return;
    }

    const url = TASK_LINKS[task.id];

    if (!url) {
        setStatus("TASK LINK NOT CONFIGURED", false);
        return;
    }

    busy = true;

    button.disabled = true;

    /*
     * Open the requested task.
     */
    window.open(
        url,
        "_blank",
        "noopener,noreferrer"
    );


    /*
     * Five-second verification timer.
     */
    for (let seconds = 5; seconds > 0; seconds--) {

        button.textContent =
            "WAIT " + seconds + "s";

        setStatus(
            "Complete " +
            task.name +
            " — waiting " +
            seconds +
            " seconds...",
            false
        );

        await new Promise(function (resolve) {
            setTimeout(resolve, 1000);
        });
    }


    button.textContent = "VERIFYING...";

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

            throw new Error(
                data.error || "TASK_ERROR"
            );
        }


        completed.add(task.id);

        busy = false;

        renderTasks();


        if (completed.size === TASKS.length) {

            setStatus(
                "ALL TASKS COMPLETED — GET YOUR CODE",
                true
            );

        } else {

            const next =
                TASKS.find(function (item) {
                    return !completed.has(item.id);
                });

            if (next) {

                setStatus(
                    "TASK COMPLETED — NEXT: " +
                    next.name,
                    true
                );
            }
        }

    } catch (error) {

        console.error(
            "TASK ERROR:",
            error
        );

        busy = false;

        button.disabled = false;
        button.textContent = "OPEN";

        setStatus(
            "VERIFICATION FAILED — PLEASE TRY AGAIN",
            false
        );
    }
}


async function startTaskSession() {

    const response = await fetch(
        API_BASE + "/api/tasks/start",
        {
            method: "POST",
            credentials: "include"
        }
    );

    const data =
        await response.json();


    if (!response.ok || !data.success) {

        throw new Error(
            data.error ||
            "SESSION_START_FAILED"
        );
    }
}


async function loadServer() {

    try {

        setStatus(
            "CONNECTING TO RGB BOT V1 SERVER...",
            false
        );


        const response = await fetch(
            "current_tunnel.json?ts=" +
            Date.now(),
            {
                cache: "no-store"
            }
        );


        if (!response.ok) {

            throw new Error(
                "CURRENT_TUNNEL_NOT_FOUND"
            );
        }


        const config =
            await response.json();


        if (!config.base_url) {

            throw new Error(
                "SERVER_URL_NOT_FOUND"
            );
        }


        API_BASE =
            config.base_url.replace(
                /\/+$/,
                ""
            );


        await startTaskSession();


        renderTasks();


        setStatus(
            "0 / 3 TASKS COMPLETED",
            false
        );


    } catch (error) {

        console.error(
            "SERVER INIT ERROR:",
            error
        );


        getKeyButton.disabled = true;


        setStatus(
            "SERVER CONNECTION FAILED — PLEASE REFRESH",
            false
        );
    }
}


getKeyButton.addEventListener(
    "click",
    async function () {

        if (
            busy ||
            completed.size !== TASKS.length
        ) {
            return;
        }


        getKeyButton.disabled = true;

        setStatus(
            "VERIFYING ALL TASKS...",
            false
        );


        try {

            const response = await fetch(
                API_BASE + "/api/tasks/status",
                {
                    credentials: "include",
                    cache: "no-store"
                }
            );


            const data =
                await response.json();


            if (
                !response.ok ||
                !data.success
            ) {

                throw new Error(
                    data.error ||
                    "STATUS_ERROR"
                );
            }


            if (
                data.tasks &&
                data.tasks.youtube &&
                data.tasks.whatsapp &&
                data.tasks.telegram
            ) {

                window.location.href =
                    "get-key.html";

            } else {

                throw new Error(
                    "TASKS_NOT_COMPLETED"
                );
            }


        } catch (error) {

            console.error(
                "GET KEY ERROR:",
                error
            );


            getKeyButton.disabled = false;


            setStatus(
                "SERVER VERIFICATION FAILED — PLEASE TRY AGAIN",
                false
            );
        }
    }
);


/*
 * Initial page.
 */
renderTasks();

loadServer();

})();
