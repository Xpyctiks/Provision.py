  document.addEventListener('DOMContentLoaded', () => {
    const pre = document.getElementById('logContent');
    const lines = pre.textContent.split('\n');
    const colored = lines.map(line => {
      let cls = '';
      if (line.includes('ERROR')) cls = 'log-error';
      else if (line.includes('WARN')) cls = 'log-warn';
      else if (line.includes('INFO')) cls = 'log-info';
      else if (line.includes('DEBUG')) cls = 'log-debug';
      return cls
        ? `<div class="${cls}">${line}</div>`
        : `<div>${line}</div>`;
    }).join('');
    pre.innerHTML = colored;

    const modalElement = document.getElementById("myModal");
    if (modalElement) {
      const modal = new bootstrap.Modal(modalElement);
      modal.show();
    }
});

async function loadLogs() {
  const res = await fetch("/logs/api?lines=300");
  const data = await res.json();
  document.getElementById("log-box").textContent =
    data.lines.join("");
}

setInterval(loadLogs, 3000);
loadLogs();
