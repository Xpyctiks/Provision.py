document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

const PAGE_LINES = 500;
const POLL_INTERVAL = 3000;
//how close to the top (px) the user must scroll to trigger loading of the previous page
const LOAD_MORE_THRESHOLD = 150;

const logState = {
  oldest: null,     // byte offset of the first line shown - older lines are before it
  newest: null,     // byte offset right after the last line shown - new lines are polled from here
  loadingOlder: false,
  polling: false
};

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function colorize(line) {
  const safe = escapeHtml(line);
  if (line.includes(" - ERROR - ") || line.includes("ERROR"))
    return `<span class="log-ERROR">${safe}</span>`;
  if (line.includes(" - WARNING - ") || line.includes("WARNING"))
    return `<span class="log-WARNING">${safe}</span>`;
  if (line.includes(" - INFO - ") || line.includes("INFO"))
    return `<span class="log-INFO">${safe}</span>`;
  return safe;
}

function renderLines(lines) {
  return lines.map(colorize).join("");
}

function isNearBottom(el, threshold = 50) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}

function setTopStatus(text) {
  document.getElementById("log-top-status").textContent = text;
}

function updateTopStatus() {
  setTopStatus(logState.oldest > 0 ? "⬆ Прокрутіть вгору, щоб завантажити попередні рядки" : "— Початок файлу логу —");
}

async function fetchLog(params) {
  const res = await fetch("/logs/api/?" + new URLSearchParams(params).toString());
  const data = await res.json();
  if (!res.ok || data.error) throw new Error(data.error || ("HTTP " + res.status));
  return data;
}

// ── Initial load: last PAGE_LINES lines ──────────────────────────────────────

async function loadInitial() {
  const box = document.getElementById("log-box");
  const content = document.getElementById("log-content");
  try {
    const data = await fetchLog({ lines: PAGE_LINES });
    content.innerHTML = renderLines(data.lines);
    logState.oldest = data.start;
    logState.newest = data.end;
    updateTopStatus();
    box.scrollTop = box.scrollHeight;
    //the log may be shorter than the box - then there's no scrollbar to trigger loading, so load more right away
    maybeLoadOlder();
  } catch (err) {
    setTopStatus("Помилка завантаження логу: " + err.message);
  }
}

// ── Scrolling up: prepend previous PAGE_LINES lines ──────────────────────────

async function maybeLoadOlder() {
  const box = document.getElementById("log-box");
  if (logState.loadingOlder || !logState.oldest || box.scrollTop > LOAD_MORE_THRESHOLD) return;
  logState.loadingOlder = true;
  setTopStatus("Завантаження попередніх рядків...");
  try {
    const data = await fetchLog({ before: logState.oldest, lines: PAGE_LINES });
    const content = document.getElementById("log-content");
    //keep the same lines under the user's eyes: shift scroll by the height of the prepended block
    const prevHeight = box.scrollHeight;
    content.insertAdjacentHTML("afterbegin", renderLines(data.lines));
    box.scrollTop += box.scrollHeight - prevHeight;
    logState.oldest = data.start;
    updateTopStatus();
  } catch (err) {
    setTopStatus("Помилка завантаження: " + err.message);
  } finally {
    logState.loadingOlder = false;
  }
  //still at the top (short page / fast scroll) - continue loading
  if (logState.oldest > 0 && box.scrollTop <= LOAD_MORE_THRESHOLD && box.scrollHeight <= box.clientHeight + LOAD_MORE_THRESHOLD) {
    maybeLoadOlder();
  }
}

// ── Live tail: append newly written lines ────────────────────────────────────

async function pollNew() {
  if (logState.polling || logState.newest === null) return;
  logState.polling = true;
  const box = document.getElementById("log-box");
  try {
    const data = await fetchLog({ after: logState.newest });
    if (data.reset) {
      //log was rotated/truncated (or grew too much since the last poll) - start over from the end of the file
      await loadInitial();
      return;
    }
    if (data.lines.length) {
      const shouldScroll = isNearBottom(box);
      //insertAdjacentHTML (not innerHTML) keeps an active text selection intact
      document.getElementById("log-content").insertAdjacentHTML("beforeend", renderLines(data.lines));
      if (shouldScroll) box.scrollTop = box.scrollHeight;
    }
    logState.newest = data.end;
  } catch (err) {
    console.warn("Log polling error:", err);
  } finally {
    logState.polling = false;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("log-box").addEventListener("scroll", maybeLoadOlder);
  loadInitial();
  setInterval(pollNew, POLL_INTERVAL);
});
