(function () {
  function clone(value) {
    return JSON.parse(JSON.stringify(value || []));
  }

  window.gameClient = function gameClient() {
    return {
      socket: null,
      connected: false,

      state: {
        id: '',
        status: '',
        result: '',
        turn: '',
        fen: '',
        board: [],
        legal_moves: [],
        white: { name: 'White', time_ms: 0 },
        black: { name: 'Black', time_ms: 0 },
        captured: { white: [], black: [] },
        moves: [],
        viewer: null,
        draw_offer_by: '',
        last_move_uci: '',
        last_move_san: ''
      },

      selectedSquare: '',
      draggedSquare: '',
      statusMessage: '',
      boardOrientation: 'white-orientation',
      clockTimer: null,

      init() {
        const stateTag = document.getElementById('game-state-data');

        if (!stateTag) {
          this.showStatus('Game state not found.');
          return;
        }

        try {
          this.state = JSON.parse(stateTag.textContent);
        } catch (error) {
          this.showStatus('Unable to read game state.');
          return;
        }

        this.boardOrientation =
          this.state.viewer && this.state.viewer.color === 'black'
            ? 'black-orientation'
            : 'white-orientation';

        this.connectSocket();

        if (this.clockTimer) {
          window.clearInterval(this.clockTimer);
        }

        this.clockTimer = window.setInterval(() => this.tickClock(), 1000);
      },

      websocketUrl() {
        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        return `${scheme}://${window.location.host}/ws/games/${this.state.id}/`;
      },

      connectSocket() {
        if (!this.state.id) {
          return;
        }

        try {
          this.socket = new WebSocket(this.websocketUrl());
        } catch (error) {
          this.connected = false;
          this.showStatus('Realtime connection could not start.');
          return;
        }

        this.socket.onopen = () => {
          this.connected = true;
        };

        this.socket.onclose = () => {
          this.connected = false;
          window.setTimeout(() => this.connectSocket(), 2000);
        };

        this.socket.onerror = () => {
          this.connected = false;
        };

        this.socket.onmessage = (event) => {
          let payload = null;

          try {
            payload = JSON.parse(event.data);
          } catch (error) {
            this.showStatus('Invalid realtime message.');
            return;
          }

          if (payload.type === 'connection.accepted' && payload.game) {
            this.replaceState(payload.game);
          }

          if (payload.type === 'game.state' && payload.game) {
            this.replaceState(payload.game);
          }

          if (payload.type === 'error') {
            this.showStatus(payload.message || 'Game error');
          }
        };
      },

      replaceState(nextState) {
        const viewer = this.state.viewer || nextState.viewer;

        this.state = nextState;

        if (viewer && !this.state.viewer) {
          this.state.viewer = viewer;
        }

        this.selectedSquare = '';
        this.draggedSquare = '';
      },

      boardRows() {
        const board = clone(this.state.board);

        if (!board.length) {
          return [];
        }

        if (this.boardOrientation === 'black-orientation') {
          return board.reverse().map((row) => row.reverse());
        }

        return board;
      },

      squareClass(square) {
        const light = (square.file + square.rank) % 2 === 1;
        const classes = [light ? 'light' : 'dark'];

        if (this.selectedSquare === square.square) {
          classes.push('selected');
        }

        if (this.isLegalTarget(square.square)) {
          classes.push('legal');
        }

        if (
          this.state.last_move_uci &&
          (
            this.state.last_move_uci.slice(0, 2) === square.square ||
            this.state.last_move_uci.slice(2, 4) === square.square
          )
        ) {
          classes.push('last');
        }

        return classes.join(' ');
      },

      isLegalTarget(squareName) {
        if (!this.selectedSquare) {
          return false;
        }

        return (this.state.legal_moves || []).some((move) => {
          return move.from === this.selectedSquare && move.to === squareName;
        });
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

        if (!viewerColor && this.state.white.name === 'White' && this.state.black.name === 'Black') {
          return true;
        }

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

        if (from) {
          this.tryMove(from, square.square);
        }
      },

      tryMove(from, to) {
        const candidates = (this.state.legal_moves || []).filter((move) => {
          return move.from === from && move.to === to;
        });

        if (candidates.length === 0) {
          this.showStatus('Illegal move.');
          this.selectedSquare = '';
          return;
        }

        let move = candidates[0].uci;

        const promotionCandidate =
          candidates.find((item) => item.uci.length === 5 && item.uci.endsWith('q')) ||
          candidates.find((item) => item.uci.length === 5);

        if (promotionCandidate) {
          move = promotionCandidate.uci;
        }

        this.send({
          type: 'game.move',
          uci: move,
          client_lag_ms: 0
        });

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

        if (hours > 0) {
          return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }

        return `${minutes}:${String(seconds).padStart(2, '0')}`;
      },

      tickClock() {
        if (this.state.status !== 'active') {
          return;
        }

        if (this.state.turn === 'white') {
          this.state.white.time_ms = Math.max(Number(this.state.white.time_ms || 0) - 1000, 0);
        }

        if (this.state.turn === 'black') {
          this.state.black.time_ms = Math.max(Number(this.state.black.time_ms || 0) - 1000, 0);
        }
      },

      showStatus(message) {
        this.statusMessage = message;

        window.setTimeout(() => {
          this.statusMessage = '';
        }, 3000);
      }
    };
  };
})();