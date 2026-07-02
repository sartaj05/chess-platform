(function () {
  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  window.gameClient = function gameClient() {
    return {
      socket: null,
      connected: false,
      state: { board: [], legal_moves: [], white: {}, black: {}, captured: { white: [], black: [] }, moves: [] },
      selectedSquare: '',
      draggedSquare: '',
      statusMessage: '',
      boardOrientation: 'white-orientation',
      clockTimer: null,
      init() {
        const stateTag = document.getElementById('game-state-data');
        if (!stateTag) return;
        this.state = JSON.parse(stateTag.textContent);
        this.boardOrientation = this.state.viewer && this.state.viewer.color === 'black' ? 'black-orientation' : 'white-orientation';
        this.connectSocket();
        this.clockTimer = window.setInterval(() => this.tickClock(), 1000);
      },
      websocketUrl() {
        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        return `${scheme}://${window.location.host}/ws/games/${this.state.id}/`;
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
          if (payload.type === 'connection.accepted' && payload.game) this.replaceState(payload.game);
          if (payload.type === 'game.state' && payload.game) this.replaceState(payload.game);
          if (payload.type === 'error') this.showStatus(payload.message || 'Game error');
        };
      },
      replaceState(nextState) {
        const viewer = this.state.viewer || nextState.viewer;
        this.state = nextState;
        if (viewer && !this.state.viewer) this.state.viewer = viewer;
        this.selectedSquare = '';
        this.draggedSquare = '';
      },
      boardRows() {
        if (this.boardOrientation === 'black-orientation') {
          return clone(this.state.board).reverse().map(row => row.reverse());
        }
        return this.state.board;
      },
      squareClass(square) {
        const light = (square.file + square.rank) % 2 === 1;
        const classes = [light ? 'light' : 'dark'];
        if (this.selectedSquare === square.square) classes.push('selected');
        if (this.isLegalTarget(square.square)) classes.push('legal');
        if (this.state.last_move_uci && (this.state.last_move_uci.slice(0, 2) === square.square || this.state.last_move_uci.slice(2, 4) === square.square)) classes.push('last');
        return classes.join(' ');
      },
      isLegalTarget(squareName) {
        if (!this.selectedSquare) return false;
        return this.state.legal_moves.some(move => move.from === this.selectedSquare && move.to === squareName);
      },
      clickSquare(square) {
        if (square.piece && this.isOwnPiece(square)) {
          this.selectedSquare = square.square;
          return;
        }
        if (this.selectedSquare) {
          this.tryMove(this.selectedSquare, square.square);
        }
      },
      isOwnPiece(square) {
        const viewerColor = this.state.viewer ? this.state.viewer.color : null;
        if (!viewerColor && this.state.white.name === 'White' && this.state.black.name === 'Black') return true;
        return square.color === viewerColor && this.state.turn === viewerColor;
      },
      dragStart(event, square) {
        if (!square.piece || !this.isOwnPiece(square)) {
          event.preventDefault();
          return;
        }
        this.draggedSquare = square.square;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', square.square);
      },
      dropSquare(event, square) {
        const from = event.dataTransfer.getData('text/plain') || this.draggedSquare;
        if (from) this.tryMove(from, square.square);
      },
      tryMove(from, to) {
        let candidates = this.state.legal_moves.filter(move => move.from === from && move.to === to);
        if (candidates.length === 0) {
          this.showStatus('Illegal move.');
          this.selectedSquare = '';
          return;
        }
        let move = candidates[0].uci;
        const promotionCandidate = candidates.find(item => item.uci.length === 5 && item.uci.endsWith('q')) || candidates.find(item => item.uci.length === 5);
        if (promotionCandidate) move = promotionCandidate.uci;
        this.send({ type: 'game.move', uci: move, client_lag_ms: 0 });
        this.selectedSquare = '';
      },
      send(payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
          this.showStatus('Realtime connection is not ready.');
          return false;
        }
        this.socket.send(JSON.stringify(payload));
        return true;
      },
      sendAction(type) {
        this.send({ type });
      },
      formatClock(ms) {
        const safe = Math.max(Number(ms || 0), 0);
        const totalSeconds = Math.ceil(safe / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        return `${minutes}:${String(seconds).padStart(2, '0')}`;
      },
      tickClock() {
        if (this.state.status !== 'active') return;
        if (this.state.turn === 'white') this.state.white.time_ms = Math.max(Number(this.state.white.time_ms || 0) - 1000, 0);
        if (this.state.turn === 'black') this.state.black.time_ms = Math.max(Number(this.state.black.time_ms || 0) - 1000, 0);
      },
      showStatus(message) {
        this.statusMessage = message;
        window.setTimeout(() => { this.statusMessage = ''; }, 3000);
      }
    };
  };
})();
