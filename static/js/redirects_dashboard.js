document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

function showLoading() {
  const spinner = document.getElementById("spinnerLoading");
  if (spinner) {
    spinner.style.visibility = "visible";
  }
}

function hideLoading() {
  const spinner = document.getElementById("spinnerLoading");
  if (spinner) {
    spinner.style.visibility = "hidden";
  } else {
    console.warn("Spinner element not found!");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  hideLoading();
});

window.addEventListener("pageshow", function (event) {
  if (event.persisted) {
    hideLoading();
  }
});

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})

// ── Full Nginx restart (AJAX) ────────────────────────────────────────────────
// The restart itself happens on the server ~2s after the answer is sent. While Nginx is down, requests to the panel
// (if it's served through the same Nginx) fail - that's expected, the page just keeps polling until Nginx is back.

const NGINX_POLL_INTERVAL = 1500;
const NGINX_RESTART_TIMEOUT = 60000;

function setNginxRestartStatus(html, done) {
  document.getElementById("nginxRestartStatus").innerHTML = html;
  document.getElementById("nginxRestartCloseBtn").disabled = !done;
}

function nginxSpinner(text) {
  return `<div class="spinner-border spinner-border-sm" role="status"></div><span>${text}</span>`;
}

function escapeNginxText(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function waitForNginx(oldPid) {
  const started = Date.now();
  //give the delayed restart time to actually begin before the first check
  await new Promise(r => setTimeout(r, 3000));
  while (Date.now() - started < NGINX_RESTART_TIMEOUT) {
    try {
      const res = await fetch("/redirects_dashboard/nginx_status/", { cache: "no-store" });
      if (res.ok) {
        const st = await res.json();
        if (st.active_state === "active" && st.pid && st.pid !== "0" && st.pid !== oldPid) {
          setNginxRestartStatus(`<span class="text-success">✅ Nginx успішно перезапущено (новий PID ${escapeNginxText(st.pid)}).</span>`, true);
          return;
        }
        if (st.active_state === "failed") {
          setNginxRestartStatus(`<span class="text-danger">❌ Nginx не запустився (стан: ${escapeNginxText(st.active_state)}/${escapeNginxText(st.sub_state)}). Перевірте сервер вручну!</span>`, true);
          return;
        }
        setNginxRestartStatus(nginxSpinner(`Перезапуск... (стан: ${escapeNginxText(st.active_state || "?")})`), false);
      } else {
        setNginxRestartStatus(nginxSpinner("Nginx перезапускається, очікування відповіді сервера..."), false);
      }
    } catch (e) {
      //network error / connection reset - expected while Nginx is down
      setNginxRestartStatus(nginxSpinner("Nginx перезапускається, очікування відповіді сервера..."), false);
    }
    await new Promise(r => setTimeout(r, NGINX_POLL_INTERVAL));
  }
  setNginxRestartStatus('<span class="text-warning">⚠ Не вдалося підтвердити перезапуск за 60 секунд. Перевірте стан Nginx вручну.</span>', true);
}

async function restartNginx() {
  if (!confirm("⚠ Виконати ПОВНИЙ перезапуск (restart) Nginx?\n\nУсі сайти на цьому сервері будуть недоступні кілька секунд.")) return;
  const modal = new bootstrap.Modal(document.getElementById("nginxRestartModal"));
  setNginxRestartStatus(nginxSpinner("Перевірка конфігурації..."), false);
  modal.show();
  try {
    const res = await fetch("/redirects_dashboard/nginx_restart/", { method: "POST" });
    let data = {};
    try { data = await res.json(); } catch (e) { data = { error: "HTTP " + res.status }; }
    if (!res.ok || data.error) {
      setNginxRestartStatus(`<span class="text-danger" style="white-space: pre-line;">❌ ${escapeNginxText(data.error || ("HTTP " + res.status))}</span>`, true);
      return;
    }
    setNginxRestartStatus(nginxSpinner("Конфігурація в порядку, перезапуск Nginx..."), false);
    await waitForNginx(String(data.old_pid || ""));
  } catch (err) {
    setNginxRestartStatus(`<span class="text-danger">❌ Помилка запиту: ${escapeNginxText(err)}</span>`, true);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const btn = document.getElementById("nginxRestartBtn");
  if (btn) btn.addEventListener("click", restartNginx);
});

function applyAccountFilter() {
  const accountFilter = document.getElementById("accountFilter");
  if (!accountFilter) {
    return;
  }
  const account = accountFilter.value.toLowerCase();
  document.querySelectorAll("#redirectsDashboardTable tbody tr").forEach(row => {
    const rowAccount = (row.dataset.account || "").toLowerCase();
    row.style.display = (!account || rowAccount === account) ? "" : "none";
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const accountFilter = document.getElementById("accountFilter");
  if (accountFilter) {
    accountFilter.addEventListener("change", applyAccountFilter);
  }
});

function parseSortDate(text) {
  const match = text.trim().match(/^(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})/);
  if (!match) {
    return 0;
  }
  const [, day, month, year, hours, minutes] = match;
  return new Date(year, month - 1, day, hours, minutes).getTime();
}

document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("redirectsDashboardTable");
  if (!table) {
    return;
  }
  const headers = table.querySelectorAll("th.sortable");
  headers.forEach((header) => {
    const realIndex = Array.from(header.parentElement.children).indexOf(header);
    header.addEventListener("click", function () {
      const sortType = header.dataset.sortType || "text";
      const isAscending = !header.classList.contains("sort-asc");
      headers.forEach(h => h.classList.remove("sort-asc", "sort-desc"));
      header.classList.add(isAscending ? "sort-asc" : "sort-desc");

      const tbody = table.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr")).filter(row => row.children.length > realIndex);

      rows.sort((rowA, rowB) => {
        const cellA = rowA.children[realIndex].innerText.trim();
        const cellB = rowB.children[realIndex].innerText.trim();
        let result;
        if (sortType === "date") {
          result = parseSortDate(cellA) - parseSortDate(cellB);
        } else {
          result = cellA.localeCompare(cellB, "uk");
        }
        return isAscending ? result : -result;
      });

      rows.forEach(row => tbody.appendChild(row));
      tbody.querySelectorAll("tr").forEach((row, i) => {
        const numberCell = row.querySelector("th[scope='row']");
        if (numberCell) {
          numberCell.textContent = i + 1;
        }
      });
    });
  });
});
