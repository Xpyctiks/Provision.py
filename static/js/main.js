document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

// ── Delete / git pull confirm dialogs (delegated - rows can be swapped in via AJAX pagination) ──

document.addEventListener("click", function (e) {
  const delBtn = e.target.closest(".delete-btn");
  if (delBtn) {
    const mainSite = delBtn.dataset.site;
    const selectedSites = Array.from(
      document.querySelectorAll(".selected-site:checked")
    ).map(chk => chk.value);
    if (!selectedSites.includes(mainSite)) {
      selectedSites.push(mainSite);
    }
    const sitesList = selectedSites.join(", ");
    if (!confirm(`Ви дійсно хочете видалити наступні сайти?\n\n${sitesList}`)) {
      e.preventDefault();
      hideLoading();
    }
    return;
  }
  const gitBtn = e.target.closest(".gitpull-btn");
  if (gitBtn) {
    const mainSite = gitBtn.dataset.site;
    const selectedSites = Array.from(
      document.querySelectorAll(".selected-site:checked")
    ).map(chk => chk.value);
    if (!selectedSites.includes(mainSite)) {
      selectedSites.push(mainSite);
    }
    const sitesList = selectedSites.join(", ");
    if (!confirm(`Оновити код до актуального на наступних сайтах?\n\n${sitesList}`)) {
      e.preventDefault();
      hideLoading();
    }
  }
});

document.addEventListener('show.bs.collapse', async function (event) {
  let button = event.target.previousElementSibling.querySelector("button");
  let path = button.dataset.path;
  let body = event.target.querySelector(".accordion-body");
  body.innerHTML = "Завантажую...";
  let response = await fetch(`/action/show/hrefhistory?domain=${encodeURIComponent(path)}`);
  let html = await response.text();
  body.innerHTML = html;
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
  overlayLoader();
});

window.addEventListener("pageshow", function (event) {
  if (event.persisted) {
  hideLoading();
  }
});

// ── Shift-click range select for row checkboxes (delegated - rows can be swapped in via AJAX pagination) ──

let lastChecked = null;
document.addEventListener("click", function (e) {
  if (!e.target.classList.contains("chk")) return;
  const allChecks = Array.from(document.querySelectorAll(".chk"));
  if (e.shiftKey && lastChecked && allChecks.includes(lastChecked)) {
    let inRange = false;
    allChecks.forEach(box => {
      if (box === e.target || box === lastChecked) {
        inRange = !inRange;
      }
      if (inRange) {
        box.checked = lastChecked.checked;
      }
    });
  }
  lastChecked = e.target;
});

function checkAll(bx) {
  document.querySelectorAll("tbody tr").forEach(row => {
    row.querySelectorAll("input[type=checkbox]").forEach(cb => {
      cb.checked = bx.checked;
    });
  });
}

function initTooltips() {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (tooltipTriggerEl) {
    const existing = bootstrap.Tooltip.getInstance(tooltipTriggerEl);
    if (existing) existing.dispose();
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

document.addEventListener("DOMContentLoaded", initTooltips);

let errorsOnly = false;

let domain = null;
function openEditor(domain) {
  fetch(`/robots/?domain=${encodeURIComponent(domain)}`)
  .then(response => response.json())
  .then(data => {
    document.getElementById("editorTextarea").value = data.content;
    document.getElementById("domain").value = domain
  })
  .catch(err => {
    alert("Помилка завантаження");
    console.error(err);
  });
}

function openDropUpload(site) {
  document.getElementById("dropUploadSitename").value = site;
  document.getElementById("dropUploadSiteLabel").textContent = site;
}

function saveEditor() {
  const content = document.getElementById("editorTextarea").value;
  const domain = document.getElementById("domain").value;
  fetch("/robots/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      domain: domain,
      content: content
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.status === "ok") {
      alert("Збережено");
      bootstrap.Modal.getInstance(
        document.getElementById('editorModal')
      ).hide();
    } else {
      alert(data.error);
    }
  });
}

// ── Slug/hreflang "OK" button (delegated - rows can be swapped in via AJAX pagination) ──

