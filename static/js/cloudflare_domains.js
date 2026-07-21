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

// Restore previously selected Cloudflare account (if any) before the rest of
// the page wires itself up, so both the top form and the DNS section pick it up.
(function restoreSelectedAccount() {
  const saved = getCookie('provision_cf_account');
  if (!saved) return;
  const item = document.querySelector('.dropdown-item.account[data-value="' + CSS.escape(saved) + '"]');
  if (!item) return;
  document.getElementById('selected_account').value = saved;
  document.getElementById('Account').innerText = saved;
  const dnsAccount = document.getElementById('dns_account');
  if (dnsAccount) dnsAccount.value = saved;
})();

document.querySelectorAll('.dropdown-item.account').forEach(item => {
  item.addEventListener('click', function () {
    let value2 = this.getAttribute('data-value');
    document.getElementById('selected_account').value = value2;
    document.getElementById('Account').innerText = value2;
    setCookie('provision_cf_account', value2, 365);
    const dnsAccount = document.getElementById('dns_account');
    if (dnsAccount) {
      dnsAccount.value = value2;
      loadDnsDomains(value2);
      loadDnsBulkDomains(value2);
    }
  });
});

// ── DNS record collapsible container ─────────────────────────────────────────

function loadDnsDomains(account) {
  const select = document.getElementById('dnsDomainSelect');
  if (!select) return;
  if (!account) {
    select.innerHTML = '<option value="">— Спочатку оберіть аккаунт вище —</option>';
    return;
  }
  select.innerHTML = '<option value="">— Завантаження доменів... —</option>';
  fetch('/cloudflare_domains/zones/?account=' + encodeURIComponent(account))
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        select.innerHTML = '<option value="">Помилка: ' + data.error + '</option>';
        return;
      }
      if (!data.zones.length) {
        select.innerHTML = '<option value="">Немає доменів на цьому аккаунті</option>';
        return;
      }
      select.innerHTML = '<option value="">— Оберіть домен —</option>' +
        data.zones.map(name => `<option value="${name}">${name}</option>`).join('');
    })
    .catch(() => {
      select.innerHTML = '<option value="">Помилка завантаження доменів</option>';
    });
}

document.addEventListener('DOMContentLoaded', function () {
  const dnsAccount = document.getElementById('dns_account');
  if (dnsAccount) {
    loadDnsDomains(dnsAccount.value);
    loadDnsBulkDomains(dnsAccount.value);
  }
  const recordType = document.getElementById('recordType');
  if (recordType) {
    recordType.addEventListener('change', function () {
      const type = this.value;
      document.getElementById('priorityWrapper').style.display = (type === 'MX') ? 'block' : 'none';
      document.getElementById('proxiedWrapper').style.display = (['A', 'AAAA', 'CNAME'].includes(type)) ? 'flex' : 'none';
      setCookie('provision_dns_record_type', type, 365);
    });
    const savedType = getCookie('provision_dns_record_type');
    if (savedType && [].slice.call(recordType.options).some(o => o.value === savedType)) {
      recordType.value = savedType;
    }
    recordType.dispatchEvent(new Event('change'));
  }
  const dnsDomainSelect = document.getElementById('dnsDomainSelect');
  if (dnsDomainSelect) {
    dnsDomainSelect.addEventListener('change', function () {
      loadDnsRecords(document.getElementById('dns_account').value, this.value);
    });
  }

  const recordName = document.getElementById('recordName');
  const recordContent = document.getElementById('recordContent');
  if (recordName) recordName.addEventListener('input', updateDnsSubmitState);
  if (recordContent) recordContent.addEventListener('input', updateDnsSubmitState);

  const dnsDomainSearch = document.getElementById('dnsDomainSearch');
  if (dnsDomainSearch) {
    dnsDomainSearch.addEventListener('input', function () {
      const q = this.value.toLowerCase().trim();
      const container = document.getElementById('dnsDomainsContainer');
      const items = container.querySelectorAll('.dns-domain-item');
      let visible = 0;
      items.forEach(function (item) {
        const match = !q || item.dataset.name.toLowerCase().includes(q);
        item.style.display = match ? '' : 'none';
        if (match) visible++;
      });
      document.getElementById('dnsNoDomainsMsg').style.display = (items.length && visible === 0) ? 'block' : 'none';
    });
  }

  const dnsSelectAllBtn = document.getElementById('dnsSelectAllBtn');
  if (dnsSelectAllBtn) {
    dnsSelectAllBtn.addEventListener('click', function () {
      document.querySelectorAll('#dnsDomainsContainer .dns-domain-item:not([style*="display: none"]) .dns-domain-check').forEach(function (cb) {
        cb.checked = true;
      });
      updateDnsSubmitState();
      saveSelectedDnsDomains();
    });
  }

  const dnsDeselectAllBtn = document.getElementById('dnsDeselectAllBtn');
  if (dnsDeselectAllBtn) {
    dnsDeselectAllBtn.addEventListener('click', function () {
      document.querySelectorAll('#dnsDomainsContainer .dns-domain-check').forEach(function (cb) {
        cb.checked = false;
      });
      updateDnsSubmitState();
      saveSelectedDnsDomains();
    });
  }

  const dnsDomainsContainer = document.getElementById('dnsDomainsContainer');
  if (dnsDomainsContainer) {
    dnsDomainsContainer.addEventListener('change', function (e) {
      if (e.target.classList.contains('dns-domain-check')) {
        updateDnsSubmitState();
        saveSelectedDnsDomains();
      }
    });
  }
});

