(function () {
  "use strict";

  const MAX_RECONNECT_DELAY_MS = 15000;
  const BASE_RECONNECT_DELAY_MS = 1000;

  const PROMOTION_PIECES = [
    { piece: "q", symbol: "\u265b", label: "Queen" },
    { piece: "r", symbol: "\u265c", label: "Rook" },
    { piece: "b", symbol: "\u265d", label: "Bishop" },
    { piece: "n", symbol: "\u265e", label: "Knight" }
  ];

  function clone(value) {
    return JSON.parse(JSON.stringify(value || []));
  }

  function notify(message, type) {
    if (window.Toast) {
      window.Toast.show(message, type);
    }
  }

  window.gameClient = function gameClient() {
    return {
      socket: null,
      connected: false,
      connecting: false,
      reconnectAttempts: 0,
      reconnectTimer: null,

      state: {
        id: "",
        mode: "",
        source: "",
        status: "",
        result: "",
        turn: "",
        fen: "",
        board: [],
        legal_moves: [],
        white: { name: "White", time_ms: 0 },
        black: { name: "Black", time_ms: 0 },
        captured: { white: [], black: [] },
        moves: [],
        viewer: null,
        draw_offer_by: "",
        last_move_uci: "",
        last_move_san: ""
      },

      selectedSquare: "",
      draggedSquare: "",
      statusMessage: "",
      boardOrientation: "white-orientation",
      clockTimer: null,
      lastTickAt: 0,
      promotionChoice: null,
      boardTheme: localStorage.getItem("chess-board-theme") || "classic",
      soundPack: localStorage.getItem("chess-sound-pack") || "wood",
      resultModalOpen: false,
      resultPresented: false,

      init() {
        const stateTag = document.getElementById("game-state-data");

        if (!stateTag) {
          this.showStatus("Game state not found.");
          return;
        }

        try {
          this.state = JSON.parse(stateTag.textContent);
        } catch (error) {
          this.showStatus("Unable to read game state.");
          return;
        }

        this.boardOrientation =
          (this.state.mode === "local_ai" && this.state.player_color === "black") ||
          (this.state.viewer && this.state.viewer.color === "black")
            ? "black-orientation"
            : "white-orientation";

        this.connectSocket();

        if (this.clockTimer) {
          window.clearInterval(this.clockTimer);
        }

        this.lastTickAt = Date.now();
        this.clockTimer = window.setInterval(() => this.tickClock(), 1000);

        if (this.state.status === "finished") {
          window.setTimeout(() => this.presentResult(), 250);
        }

        window.addEventListener("beforeunload", () => {
          if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
          if (this.socket) this.socket.close();
        });
      },

      isSameBrowserGame() {
        return this.state.mode === "same_pc" || this.state.source === "fen_import";
      },

      isBotGame() {
        return this.state.mode === "local_ai";
      },

      websocketUrl() {
        const scheme = window.location.protocol === "https:" ? "wss" : "ws";
        return `${scheme}://${window.location.host}/ws/games/${this.state.id}/`;
      },

      connectSocket() {
        if (!this.state.id || this.connecting) {
          return;
        }

        this.connecting = true;
        let socket;

        try {
          socket = new WebSocket(this.websocketUrl());
        } catch (error) {
          this.connecting = false;
          this.connected = false;
          this.showStatus("Realtime connection could not start.");
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
          let payload = null;

          try {
            payload = JSON.parse(event.data);
          } catch (error) {
            this.showStatus("Invalid realtime message.");
            return;
          }

          if (payload.type === "connection.accepted" && payload.game) {
            this.replaceState(payload.game);
          }

          if (payload.type === "game.state" && payload.game) {
            this.replaceState(payload.game);
          }

          if (payload.type === "error") {
            this.showStatus(payload.message || "Game error");
            notify(payload.message || "Game error", "error");
          }
        };
      },

      scheduleReconnect() {
        if (this.reconnectTimer || !this.state.id) return;

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

      replaceState(nextState) {
        const oldViewer = this.state.viewer;
        const previousMove = this.state.last_move_uci;
        const previousStatus = this.state.status;

        this.state = nextState;

        if (this.isSameBrowserGame()) {
          this.state.viewer = {
            color: this.state.turn,
            name: this.state.turn === "white" ? this.state.white.name : this.state.black.name,
            can_move: true
          };
        } else if (oldViewer && !this.state.viewer) {
          this.state.viewer = oldViewer;
        }

        this.selectedSquare = "";
        this.draggedSquare = "";
        if (nextState.last_move_uci && nextState.last_move_uci !== previousMove) this.playSound("move");
        if (previousStatus !== "finished" && nextState.status === "finished") {
          this.playSound("finish");
          this.presentResult();
        }
      },

      resultOutcome() {
        if (this.state.result === "1/2-1/2") return "draw";
        const winner = this.state.winner_color || (this.state.result === "1-0" ? "white" : this.state.result === "0-1" ? "black" : "");
        const player = this.isBotGame() ? this.state.player_color : (this.state.viewer ? this.state.viewer.color : "");
        if (!player) return winner ? "complete" : "draw";
        return winner === player ? "win" : "loss";
      },

      resultTitle() {
        const outcome = this.resultOutcome();
        if (outcome === "win") return "Brilliant. You won!";
        if (outcome === "loss") return "Tough game";
        if (outcome === "draw") return "Game drawn";
        return `${this.state.winner_color === "white" ? "White" : "Black"} wins`;
      },

      resultMessage() {
        const outcome = this.resultOutcome();
        if (outcome === "win") return this.state.level_unlocked ? `Level ${this.state.level_unlocked} unlocked. Your next challenge is ready.` : "A strong finish. Your result has been saved.";
        if (outcome === "loss") return "Every game teaches something. Review the position or start a fresh challenge.";
        if (outcome === "draw") return "An even battle. One more game could settle it.";
        return "The game is complete. Start another when you are ready.";
      },

      presentResult() {
        if (this.resultPresented || this.state.status !== "finished") return;
        this.resultPresented = true;
        this.resultModalOpen = true;
      },

      closeResult() { this.resultModalOpen = false; },

      boardRows() {
        const board = clone(this.state.board);

        if (!board.length) {
          return [];
        }

        if (this.boardOrientation === "black-orientation") {
          return board.reverse().map((row) => row.reverse());
        }

        return board;
      },

      squareClass(square) {
        const light = (square.file + square.rank) % 2 === 1;
        const classes = [light ? "light" : "dark"];

        if (this.selectedSquare === square.square) {
          classes.push("selected");
        }

        if (this.isLegalTarget(square.square)) {
          classes.push("legal");
        }

        if (
          this.state.last_move_uci &&
          (this.state.last_move_uci.slice(0, 2) === square.square ||
            this.state.last_move_uci.slice(2, 4) === square.square)
        ) {
          classes.push("last");
        }

        return classes.join(" ");
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
        if (this.isBotGame()) {
          return square.color === this.state.player_color && this.state.turn === this.state.player_color;
        }
        if (this.isSameBrowserGame()) {
          return square.color === this.state.turn;
        }

        const viewerColor = this.state.viewer ? this.state.viewer.color : null;

        if (!viewerColor && this.state.white.name === "White" && this.state.black.name === "Black") {
          return square.color === this.state.turn;
        }

        return square.color === viewerColor && this.state.turn === viewerColor;
      },

      dragStart(event, square) {
        if (!square.piece || !this.isOwnPiece(square)) {
          event.preventDefault();
          return;
        }

        this.draggedSquare = square.square;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", square.square);
      },

      dropSquare(event, square) {
        const from = event.dataTransfer.getData("text/plain") || this.draggedSquare;

        if (from) {
          this.tryMove(from, square.square);
        }
      },

      tryMove(from, to) {
        const candidates = (this.state.legal_moves || []).filter((move) => {
          return move.from === from && move.to === to;
        });

        if (candidates.length === 0) {
          this.showStatus("Illegal move.");
          this.selectedSquare = "";
          return;
        }

        const promotionCandidates = candidates.filter((item) => item.uci.length === 5);

        if (promotionCandidates.length > 1) {
          this.promotionChoice = { from, to, candidates: promotionCandidates };
          return;
        }

        this.dispatchMove(candidates[0].uci);
      },

      promotionOptions() {
        if (!this.promotionChoice) return [];

        const available = new Set(this.promotionChoice.candidates.map((c) => c.uci.slice(4)));
        return PROMOTION_PIECES.filter((option) => available.has(option.piece));
      },

      confirmPromotion(piece) {
        if (!this.promotionChoice) return;

        const match = this.promotionChoice.candidates.find((c) => c.uci.endsWith(piece));
        this.promotionChoice = null;

        if (match) {
          this.dispatchMove(match.uci);
        }
      },

      cancelPromotion() {
        this.promotionChoice = null;
        this.selectedSquare = "";
      },

      dispatchMove(uci) {
        this.send({
          type: "game.move",
          uci,
          client_lag_ms: 0
        });

        this.selectedSquare = "";
      },

      send(payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
          this.showStatus("Realtime connection is not ready.");
          return false;
        }

        this.socket.send(JSON.stringify(payload));
        return true;
      },

      sendAction(type) {
        this.send({ type });
      },

      saveExperience() {
        localStorage.setItem("chess-board-theme", this.boardTheme);
        localStorage.setItem("chess-sound-pack", this.soundPack);
        this.playSound("move");
      },

      playSound(kind) {
        if (this.soundPack === "silent" || !window.AudioContext) return;
        const context = new AudioContext();
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        oscillator.type = this.soundPack === "soft" ? "sine" : "triangle";
        oscillator.frequency.value = kind === "finish" ? 660 : (this.soundPack === "soft" ? 310 : 220);
        gain.gain.setValueAtTime(0.055, context.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + (kind === "finish" ? 0.32 : 0.09));
        oscillator.connect(gain); gain.connect(context.destination); oscillator.start(); oscillator.stop(context.currentTime + (kind === "finish" ? 0.34 : 0.1));
      },

      async shareGame() {
        const result = `${this.state.white.name} vs ${this.state.black.name} — ${this.state.result}`;
        const canvas = document.createElement("canvas"); canvas.width = 1200; canvas.height = 630;
        const draw = canvas.getContext("2d");
        draw.fillStyle = "#173b2a"; draw.fillRect(0, 0, 1200, 630);
        draw.fillStyle = "#b7d7a9"; draw.font = "700 28px system-ui"; draw.fillText("CHESS PLATFORM · GAME RESULT", 72, 90);
        draw.fillStyle = "#ffffff"; draw.font = "700 62px system-ui"; draw.fillText(this.state.white.name, 72, 230); draw.fillText(this.state.black.name, 72, 330);
        draw.fillStyle = "#b7d7a9"; draw.font = "500 34px system-ui"; draw.fillText("versus", 72, 275);
        draw.fillStyle = "#ffffff"; draw.font = "800 96px Georgia"; draw.textAlign = "right"; draw.fillText(this.state.result, 1128, 290);
        draw.fillStyle = "#a9c7a9"; draw.font = "500 25px system-ui"; draw.fillText("Review and replay this game", 1128, 530); draw.textAlign = "left";
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
        const file = blob ? new File([blob], "chess-result.png", { type: "image/png" }) : null;
        const data = { title: "Chess Platform game", text: result, url: window.location.href, files: file ? [file] : [] };
        try {
          if (navigator.share && (!file || !navigator.canShare || navigator.canShare({ files: [file] }))) await navigator.share(data);
          else { if (blob) { const link = document.createElement("a"); link.download = "chess-result.png"; link.href = URL.createObjectURL(blob); link.click(); URL.revokeObjectURL(link.href); } await navigator.clipboard.writeText(`${result}\n${window.location.href}`); notify("Result card saved and link copied.", "success"); }
        } catch (error) {
          if (error.name !== "AbortError") notify("Could not share this result.", "error");
        }
      },

      formatClock(ms) {
        const safe = Math.max(Number(ms || 0), 0);
        const totalSeconds = Math.ceil(safe / 1000);

        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        if (hours > 0) {
          return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
        }

        return `${minutes}:${String(seconds).padStart(2, "0")}`;
      },

      tickClock() {
        if (this.state.status !== "active") {
          this.lastTickAt = Date.now();
          return;
        }

        const now = Date.now();
        const elapsed = now - this.lastTickAt;
        this.lastTickAt = now;

        if (this.state.turn === "white") {
          this.state.white.time_ms = Math.max(Number(this.state.white.time_ms || 0) - elapsed, 0);
        }

        if (this.state.turn === "black") {
          this.state.black.time_ms = Math.max(Number(this.state.black.time_ms || 0) - elapsed, 0);
        }
      },

      showStatus(message) {
        this.statusMessage = message;

        window.setTimeout(() => {
          this.statusMessage = "";
        }, 3000);
      }
    };
  };
})();
