(() => {
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  if (!window.location.hash) window.scrollTo({ top: 0, left: 0, behavior: "instant" });

  document.querySelectorAll(".mode-card button").forEach((button) => {
    button.addEventListener("focus", () => button.closest(".mode-card")?.classList.add("keyboard-focus"));
    button.addEventListener("blur", () => button.closest(".mode-card")?.classList.remove("keyboard-focus"));
  });
})();
