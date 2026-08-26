document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

function colorize(line) {
  if (line.includes("ERROR"))
    return `<span class="log-ERROR">${line}</span>`;
  if (line.includes("WARNING"))
    return `<span class="log-WARNING">${line}</span>`;
  if (line.includes("INFO"))
    return `<span class="log-INFO">${line}</span>`;
  return line;
}

function isNearBottom(el, threshold = 50) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}

function hasActiveSelection(el) {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) return false;
  return el.contains(sel.anchorNode);
}

async function loadLogs() {
  const box = document.getElementById("log-box");
  if (hasActiveSelection(box)) return;  
  const res = await fetch("/logs/api/");
  const data = await res.json();
  const shouldScroll = isNearBottom(box);
  const html = data.lines.map(line => colorize(line)).join("");
  box.innerHTML = html;
  if (shouldScroll) {
    box.scrollTop = box.scrollHeight;
  }
}

setInterval(loadLogs, 3000);
loadLogs();
