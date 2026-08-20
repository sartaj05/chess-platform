(() => {
  const board = document.getElementById("puzzleBoard");
  const input = document.getElementById("puzzleMove");
  const submit = document.getElementById("puzzleSubmit");
  const help = document.getElementById("puzzleHelp");
  const data = document.getElementById("puzzle-legal-moves");
  if (!board || !input || !submit || !help || !data) return;

  const legalMoves = JSON.parse(data.textContent || "{}");
  let source = null;

  const clearSelection = () => {
    board.querySelectorAll(".selected,.legal-target,.target").forEach((square) =>
      square.classList.remove("selected", "legal-target", "target"),
    );
    input.value = "";
    submit.disabled = true;
  };

  const selectSource = (square) => {
    clearSelection();
    const name = square.dataset.square;
    if (!legalMoves[name]) {
      help.textContent = "Choose one of your pieces that has a legal move.";
      return;
    }
    source = name;
    square.classList.add("selected");
    Object.keys(legalMoves[name]).forEach((destination) =>
      board.querySelector(`[data-square="${destination}"]`)?.classList.add("legal-target"),
    );
    help.textContent = `Selected ${name}. Choose a highlighted destination.`;
  };

  board.addEventListener("click", (event) => {
    const square = event.target.closest("[data-square]");
    if (!square) return;
    const name = square.dataset.square;
    if (!source || legalMoves[name]) {
      selectSource(square);
      return;
    }
    const move = legalMoves[source]?.[name];
    if (!move) {
      help.textContent = `${source} to ${name} is not legal. Choose a highlighted square.`;
      return;
    }
    clearSelection();
    square.classList.add("target");
    input.value = move;
    submit.disabled = false;
    help.textContent = `Playing ${move}…`;
    source = null;
    board.classList.add("is-submitting");
    submit.form.requestSubmit();
  });
})();