document.addEventListener("click", function (e) {
  const btn = e.target.closest(".buttonSetHref");
  if (!btn) return;
  const slugInput = document.getElementById(btn.dataset.slugId);
  const hreflangInput = document.getElementById(btn.dataset.hreflangId);
  const slug = slugInput.value.trim();
  const hreflang = hreflangInput.value.trim();

  slugInput.classList.toggle("is-invalid", slug === "");
  hreflangInput.classList.toggle("is-invalid", hreflang === "");
  if (slug === "" || hreflang === "") {
    return;
  }

  const formData = new FormData();
  formData.append("slug", slug);
  formData.append("hreflang", hreflang);
  formData.append("action", "page_clone_home");

  fetch(`https://${btn.dataset.site}/api/`, {
    method: "POST",
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    alert("Збережено");
  })
  .catch(err => {
    alert("Помилка надсилання запиту");
    console.error(err);
  });
});

const scrollTopBtn = document.getElementById("scrollTopBtn");
window.addEventListener("scroll", () => {
  if (window.scrollY > 300) {
    scrollTopBtn.style.display = "block";
  } else {
    scrollTopBtn.style.display = "none";
  }
});

scrollTopBtn.addEventListener("click", () => {
  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
});

// ── Backend-driven pagination + filtering (replaces the old client-side row-hiding filter) ──────

function currentFilterParams() {
  const params = new URLSearchParams();
  const search = (document.getElementById("siteFilter")?.value || "").trim();
  const owner = document.getElementById("ownerFilter")?.value || "";
  const account = document.getElementById("accountFilter")?.value || "";
  if (search) params.set("search", search);
  if (owner) params.set("owner", owner);
  if (account) params.set("account", account);
  if (errorsOnly) params.set("errors", "1");
  return params;
}

function updatePaginationUI(page, totalPages, filteredCount, totalCount) {
  const info = document.getElementById("paginationInfo");
  if (info) info.textContent = `Сторінка ${page} з ${totalPages} (${filteredCount} сайтів)`;
  const totalBadge = document.getElementById("headerTotalSitesBadge");
  if (totalBadge) totalBadge.textContent = totalCount;
  const jumpInput = document.getElementById("pageJumpInput");
  if (jumpInput) jumpInput.max = totalPages;
  const params = currentFilterParams();
  const targets = { first: 1, prev: Math.max(1, page - 1), next: Math.min(totalPages, page + 1), last: totalPages };
  document.querySelectorAll(".page-nav-btn").forEach(navBtn => {
    const targetPage = targets[navBtn.dataset.target];
    const p = new URLSearchParams(params);
    p.set("page", targetPage);
    navBtn.href = "/?" + p.toString();
    navBtn.dataset.page = targetPage;
  });
}

function loadSitesPage(page) {
  const params = currentFilterParams();
  params.set("page", page);
  showLoading();
  fetch("/?" + params.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      const tbody = document.querySelector("table.table tbody");
      if (tbody) tbody.innerHTML = data.rows_html;
      updatePaginationUI(data.page, data.total_pages, data.filtered_count, data.total_count);
      const cfErrorIcon = document.getElementById("cfErrorIcon");
      if (cfErrorIcon) cfErrorIcon.style.display = data.has_cf_errors ? "inline-block" : "none";
      initTooltips();
      hideLoading();
    })
    .catch(err => {
      console.error("loadSitesPage() error:", err);
      hideLoading();
    });
}

document.addEventListener("click", function (e) {
  const navBtn = e.target.closest(".page-nav-btn");
  if (!navBtn) return;
  e.preventDefault();
  const targetPage = parseInt(navBtn.dataset.page, 10) || 1;
  loadSitesPage(targetPage);
});

document.addEventListener("DOMContentLoaded", function () {
  const jumpBtn = document.getElementById("pageJumpBtn");
  const jumpInput = document.getElementById("pageJumpInput");
  if (jumpBtn && jumpInput) {
    jumpBtn.addEventListener("click", function () {
      const val = parseInt(jumpInput.value, 10);
      if (val && val > 0) loadSitesPage(val);
    });
    jumpInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        jumpBtn.click();
      }
    });
  }
});

