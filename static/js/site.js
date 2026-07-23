(function () {
  "use strict";

  /* ------------------------------------------------------------------
   * Toast notifications
   * Usage: Toast.show("Message", "success" | "error" | "info")
   * ------------------------------------------------------------------ */
  const Toast = {
    stack: null,

    getStack() {
      if (!this.stack) {
        this.stack = document.getElementById("toastStack");
      }
      return this.stack;
    },

    show(message, type = "info", duration = 3200) {
      const stack = this.getStack();
      if (!stack || !message) return;

      const item = document.createElement("div");
      item.className = `toast-item toast-${type}`;
      item.setAttribute("role", "status");

      const text = document.createElement("span");
      text.textContent = message;
      item.appendChild(text);

      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "toast-close";
      closeBtn.setAttribute("aria-label", "Dismiss notification");
      closeBtn.textContent = "\u00d7";
      closeBtn.addEventListener("click", () => remove());
      item.appendChild(closeBtn);

      stack.appendChild(item);

      let removed = false;
      const remove = () => {
        if (removed) return;
        removed = true;
        item.classList.add("leaving");
        window.setTimeout(() => item.remove(), 200);
      };

      window.setTimeout(remove, duration);
      return remove;
    }
  };

  window.Toast = Toast;

  /* ------------------------------------------------------------------
   * Dashboard WebSocket ping test
   * ------------------------------------------------------------------ */
  const pingBtn = document.getElementById("pingSocketBtn");
  const pingOut = document.getElementById("pingSocketOutput");

  if (pingBtn && pingOut) {
    let activeSocket = null;

    pingBtn.addEventListener("click", function () {
      if (activeSocket && activeSocket.readyState === WebSocket.OPEN) {
        return;
      }

      pingBtn.disabled = true;
      pingOut.textContent = "connecting...";

      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      let socket;

      try {
        socket = new WebSocket(`${scheme}://${window.location.host}/ws/ping/`);
      } catch (error) {
        pingOut.textContent = "WebSocket unavailable";
        pingBtn.disabled = false;
        return;
      }

      activeSocket = socket;

      const timeout = window.setTimeout(() => {
        pingOut.textContent = "Timed out waiting for response";
        pingBtn.disabled = false;
        socket.close();
      }, 8000);

      socket.addEventListener("open", () => {
        socket.send(JSON.stringify({ type: "ping" }));
      });

      socket.addEventListener("message", (event) => {
        window.clearTimeout(timeout);
        pingOut.textContent = event.data;
        pingBtn.disabled = false;
        socket.close();
      });

      socket.addEventListener("error", () => {
        window.clearTimeout(timeout);
        pingOut.textContent = "WebSocket error";
        pingBtn.disabled = false;
      });

      socket.addEventListener("close", () => {
        window.clearTimeout(timeout);
        pingBtn.disabled = false;
        activeSocket = null;
      });
    });
  }

  /* ------------------------------------------------------------------
   * Bootstrap alert auto-dismiss (server-rendered Django messages)
   * ------------------------------------------------------------------ */
  document.querySelectorAll(".alert-dismissible").forEach((alertEl) => {
    window.setTimeout(() => {
      const closeBtn = alertEl.querySelector(".btn-close");
      if (closeBtn) closeBtn.click();
    }, 8000);
  });
})();