function saveSelectedDnsDomains() {
  const checked = [].slice.call(document.querySelectorAll('#dnsDomainsContainer .dns-domain-check:checked')).map(cb => cb.value);
  setCookie('provision_dns_domains', JSON.stringify(checked), 365);
}

// ── Bulk domain picker for "add new record" ──────────────────────────────────

function loadDnsBulkDomains(account) {
  const container = document.getElementById('dnsDomainsContainer');
  const noDomainsMsg = document.getElementById('dnsNoDomainsMsg');
  const countBadge = document.getElementById('dnsDomainCountBadge');
  if (!container) return;
  noDomainsMsg.style.display = 'none';
  if (!account) {
    container.innerHTML = '<div class="text-muted text-center py-2">Спочатку оберіть аккаунт вище</div>';
    countBadge.textContent = '0';
    updateDnsSubmitState();
    return;
  }
  container.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm" role="status"></div> Завантаження доменів...</div>';
  fetch('/cloudflare_domains/zones/?account=' + encodeURIComponent(account))
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка: ' + escapeHtml(data.error) + '</div>';
        countBadge.textContent = '0';
        updateDnsSubmitState();
        return;
      }
      container.innerHTML = '';
      if (!data.zones.length) {
        noDomainsMsg.style.display = 'block';
      } else {
        let savedDomains = [];
        try {
          savedDomains = JSON.parse(getCookie('provision_dns_domains') || '[]');
        } catch (e) {
          savedDomains = [];
        }
        data.zones.forEach(function (name, idx) {
          const col = document.createElement('div');
          col.className = 'col-12 col-sm-6 col-md-4 col-lg-3 dns-domain-item';
          col.dataset.name = name;
          const checked = savedDomains.includes(name) ? 'checked' : '';
          col.innerHTML =
            '<div class="form-check">' +
              '<input class="form-check-input dns-domain-check" type="checkbox" name="dns_domains" value="' + escapeHtml(name) + '" id="dns-zone-' + idx + '" ' + checked + '>' +
              '<label class="form-check-label text-truncate d-block" for="dns-zone-' + idx + '" title="' + escapeHtml(name) + '">' + escapeHtml(name) + '</label>' +
            '</div>';
          container.appendChild(col);
        });
      }
      countBadge.textContent = data.zones.length;
      document.getElementById('dnsDomainSearch').value = '';
      updateDnsSubmitState();
    })
    .catch(err => {
      container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка завантаження: ' + escapeHtml(String(err)) + '</div>';
      countBadge.textContent = '0';
      updateDnsSubmitState();
    });
}

function updateDnsSubmitState() {
  const submitBtn = document.getElementById('dnsSubmitBtn');
  const selectedCountMsg = document.getElementById('dnsSelectedCountMsg');
  if (!submitBtn) return;
  const hasName = document.getElementById('recordName').value.trim() !== '';
  const hasContent = document.getElementById('recordContent').value.trim() !== '';
  const checkedCount = document.querySelectorAll('#dnsDomainsContainer .dns-domain-check:checked').length;
  submitBtn.disabled = !(hasName && hasContent && checkedCount > 0);
  selectedCountMsg.textContent = checkedCount > 0 ? 'Обрано доменів: ' + checkedCount : '';
}