let filterDebounceTimer = null;

function applyFilters() {
  loadSitesPage(1);
}

function scheduleApplyFilters() {
  clearTimeout(filterDebounceTimer);
  filterDebounceTimer = setTimeout(applyFilters, 300);
}

document.getElementById("ownerFilter").addEventListener("change", applyFilters);
document.getElementById("accountFilter").addEventListener("change", applyFilters);
document.getElementById("siteFilter").addEventListener("input", scheduleApplyFilters);

function clearFilters() {
  const siteFilter  = document.getElementById("siteFilter");
  if (siteFilter) siteFilter.value = "";
  if (errorsOnly) {
    errorsOnly = false;
    const cfErrorIcon = document.getElementById("cfErrorIcon");
    if (cfErrorIcon) cfErrorIcon.style.opacity = "1";
  }
  applyFilters();
}

document.addEventListener("DOMContentLoaded", function () {
  const cfErrorIcon = document.getElementById("cfErrorIcon");
  if (cfErrorIcon) {
    //restore errors-only state from the server-rendered URL (?errors=1), so a direct/bookmarked link
    //shows the icon/title correctly without needing a click first
    errorsOnly = cfErrorIcon.dataset.active === "true";
    cfErrorIcon.addEventListener("click", function () {
      errorsOnly = !errorsOnly;
      cfErrorIcon.style.opacity = errorsOnly ? "0.5" : "1";
      cfErrorIcon.title = errorsOnly ? "Показати всі сайти (скинути фільтр)" : "Є проблеми з Cloudflare у деяких сайтів!";
      applyFilters();
    });
  }
});

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    clearFilters();
  }
});

function overlayLoader() {
  const overlayLoader = document.getElementById("overlayLoader");
  overlayLoader.classList.add("d-none");
}

document.addEventListener("DOMContentLoaded", function () {
  const value = document.cookie
    .split('; ')
    .find(row => row.startsWith('x_cache='));

  if (value && value.split('=')[1] === "HIT") {
    document.getElementById("cacheIcon")
      .classList.remove("d-none");
  }
});

function csvEscape(value) {
  const str = value === undefined || value === null ? "" : String(value);
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

document.addEventListener("DOMContentLoaded", function () {
  const exportBtn = document.getElementById("exportHrefHistoryBtn");
  if (!exportBtn) return;
  exportBtn.addEventListener("click", async function () {
    exportBtn.disabled = true;
    showLoading();
    try {
      //full (unpaginated) list of every site visible to this user - the table itself only ever holds
      //the current page's rows, so we can't scrape the DOM for this anymore
      const listResponse = await fetch("/?export_list=1", { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const listData = await listResponse.json();
      const sites = (listData.sites || []).map(s => ({ domain: s.domain, owner: s.owner || "" }));

      const results = await Promise.all(sites.map(async ({ domain, owner }) => {
        try {
          const response = await fetch(`/action/show/hrefhistory?domain=${encodeURIComponent(domain)}&format=json`);
          const history = await response.json();
          return { domain, owner, history: Array.isArray(history) ? history : [] };
        } catch (err) {
          console.warn(`Не вдалося завантажити історію Href для ${domain}:`, err);
          return { domain, owner, history: [] };
        }
      }));

      const keysOrder = [];
      const rows = [];
      results.forEach(({ domain, owner, history }) => {
        if (history.length === 0) {
          rows.push({ domain, owner });
          return;
        }
        history.forEach(entry => {
          Object.keys(entry).forEach(key => {
            if (!keysOrder.includes(key)) keysOrder.push(key);
          });
          rows.push(Object.assign({ domain, owner }, entry));
        });
      });

      const columns = ["domain", "owner", ...keysOrder];
      let csv = "﻿" + columns.join(",") + "\r\n";
      rows.forEach(row => {
        csv += columns.map(col => csvEscape(row[col])).join(",") + "\r\n";
      });

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `href_history_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      alert("Помилка при вивантаженні історії Href у CSV");
      console.error(err);
    } finally {
      hideLoading();
      exportBtn.disabled = false;
    }
  });
});
