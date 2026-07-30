document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

// ── Cookie helpers (persist page state per browser/user across reloads) ─────

function setCookie(name, value, days) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/; SameSite=Lax';
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

// ── Крок 1: domain list textarea persistence ─────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
  const domainsField = document.getElementById('domains');
  if (domainsField) {
    const saved = getCookie('domain_purchase_domains');
    if (saved && !domainsField.value) {
      domainsField.value = saved;
    }
    domainsField.addEventListener('input', function () {
      setCookie('domain_purchase_domains', this.value, 365);
    });
  }
});

// ── Крок 1: registrator dropdown persistence ─────────────────────────────────

(function restoreSelectedRegistrator() {
  const saved = getCookie('domain_purchase_registrator');
  if (!saved) return;
  const item = document.querySelector('.dropdown-item.registrator[data-value="' + CSS.escape(saved) + '"]');
  if (!item) return;
  const hidden = document.getElementById('selected_registrator');
  if (hidden) hidden.value = saved;
  const btn = document.getElementById('Registrator');
  if (btn) btn.innerText = saved;
})();

document.querySelectorAll('.dropdown-item.registrator').forEach(item => {
  item.addEventListener('click', function () {
    const value = this.getAttribute('data-value');
    document.getElementById('selected_registrator').value = value;
    document.getElementById('Registrator').innerText = value;
    setCookie('domain_purchase_registrator', value, 365);
  });
});

// ── Крок 1: Cloudflare accounts checkbox persistence ─────────────────────────

function updateCfAccountBadge() {
  const badge = document.getElementById('cfAccountCountBadge');
  if (!badge) return;
  badge.textContent = document.querySelectorAll('#cfAccountsContainer .cf-account-check:checked').length;
}

function saveSelectedCfAccounts() {
  const checked = [].slice.call(document.querySelectorAll('#cfAccountsContainer .cf-account-check:checked')).map(cb => cb.value);
  setCookie('domain_purchase_cf_accounts', JSON.stringify(checked), 365);
}

document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('cfAccountsContainer');
  if (!container) return;
  let savedAccounts = [];
  try {
    savedAccounts = JSON.parse(getCookie('domain_purchase_cf_accounts') || '[]');
  } catch (e) {
    savedAccounts = [];
  }
  if (savedAccounts.length) {
    container.querySelectorAll('.cf-account-check').forEach(cb => {
      if (savedAccounts.includes(cb.value)) cb.checked = true;
    });
  }
  updateCfAccountBadge();

  container.addEventListener('change', function (e) {
    if (e.target.classList.contains('cf-account-check')) {
      updateCfAccountBadge();
      saveSelectedCfAccounts();
    }
  });

  const selectAllBtn = document.getElementById('cfSelectAllBtn');
  if (selectAllBtn) {
    selectAllBtn.addEventListener('click', function () {
      container.querySelectorAll('.cf-account-check').forEach(cb => { cb.checked = true; });
      updateCfAccountBadge();
      saveSelectedCfAccounts();
    });
  }

  const deselectAllBtn = document.getElementById('cfDeselectAllBtn');
  if (deselectAllBtn) {
    deselectAllBtn.addEventListener('click', function () {
      container.querySelectorAll('.cf-account-check').forEach(cb => { cb.checked = false; });
      updateCfAccountBadge();
      saveSelectedCfAccounts();
    });
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
