(function () {
  "use strict";

  const POLL_INTERVAL_MS = 3000;
  const MAX_CONSECUTIVE_ERRORS = 5;
  const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

  function notify(message, type) {
    if (window.Toast) {
      window.Toast.show(message, type);
    }
  }

  function drawEvaluationGraph(canvas, reviews) {
    if (!canvas || !reviews || reviews.length === 0) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.clientWidth || 600;
    const height = Number(canvas.getAttribute("height") || 120);
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    const styles = getComputedStyle(document.documentElement);
    ctx.strokeStyle = (styles.getPropertyValue("--brass-light") || "#e4c37d").trim();
    ctx.lineWidth = 2;

    const padding = 12;
    const values = reviews.map((item) =>
      Math.max(Math.min(Number(item.after_score_white_cp || 0), 1000), -1000)
    );
    const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : width - padding * 2;

    ctx.beginPath();
    values.forEach((value, index) => {
      const x = padding + index * step;
      const y = padding + ((1000 - value) / 2000) * (height - padding * 2);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.strokeStyle = (styles.getPropertyValue("--surface-border-strong") || "rgba(228,195,125,.26)").trim();
    ctx.beginPath();
    ctx.moveTo(padding, height / 2);
    ctx.lineTo(width - padding, height / 2);
    ctx.stroke();
  }

  window.analysisJob = function analysisJob(jobId) {
    return {
      jobId,
      state: { job: {}, reviews: [] },
      timer: null,
      resizeHandler: null,
      loading: false,
      consecutiveErrors: 0,

      init() {
        this.load();
        this.timer = window.setInterval(() => this.load(), POLL_INTERVAL_MS);

        this.resizeHandler = () => {
          drawEvaluationGraph(document.getElementById("evaluationGraph"), this.state.reviews);
        };
        window.addEventListener("resize", this.resizeHandler);

        window.addEventListener("beforeunload", () => this.stop());
      },

      stop() {
        if (this.timer) {
          window.clearInterval(this.timer);
          this.timer = null;
        }
        if (this.resizeHandler) {
          window.removeEventListener("resize", this.resizeHandler);
          this.resizeHandler = null;
        }
      },

      load() {
        if (this.loading) return;
        this.loading = true;

        fetch(`/analysis/jobs/${this.jobId}/state/`, {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
          .then((response) => {
            if (!response.ok) throw new Error(`Request failed with ${response.status}`);
            return response.json();
          })
          .then((payload) => {
            this.consecutiveErrors = 0;
            this.state = payload;

            document.querySelectorAll(".server-review-row").forEach((row) => {
              row.classList.add("hidden-by-client");
            });

            drawEvaluationGraph(document.getElementById("evaluationGraph"), this.state.reviews);

            if (TERMINAL_STATUSES.includes(this.state.job.status)) {
              this.stop();
            }
          })
          .catch(() => {
            this.consecutiveErrors += 1;
            if (this.consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
              notify("Lost connection to the analysis job. Reload to retry.", "error");
              this.stop();
            }
          })
          .finally(() => {
            this.loading = false;
          });
      },

      classificationClass(name) {
        const map = {
          best: "text-bg-success",
          excellent: "text-bg-primary",
          good: "text-bg-info",
          inaccuracy: "text-bg-warning",
          mistake: "text-bg-danger",
          blunder: "text-bg-dark",
          book: "text-bg-secondary",
          forced: "text-bg-secondary",
          unknown: "text-bg-secondary"
        };
        return map[name] || "text-bg-secondary";
      }
    };
  };
})();