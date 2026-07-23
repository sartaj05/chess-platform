(function () {
  "use strict";

  const MAX_RECONNECT_DELAY_MS = 15000;
  const BASE_RECONNECT_DELAY_MS = 1000;

  function notify(message, type) {
    if (window.Toast) {
      window.Toast.show(message, type);
    }
  }

  function appendChatMessage(actor, message, createdAt) {
    const log = document.getElementById("roomChatLog");
    if (!log) return;

    const emptyState = log.querySelector(".empty-state");
    if (emptyState) emptyState.remove();

    const row = document.createElement("div");
    row.className = "small mb-2";

    const strong = document.createElement("strong");
    strong.textContent = `${actor}: `;
    row.appendChild(strong);
    row.appendChild(document.createTextNode(message));

    if (createdAt) {
      row.title = createdAt;
    }

    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  window.roomClient = function roomClient() {
    return {
      socket: null,
      connected: false,
      connecting: false,
      chatMessage: "",
      state: { participants: [] },
      reconnectAttempts: 0,
      reconnectTimer: null,

      init() {
        const stateTag = document.getElementById("room-state-data");
        if (!stateTag) return;

        try {
          this.state = JSON.parse(stateTag.textContent);
        } catch (error) {
          notify("Unable to read room state.", "error");
          return;
        }

        this.connectSocket();

        window.addEventListener("beforeunload", () => {
          if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
          if (this.socket) this.socket.close();
        });
      },

      websocketUrl() {
        const scheme = window.location.protocol === "https:" ? "wss" : "ws";
        return `${scheme}://${window.location.host}/ws/rooms/${this.state.code}/`;
      },

      connectSocket() {
        if (this.connecting) return;
        this.connecting = true;

        let socket;
        try {
          socket = new WebSocket(this.websocketUrl());
        } catch (error) {
          this.connecting = false;
          this.scheduleReconnect();
          return;
        }

        this.socket = socket;

        socket.onopen = () => {
          this.connected = true;
          this.connecting = false;
          this.reconnectAttempts = 0;
        };

        socket.onclose = () => {
          const wasConnected = this.connected;
          this.connected = false;
          this.connecting = false;
          if (wasConnected) notify("Realtime connection lost. Reconnecting…", "error");
          this.scheduleReconnect();
        };

        socket.onerror = () => {
          this.connected = false;
        };

        socket.onmessage = (event) => {
          let payload;

          try {
            payload = JSON.parse(event.data);
          } catch (error) {
            notify("Received an invalid realtime message.", "error");
            return;
          }

          if (payload.type === "connection.accepted" && payload.room) {
            this.state = payload.room;
          }

          if (payload.type === "room.state" && payload.room) {
            this.state = payload.room;
          }

          if (payload.type === "room.chat" && payload.chat) {
            appendChatMessage(payload.chat.actor, payload.chat.message, payload.chat.created_at);
          }

          if (payload.type === "error") {
            notify(payload.message || "Room error", "error");
          }
        };
      },

      scheduleReconnect() {
        if (this.reconnectTimer) return;

        const delay = Math.min(
          BASE_RECONNECT_DELAY_MS * Math.pow(2, this.reconnectAttempts),
          MAX_RECONNECT_DELAY_MS
        );
        this.reconnectAttempts += 1;

        this.reconnectTimer = window.setTimeout(() => {
          this.reconnectTimer = null;
          this.connectSocket();
        }, delay);
      },

      send(payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
          notify("Realtime connection is not ready yet.", "error");
          return false;
        }

        this.socket.send(JSON.stringify(payload));
        return true;
      },

      sendChat() {
        const message = this.chatMessage.trim();
        if (!message) return;

        if (this.send({ type: "room.chat", message })) {
          this.chatMessage = "";
        }
      },

      setReady(ready) {
        this.send({ type: "room.ready", ready });
      }
    };
  };

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-copy-target]");
    if (!button) return;

    const input = document.querySelector(button.getAttribute("data-copy-target"));
    if (!input) return;

    input.select();
    input.setSelectionRange(0, 99999);

    navigator.clipboard
      .writeText(input.value)
      .then(function () {
        const oldText = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(function () {
          button.textContent = oldText;
        }, 1200);
      })
      .catch(function () {
        notify("Could not copy to clipboard.", "error");
      });
  });
})();