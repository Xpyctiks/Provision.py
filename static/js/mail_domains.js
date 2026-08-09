document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

// ── Крок 1: Cloudflare account -> domain AJAX (reuses the existing /cloudflare_domains/zones/ endpoint) ──

document.addEventListener('DOMContentLoaded', function () {
  const cfSelect = document.getElementById('mailCfAccount');
  const domainSelect = document.getElementById('mailDomain');
  if (!cfSelect || !domainSelect) return;
  cfSelect.addEventListener('change', function () {
    const account = this.value;
    if (!account) {
      domainSelect.innerHTML = '<option value="">— Спочатку оберіть аккаунт —</option>';
      domainSelect.disabled = true;
      return;
    }
    domainSelect.disabled = true;
    domainSelect.innerHTML = '<option value="">— Завантаження доменів... —</option>';
    fetch('/cloudflare_domains/zones/?account=' + encodeURIComponent(account))
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          domainSelect.innerHTML = '<option value="">Помилка: ' + data.error + '</option>';
          return;
        }
        if (!data.zones.length) {
          domainSelect.innerHTML = '<option value="">Немає доменів на цьому аккаунті</option>';
          return;
        }
        domainSelect.innerHTML = '<option value="">— Оберіть домен —</option>' +
          data.zones.map(name => `<option value="${name}">${name}</option>`).join('');
        domainSelect.disabled = false;
      })
      .catch(() => {
        domainSelect.innerHTML = '<option value="">Помилка завантаження доменів</option>';
      });
  });
});

// ── Крок 2: quick filter by domain / owner / Cloudflare account (same pattern as main.js) ──

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

// ── Крок 2: confirm before deleting a domain from the remote mail server ─────

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
