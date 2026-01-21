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

async function loadLogs() {
  const res = await fetch("/logs/api");
  const data = await res.json();
  const box = document.getElementById("log-box");
  const shouldScroll = isNearBottom(box);
  const html = data.lines.map(line => colorize(line)).join("");

  document.getElementById("log-box").innerHTML = html;
  if (shouldScroll) {
    box.scrollTop = box.scrollHeight;
  }
}

setInterval(loadLogs, 3000);
loadLogs();
