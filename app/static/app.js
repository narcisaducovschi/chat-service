const AUTH_URL = "http://localhost:8000";
const CHAT_WS_URL = "ws://localhost:8001";


function saveToken(token) {
    sessionStorage.setItem("access_token", token);
}

function getToken() {
    return sessionStorage.getItem("access_token");
}

function saveEmail(email) {
    sessionStorage.setItem("user_email", email);
}

function getEmail() {
    return sessionStorage.getItem("user_email");
}

function saveRoom(room) {
    sessionStorage.setItem("room", room);
}

function getRoom() {
    return sessionStorage.getItem("room");
}


const loginForm = document.getElementById("login-form");
const roomForm = document.getElementById("room-form");

if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("login-email").value;
        const password = document.getElementById("login-password").value;
        const messageEl = document.getElementById("login-message");

        try {
            const response = await fetch(`${AUTH_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                messageEl.textContent = data.detail || "Error al iniciar sesión";
                messageEl.className = "message error";
                return;
            }

            saveToken(data.access_token);
            saveEmail(email);

            document.getElementById("login-card").style.display = "none";
            document.getElementById("room-card").style.display = "block";
        } catch {
            messageEl.textContent = "No se pudo conectar con el servidor de auth";
            messageEl.className = "message error";
        }
    });
}

if (roomForm) {
    roomForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const roomName = document.getElementById("room-name").value.trim();
        if (!roomName) return;

        saveRoom(roomName);
        window.location.href = "/static/room.html";
    });
}

const messagesEl = document.getElementById("messages");
const userListEl = document.getElementById("user-list");
const typingIndicatorEl = document.getElementById("typing-indicator");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const leaveBtn = document.getElementById("leave-btn");
const roomTitleEl = document.getElementById("room-title");

if (messagesEl) {
    const token = getToken();
    const room = getRoom();
    const myEmail = getEmail();

    if (!token || !room) {
        window.location.href = "/static/index.html";
    } else {
        roomTitleEl.textContent = `Sala: ${room}`;

        const ws = new WebSocket(`${CHAT_WS_URL}/ws/${room}?token=${token}`);

        let typingTimeout = null;

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "message") {
                addMessage(data.user_email, data.content);
            } else if (data.type === "system") {
                addSystemMessage(data.content);
            } else if (data.type === "user_list") {
                updateUserList(data.users);
            } else if (data.type === "typing") {
                showTyping(data.user_email);
            }
        };

        ws.onclose = () => {
            addSystemMessage("Conexión cerrada");
        };

        function addMessage(userEmail, content) {
            const div = document.createElement("div");
            const isOwn = userEmail === myEmail;
            div.className = isOwn ? "msg own" : "msg";
            div.innerHTML = `${isOwn ? "" : `<div class="sender">${userEmail}</div>`}${escapeHtml(content)}`;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function addSystemMessage(content) {
            const div = document.createElement("div");
            div.className = "msg system";
            div.textContent = content;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function updateUserList(users) {
            userListEl.innerHTML = users
                .map((u) => `<div class="user-item">${escapeHtml(u)}</div>`)
                .join("");
        }

        function showTyping(userEmail) {
            typingIndicatorEl.textContent = `${userEmail} está escribiendo...`;
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                typingIndicatorEl.textContent = "";
            }, 2000);
        }

        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }

        function sendMessage() {
            const content = messageInput.value.trim();
            if (!content) return;

            ws.send(JSON.stringify({ type: "message", content }));
            messageInput.value = "";
        }

        sendBtn.addEventListener("click", sendMessage);
        messageInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                sendMessage();
            } else {
                ws.send(JSON.stringify({ type: "typing" }));
            }
        });

        leaveBtn.addEventListener("click", () => {
            ws.close();
            sessionStorage.removeItem("room");
            window.location.href = "/static/index.html";
        });
    }
}