// ── Existing DNS records list (view / edit / delete) ─────────────────────────

const RECORD_TYPES = ['A', 'AAAA', 'CNAME', 'TXT', 'MX', 'NS'];

function loadDnsRecords(account, domain) {
  const container = document.getElementById('existingRecordsContainer');
  if (!container) return;
  if (!account || !domain) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm" role="status"></div> Завантаження записів...</div>';
  fetch('/cloudflare_domains/dns_records/?account=' + encodeURIComponent(account) + '&domain=' + encodeURIComponent(domain))
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка: ' + escapeHtml(data.error) + '</div>';
        return;
      }
      renderDnsRecords(data.records);
    })
    .catch(err => {
      container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка завантаження: ' + escapeHtml(String(err)) + '</div>';
    });
}

function renderDnsRecords(records) {
  const container = document.getElementById('existingRecordsContainer');
  if (!container) return;
  if (!records.length) {
    container.innerHTML = '<div class="text-muted text-center py-2">Немає DNS записів для цього домену</div>';
    return;
  }
  let rows = '';
  records.forEach(rec => {
    const showProxied = ['A', 'AAAA', 'CNAME'].includes(rec.type);
    const showPriority = rec.type === 'MX';
    const typeOptions = RECORD_TYPES.map(t => `<option value="${t}" ${t === rec.type ? 'selected' : ''}>${t}</option>`).join('');
    const actions = rec.locked
      ? '<span class="badge bg-secondary" data-bs-toggle="tooltip" title="Системний запис, керується Cloudflare">🔒 Системний</span>'
      : '<button type="button" class="btn btn-sm btn-success save-record-btn" title="Зберегти">💾</button> ' +
        '<button type="button" class="btn btn-sm btn-danger delete-record-btn" title="Видалити">❌</button>';
    rows += `<tr data-record-id="${escapeHtml(rec.id)}">
      <td><select class="form-select form-select-sm rec-type" ${rec.locked ? 'disabled' : ''}>${typeOptions}</select></td>
      <td><input type="text" class="form-control form-control-sm rec-name" value="${escapeHtml(rec.name)}" ${rec.locked ? 'disabled' : ''}></td>
      <td><input type="text" class="form-control form-control-sm rec-content" value="${escapeHtml(rec.content || '')}" ${rec.locked ? 'disabled' : ''}></td>
      <td>
        <select class="form-select form-select-sm rec-ttl" ${rec.locked ? 'disabled' : ''}>
          <option value="1" ${rec.ttl === 1 ? 'selected' : ''}>Auto</option>
          <option value="300" ${rec.ttl === 300 ? 'selected' : ''}>5 хв</option>
          <option value="3600" ${rec.ttl === 3600 ? 'selected' : ''}>1 год</option>
          <option value="86400" ${rec.ttl === 86400 ? 'selected' : ''}>1 доба</option>
        </select>
      </td>
      <td class="text-center"><input type="checkbox" class="form-check-input rec-proxied" ${rec.proxied ? 'checked' : ''} ${rec.locked ? 'disabled' : ''} style="${showProxied ? '' : 'display:none;'}"></td>
      <td><input type="number" class="form-control form-control-sm rec-priority" value="${rec.priority != null ? rec.priority : ''}" ${rec.locked ? 'disabled' : ''} style="${showPriority ? '' : 'display:none;'}"></td>
      <td class="text-nowrap">${actions}</td>
    </tr>`;
  });
  container.innerHTML = `<div class="table-responsive"><table class="table table-bordered table-sm align-middle mb-0">
    <thead><tr>
      <th style="width:9%">Тип</th>
      <th style="width:20%">Ім'я</th>
      <th style="width:23%">Значення</th>
      <th style="width:9%">TTL</th>
      <th style="width:8%">Proxied</th>
      <th style="width:9%">Пріоритет</th>
      <th style="width:22%">Дії</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;

  container.querySelectorAll('.rec-type').forEach(sel => {
    sel.addEventListener('change', function () {
      const row = this.closest('tr');
      const type = this.value;
      row.querySelector('.rec-proxied').style.display = RECORD_TYPES.slice(0, 3).includes(type) ? '' : 'none';
      row.querySelector('.rec-priority').style.display = (type === 'MX') ? '' : 'none';
    });
  });

  container.querySelectorAll('.save-record-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      saveDnsRecord(this.closest('tr'));
    });
  });

  container.querySelectorAll('.delete-record-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      deleteDnsRecord(this.closest('tr'));
    });
  });

  const tooltips = [].slice.call(container.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltips.map(el => new bootstrap.Tooltip(el));
}

function saveDnsRecord(row) {
  const account = document.getElementById('dns_account').value;
  const domain = document.getElementById('dnsDomainSelect').value;
  const formData = new FormData();
  formData.append('dns_account', account);
  formData.append('dns_domain', domain);
  formData.append('record_id', row.dataset.recordId);
  formData.append('record_type', row.querySelector('.rec-type').value);
  formData.append('record_name', row.querySelector('.rec-name').value);
  formData.append('record_content', row.querySelector('.rec-content').value);
  formData.append('record_ttl', row.querySelector('.rec-ttl').value);
  formData.append('record_priority', row.querySelector('.rec-priority').value);
  formData.append('record_proxied', row.querySelector('.rec-proxied').checked ? 'true' : 'false');

  const saveBtn = row.querySelector('.save-record-btn');
  saveBtn.disabled = true;
  fetch('/cloudflare_domains/dns_records/update/', { method: 'POST', body: formData })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        loadDnsRecords(account, domain);
      } else {
        saveBtn.disabled = false;
        alert('Помилка збереження: ' + (data.error || 'Невідома помилка'));
      }
    })
    .catch(err => {
      saveBtn.disabled = false;
      alert('Помилка збереження: ' + err);
    });
}

function deleteDnsRecord(row) {
  if (!confirm('⚠Видалити цей DNS запис?')) return;
  const account = document.getElementById('dns_account').value;
  const domain = document.getElementById('dnsDomainSelect').value;
  const formData = new FormData();
  formData.append('dns_account', account);
  formData.append('dns_domain', domain);
  formData.append('record_id', row.dataset.recordId);

  const delBtn = row.querySelector('.delete-record-btn');
  delBtn.disabled = true;
  fetch('/cloudflare_domains/dns_records/delete/', { method: 'POST', body: formData })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        loadDnsRecords(account, domain);
      } else {
        delBtn.disabled = false;
        alert('Помилка видалення: ' + (data.error || 'Невідома помилка'));
      }
    })
    .catch(err => {
      delBtn.disabled = false;
      alert('Помилка видалення: ' + err);
    });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

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

document.getElementById("buttonShowZones").addEventListener("click", function () {
  document.getElementById("modalResultBody").innerHTML = `
  <div class="text-center">
    <div class="spinner-border" role="status"></div>
    <div>Завантаження...</div>
  </div>`;
  let modal = new bootstrap.Modal(document.getElementById('resultModal'));
  modal.show();

  let formData = new FormData();
  formData.append("domain", document.getElementById("domain").value);
  formData.append("selected_account", document.getElementById("selected_account").value);
  fetch("/cloudflare_domains/existing_domains/", {
    method: "POST",
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    document.getElementById("modalResultBody").innerHTML =
      `<div class="alert alert-secondary">${data.message}</div>`;
    modal.show();
  })
  .catch(error => {
    document.getElementById("modalResultBody").innerHTML =
      `<div class="alert alert-danger">Ошибка: ${error}</div>`;
    modal.show();
  });
});

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
})

function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
      document.execCommand("copy") ? resolve() : reject(new Error("execCommand('copy') failed"));
    } catch (err) {
      reject(err);
    } finally {
      document.body.removeChild(textarea);
    }
  });
}

function copyText(elementId) {
  const el = document.getElementById(elementId);
  if (!el) {
    console.warn(`copyText(): element #${elementId} not found!`);
    return;
  }
  copyToClipboard(el.textContent).then(() => {
    alert("✅Скопійовано в буфер обміну!");
  }).catch(err => {
    console.error("♨Помилка копіювання:", err);
  });
}

function copyAllDomains() {
  const text = document.getElementById("copyAllDomainsBtn").getAttribute("data-domains");
  copyToClipboard(text).then(() => {
    alert("✅Скопійовано в буфер обміну!");
  }).catch(err => {
    console.error("♨Помилка копіювання:", err);
  });
}

document.addEventListener("submit", function (e) {
  const btn = e.submitter;
  if (btn && btn.classList.contains("delDomain-btn")) {
    if (!confirm("⚠Видалити цей домен з аккаунту?")) {
      e.preventDefault();
    }
  }
});
