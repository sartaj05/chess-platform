(function () {
  function appendChatMessage(actor, message, createdAt) {
    const log = document.getElementById('roomChatLog');
    if (!log) return;
    const row = document.createElement('div');
    row.className = 'small mb-2';
    const strong = document.createElement('strong');
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
      chatMessage: '',
      state: { participants: [] },
      init() {
        const stateTag = document.getElementById('room-state-data');
        if (!stateTag) return;
        this.state = JSON.parse(stateTag.textContent);
        this.connectSocket();
      },
      websocketUrl() {
        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        return `${scheme}://${window.location.host}/ws/rooms/${this.state.code}/`;
      },
      connectSocket() {
        this.socket = new WebSocket(this.websocketUrl());
        this.socket.onopen = () => { this.connected = true; };
        this.socket.onclose = () => {
          this.connected = false;
          window.setTimeout(() => this.connectSocket(), 2000);
        };
        this.socket.onerror = () => { this.connected = false; };
        this.socket.onmessage = (event) => {
          const payload = JSON.parse(event.data);
          if (payload.type === 'connection.accepted' && payload.room) {
            this.state = payload.room;
          }
          if (payload.type === 'room.state' && payload.room) {
            this.state = payload.room;
          }
          if (payload.type === 'room.chat' && payload.chat) {
            appendChatMessage(payload.chat.actor, payload.chat.message, payload.chat.created_at);
          }
        };
      },
      send(payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false;
        this.socket.send(JSON.stringify(payload));
        return true;
      },
      sendChat() {
        const message = this.chatMessage.trim();
        if (!message) return;
        if (this.send({ type: 'room.chat', message })) {
          this.chatMessage = '';
        }
      },
      setReady(ready) {
        this.send({ type: 'room.ready', ready });
      }
    };
  };

  document.addEventListener('click', function (event) {
    const button = event.target.closest('[data-copy-target]');
    if (!button) return;
    const input = document.querySelector(button.getAttribute('data-copy-target'));
    if (!input) return;
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(input.value).then(function () {
      const oldText = button.textContent;
      button.textContent = 'Copied';
      window.setTimeout(function () { button.textContent = oldText; }, 1200);
    });
  });
})();
