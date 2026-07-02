(function () {
  function drawEvaluationGraph(canvas, reviews) {
    if (!canvas || !reviews || reviews.length === 0) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.clientWidth || 600;
    const height = Number(canvas.getAttribute('height') || 120);
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 2;
    const padding = 12;
    const values = reviews.map(item => Math.max(Math.min(Number(item.after_score_white_cp || 0), 1000), -1000));
    const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : width - padding * 2;
    ctx.beginPath();
    values.forEach((value, index) => {
      const x = padding + index * step;
      const y = padding + ((1000 - value) / 2000) * (height - padding * 2);
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
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
      init() {
        this.load();
        this.timer = window.setInterval(() => this.load(), 3000);
      },
      load() {
        fetch(`/analysis/jobs/${this.jobId}/state/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
          .then(response => response.json())
          .then(payload => {
            this.state = payload;
            document.querySelectorAll('.server-review-row').forEach(row => row.classList.add('hidden-by-client'));
            drawEvaluationGraph(document.getElementById('evaluationGraph'), this.state.reviews);
            if (['completed', 'failed', 'cancelled'].includes(this.state.job.status)) window.clearInterval(this.timer);
          })
          .catch(() => {});
      },
      classificationClass(name) {
        const map = {
          best: 'text-bg-success', excellent: 'text-bg-primary', good: 'text-bg-info',
          inaccuracy: 'text-bg-warning', mistake: 'text-bg-danger', blunder: 'text-bg-dark',
          book: 'text-bg-secondary', forced: 'text-bg-secondary', unknown: 'text-bg-secondary'
        };
        return map[name] || 'text-bg-secondary';
      }
    };
  };
})();
