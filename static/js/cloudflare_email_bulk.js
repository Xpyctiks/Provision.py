'use strict';

(function () {
  const accountSelect     = document.getElementById('accountSelect');
  const selectedAccount   = document.getElementById('selectedAccount');
  const bulkSection       = document.getElementById('bulkSection');
  const accountLoadingMsg = document.getElementById('accountLoadingMsg');
  const accountErrorMsg   = document.getElementById('accountErrorMsg');
  const destinationSelect = document.getElementById('destinationSelect');
  const domainsContainer  = document.getElementById('domainsContainer');
  const domainsLoadingMsg = document.getElementById('domainsLoadingMsg');
  const noDomainsMsg      = document.getElementById('noDomainsMsg');
  const domainSearch      = document.getElementById('domainSearch');
  const noCatchallFilter  = document.getElementById('noCatchallFilter');
  const selectAllBtn      = document.getElementById('selectAllBtn');
  const deselectAllBtn    = document.getElementById('deselectAllBtn');
  const loginInput        = document.getElementById('loginInput');
  const catchallCheckbox  = document.getElementById('catchallCheckbox');
  const emailPreview      = document.getElementById('emailPreview');
  const submitBtn         = document.getElementById('submitBtn');
  const domainCountBadge  = document.getElementById('domainCountBadge');
  const selectedCountMsg  = document.getElementById('selectedCountMsg');

  // Auto-open flash modal if present
  const modal = document.getElementById('myModal');
  if (modal) {
    new bootstrap.Modal(modal).show();
  }

  // Show the navbar spinner during form submit
  window.showLoading = function () {
    const s = document.getElementById('spinnerLoading');
    if (s) s.style.visibility = 'visible';
  };

  // ── Cookie helpers (persist the catchall filter per browser/user across reloads) ──

  function setCookie(name, value, days) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/; SameSite=Lax';
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  // Checkbox defaults to checked (HTML attribute) - only override it when the cookie explicitly says "0"
  if (getCookie('cf_email_bulk_no_catchall') === '0') {
    noCatchallFilter.checked = false;
  }

  // ── Account selection / domains list loading ────────────────────────────────

  function loadAccountData(account) {
    const preserveDestination = destinationSelect.value;
    const onlyNoCatchall = noCatchallFilter.checked;
    accountErrorMsg.style.display = 'none';
    accountErrorMsg.textContent = '';
    accountLoadingMsg.style.display = 'block';
    domainsLoadingMsg.style.display = 'block';
    domainsContainer.style.display = 'none';
    noDomainsMsg.style.display = 'none';

    const url = '/cloudflare_email_bulk/account_data?account=' + encodeURIComponent(account) +
                '&only_no_catchall=' + (onlyNoCatchall ? '1' : '0');

    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        accountLoadingMsg.style.display = 'none';
        domainsLoadingMsg.style.display = 'none';
        domainsContainer.style.display = '';
        if (data.error) {
          accountErrorMsg.textContent = 'Помилка: ' + data.error;
          accountErrorMsg.style.display = 'block';
          return;
        }

        // Populate destination addresses (keep the previous selection if it's still available)
        destinationSelect.innerHTML = '<option value="">— Оберіть адресу —</option>';
        data.addresses.forEach(function (addr) {
          const opt = document.createElement('option');
          opt.value = addr.email;
          opt.textContent = addr.email;
          destinationSelect.appendChild(opt);
        });
        if (preserveDestination) {
          destinationSelect.value = preserveDestination;
        }

        // Populate domains list
        domainsContainer.innerHTML = '';
        if (data.zones.length === 0) {
          noDomainsMsg.style.display = 'block';
        } else {
          data.zones.forEach(function (zone) {
            const col = document.createElement('div');
            col.className = 'col-12 col-sm-6 col-md-4 col-lg-3 domain-item';
            col.dataset.name = zone.name;
            col.innerHTML =
              '<div class="form-check">' +
                '<input class="form-check-input domain-check" type="checkbox" name="domains" value="' + escapeHtml(zone.name) + '" id="zone-' + escapeHtml(zone.id) + '">' +
                '<label class="form-check-label text-truncate d-block" for="zone-' + escapeHtml(zone.id) + '" title="' + escapeHtml(zone.name) + '">' + escapeHtml(zone.name) + '</label>' +
              '</div>';
            domainsContainer.appendChild(col);
          });
          applyDomainSearchFilter();
        }

        domainCountBadge.textContent = data.zones.length;
        selectedAccount.value = account;
        bulkSection.style.display = 'block';
        updateSubmitState();
        updateSelectedCount();
      })
      .catch(function (err) {
        accountLoadingMsg.style.display = 'none';
        domainsLoadingMsg.style.display = 'none';
        domainsContainer.style.display = '';
        accountErrorMsg.textContent = 'Помилка завантаження: ' + err;
        accountErrorMsg.style.display = 'block';
      });
  }

  accountSelect.addEventListener('change', function () {
    const account = this.value;
    bulkSection.style.display = 'none';
    accountErrorMsg.style.display = 'none';
    accountErrorMsg.textContent = '';
    domainSearch.value = '';

    if (!account) return;

    loadAccountData(account);
  });

  // Toggling the filter re-requests the domains list from Cloudflare for the currently selected account
  noCatchallFilter.addEventListener('change', function () {
    setCookie('cf_email_bulk_no_catchall', this.checked ? '1' : '0', 365);
    if (accountSelect.value) {
      loadAccountData(accountSelect.value);
    }
  });

  // ── Domain search ──────────────────────────────────────────────────────────

  function applyDomainSearchFilter() {
    const q = domainSearch.value.toLowerCase().trim();
    const items = domainsContainer.querySelectorAll('.domain-item');
    let visible = 0;
    items.forEach(function (item) {
      const match = !q || item.dataset.name.toLowerCase().includes(q);
      item.style.display = match ? '' : 'none';
      if (match) visible++;
    });
    noDomainsMsg.style.display = (visible === 0) ? 'block' : 'none';
  }

  domainSearch.addEventListener('input', applyDomainSearchFilter);

  // ── Select / Deselect all (only visible) ──────────────────────────────────

  selectAllBtn.addEventListener('click', function () {
    domainsContainer.querySelectorAll('.domain-item:not([style*="display: none"]) .domain-check').forEach(function (cb) {
      cb.checked = true;
    });
    updateSubmitState();
    updateSelectedCount();
  });

  deselectAllBtn.addEventListener('click', function () {
    domainsContainer.querySelectorAll('.domain-check').forEach(function (cb) {
      cb.checked = false;
    });
    updateSubmitState();
    updateSelectedCount();
  });

  // Track checkbox changes via delegation
  domainsContainer.addEventListener('change', function (e) {
    if (e.target.classList.contains('domain-check')) {
      updateSubmitState();
      updateSelectedCount();
    }
  });

  // ── Login preview ──────────────────────────────────────────────────────────

  loginInput.addEventListener('input', function () {
    updateEmailPreview();
    updateSubmitState();
  });

  destinationSelect.addEventListener('change', updateSubmitState);

  // ── Catchall checkbox - disables the login field, bypasses its requirement ──

  catchallCheckbox.addEventListener('change', function () {
    loginInput.disabled = this.checked;
    updateEmailPreview();
    updateSubmitState();
  });

  // ── Helpers ────────────────────────────────────────────────────────────────

  function updateEmailPreview() {
    if (catchallCheckbox.checked) {
      emailPreview.textContent = 'Усі листи на домен → адреса призначення (catchall)';
      return;
    }
    const login = loginInput.value.trim();
    emailPreview.textContent = login ? login + '@домен → адреса призначення' : 'login@домен';
  }

  function updateSubmitState() {
    const hasDestination = destinationSelect.value !== '';
    const hasLogin       = catchallCheckbox.checked || loginInput.value.trim() !== '';
    const hasChecked     = domainsContainer.querySelectorAll('.domain-check:checked').length > 0;
    submitBtn.disabled   = !(hasDestination && hasLogin && hasChecked);
  }

  function updateSelectedCount() {
    const count = domainsContainer.querySelectorAll('.domain-check:checked').length;
    selectedCountMsg.textContent = count > 0 ? 'Обрано доменів: ' + count : '';
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}());
