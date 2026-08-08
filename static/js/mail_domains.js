document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

// ── Крок 1: quick filter by domain / owner / Cloudflare account (same pattern as main.js) ──

function applyMailDomainsFilters() {
  const ownerEl = document.getElementById("mailOwnerFilter");
  const accountEl = document.getElementById("mailAccountFilter");
  const textEl = document.getElementById("mailDomainFilter");
  if (!ownerEl || !accountEl) return;
  const owner = ownerEl.value.toLowerCase();
  const account = accountEl.value.toLowerCase();
  const text = (textEl?.value || "").toLowerCase();
  document.querySelectorAll("tbody tr").forEach(row => {
    const rowOwner = (row.dataset.owner || "").toLowerCase();
    const rowAccount = (row.dataset.account || "").toLowerCase();
    const rowText = row.innerText.toLowerCase();
    const matchOwner = !owner || rowOwner === owner;
    const matchAccount = !account || rowAccount === account;
    const matchText = !text || rowText.includes(text);
    row.style.display = (matchOwner && matchAccount && matchText) ? "" : "none";
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const ownerEl = document.getElementById("mailOwnerFilter");
  const accountEl = document.getElementById("mailAccountFilter");
  const textEl = document.getElementById("mailDomainFilter");
  if (ownerEl) ownerEl.addEventListener("change", applyMailDomainsFilters);
  if (accountEl) accountEl.addEventListener("change", applyMailDomainsFilters);
  if (textEl) textEl.addEventListener("input", applyMailDomainsFilters);
});

function clearMailDomainsFilters() {
  const textEl = document.getElementById("mailDomainFilter");
  if (textEl) textEl.value = "";
  applyMailDomainsFilters();
}

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    clearMailDomainsFilters();
  }
});

// ── Крок 1: confirm before deleting a domain from the remote mail server ─────

document.addEventListener("submit", function (e) {
  if (e.target.classList && e.target.classList.contains("delete-mail-domain-form")) {
    if (!confirm("⚠Видалити цей домен з обслуговування на поштовому сервері? DKIM/DMARC/SPF записи також будуть відкочені.")) {
      e.preventDefault();
    }
  }
});

// ── Loading spinner (shared behavior with other pages) ───────────────────────

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

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl);
});
