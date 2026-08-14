(() => {
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  if (!window.location.hash) window.scrollTo({ top: 0, left: 0, behavior: "instant" });

  document.querySelectorAll(".mode-card button").forEach((button) => {
    button.addEventListener("focus", () => button.closest(".mode-card")?.classList.add("keyboard-focus"));
    button.addEventListener("blur", () => button.closest(".mode-card")?.classList.remove("keyboard-focus"));
  });

  const tour = document.getElementById("onboardingTour");
  const openTour = document.getElementById("openOnboarding");
  if (!tour || !openTour) return;
  const steps = [
    ["Choose how you want to play", "Train with Stockfish, share one device, or create a private online room."],
    ["Set your identity and side", "Enter your display name, then choose White, Black, or let the board decide randomly."],
    ["Build visible progress", "Games, puzzle streaks, ratings, bot levels, daily goals, and achievements update as you play."],
    ["Join the chess community", "Watch live games, challenge friends, enter tournaments, and review every finished game."],
  ];
  let step = 0;
  const title = document.getElementById("tourTitle");
  const description = document.getElementById("tourDescription");
  const number = document.getElementById("tourStepNumber");
  const next = tour.querySelector(".tour-next");
  const closeButtons = tour.querySelectorAll(".tour-close,.tour-skip,.onboarding-backdrop");
  const dots = [...tour.querySelectorAll(".tour-dots i")];
  const render = () => {
    [title.textContent, description.textContent] = steps[step];
    number.textContent = step + 1;
    dots.forEach((dot, index) => dot.classList.toggle("active", index === step));
    next.textContent = step === steps.length - 1 ? "Start playing →" : "Next →";
  };
  const show = () => { step = 0; render(); tour.hidden = false; tour.setAttribute("aria-hidden", "false"); document.body.classList.add("tour-open"); next.focus(); };
  const close = () => { tour.hidden = true; tour.setAttribute("aria-hidden", "true"); document.body.classList.remove("tour-open"); localStorage.setItem("chess-onboarding-complete", "1"); openTour.focus(); };
  openTour.addEventListener("click", show);
  closeButtons.forEach((button) => button.addEventListener("click", close));
  next.addEventListener("click", () => { if (step < steps.length - 1) { step += 1; render(); } else { close(); document.getElementById("playStudio")?.scrollIntoView(); } });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !tour.hidden) close(); });
  if (!localStorage.getItem("chess-onboarding-complete")) window.setTimeout(show, 650);
})();
