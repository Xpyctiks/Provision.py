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

// ── Крок 2: SMTP2GO account dropdown persistence ─────────────────────────────

(function restoreSelectedSmtp2go() {
  const saved = getCookie('domain_purchase_smtp2go');
  if (!saved) return;
  const item = document.querySelector('.dropdown-item.smtp2go[data-value="' + CSS.escape(saved) + '"]');
  if (!item) return;
  const hidden = document.getElementById('selected_smtp2go');
  if (hidden) hidden.value = saved;
  const btn = document.getElementById('Smtp2go');
  if (btn) btn.innerText = saved;
})();

document.querySelectorAll('.dropdown-item.smtp2go').forEach(item => {
  item.addEventListener('click', function () {
    const value = this.getAttribute('data-value');
    document.getElementById('selected_smtp2go').value = value;
    document.getElementById('Smtp2go').innerText = value;
    setCookie('domain_purchase_smtp2go', value, 365);
  });
});

// ── Крок 2: Server / Template dropdown click handlers (same pattern as provision.js) ──

document.querySelectorAll('.dropdown-item.server').forEach(item => {
  item.addEventListener('click', function () {
    const value = this.getAttribute('data-value');
    document.getElementById('selected_server').value = value;
    document.getElementById('Server').innerText = value;
  });
});

document.querySelectorAll('.dropdown-item.template').forEach(item => {
  item.addEventListener('click', function () {
    const value = this.getAttribute('data-value');
    document.getElementById('selected_template').value = value;
    document.getElementById('Template').innerText = value;
  });
});

// ── Крок 2: Cloudflare account filter - narrows the domain list and reloads the destination address list ──

function updateDestinationAddresses(account) {
  const select = document.getElementById('destination_email');
  if (!select) return;
  const addresses = (window.DOMAIN_PURCHASE_ADDRESSES || {})[account] || [];
  if (!account) {
    select.innerHTML = '<option value="">— Спочатку оберіть аккаунт Cloudflare вище —</option>';
    return;
  }
  if (!addresses.length) {
    select.innerHTML = '<option value="">Верифікованих адрес не знайдено для цього аккаунту</option>';
    return;
  }
  select.innerHTML = '<option value="">— Оберіть адресу —</option>' +
    addresses.map(email => `<option value="${email}">${email}</option>`).join('');
}

document.addEventListener('DOMContentLoaded', function () {
  const filter = document.getElementById('cfAccountFilter');
  if (!filter) return;
  filter.addEventListener('change', function () {
    const account = this.value;
    document.querySelectorAll('#setupDomainsContainer .setup-domain-item').forEach(item => {
      item.style.display = (!account || item.dataset.account === account) ? '' : 'none';
    });
    updateDestinationAddresses(account);
  });
});

// ── Крок 2: email alias persistence (defaults to "support") ──────────────────

document.addEventListener('DOMContentLoaded', function () {
  const aliasField = document.getElementById('email_alias');
  if (aliasField) {
    const saved = getCookie('domain_purchase_email_alias');
    if (saved) {
      aliasField.value = saved;
    }
    aliasField.addEventListener('input', function () {
      setCookie('domain_purchase_email_alias', this.value, 365);
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
