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

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Page state ───────────────────────────────────────────────────────────────

const state = {
  registrator: '',
  domains: [],          // all domains of the registrator, as returned by the API
  filtered: [],         // after search + sort
  page: 1,
  perPage: 500,         // 0 = all
  sortField: 'name',
  sortDir: 'asc',
  selected: new Set()   // selected domain names - kept across pages/search
};

const COOKIE_SORT = 'regdomains_sort';
const COOKIE_PER_PAGE = 'regdomains_per_page';
const COOKIE_REGISTRATOR = 'regdomains_registrator';

// ── Loading the domain list ──────────────────────────────────────────────────

function loadDomains() {
  const container = document.getElementById('domainsContainer');
  const toolbar = document.getElementById('domainsToolbar');
  state.domains = [];
  state.selected.clear();
  state.page = 1;
  document.getElementById('paginationNav').innerHTML = '';
  updateSelectedState();
  if (!state.registrator) {
    toolbar.classList.add('d-none');
    container.innerHTML = '<div class="text-muted text-center py-3">Спочатку оберіть реєстратора</div>';
    document.getElementById('reloadDomainsBtn').disabled = true;
    return;
  }
  document.getElementById('reloadDomainsBtn').disabled = false;
  toolbar.classList.add('d-none');
  container.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm" role="status"></div> Завантаження доменів з API реєстратора (може зайняти деякий час)...</div>';
  fetch('/domain_registrators/domains/?registrator=' + encodeURIComponent(state.registrator))
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка: ' + escapeHtml(data.error) + '</div>';
        return;
      }
      state.domains = data.domains || [];
      toolbar.classList.remove('d-none');
      applyFilterAndSort();
    })
    .catch(err => {
      container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка завантаження: ' + escapeHtml(String(err)) + '</div>';
    });
}

// ── Search + sort ────────────────────────────────────────────────────────────

function sortKey(domain, field) {
  if (field === 'ns') return (domain.ns || []).join(',');
  if (field === 'created') return domain.created || '';
  return domain.name || '';
}

function applyFilterAndSort() {
  const q = document.getElementById('domainSearch').value.toLowerCase().trim();
  let list = state.domains;
  if (q) {
    list = list.filter(d =>
      d.name.includes(q) ||
      (d.ns || []).join(',').includes(q) ||
      String(d.status || '').toLowerCase().includes(q)
    );
  }
  const field = state.sortField;
  const dir = state.sortDir === 'desc' ? -1 : 1;
  list = list.slice().sort((a, b) => {
    const result = sortKey(a, field).localeCompare(sortKey(b, field), 'uk');
    //secondary order by name keeps groups (same NS / same date) stable and readable
    return result !== 0 ? result * dir : a.name.localeCompare(b.name);
  });
  state.filtered = list;
  const pages = totalPages();
  if (state.page > pages) state.page = pages;
  render();
}

function totalPages() {
  if (!state.perPage) return 1;
  return Math.max(1, Math.ceil(state.filtered.length / state.perPage));
}

// ── Rendering ────────────────────────────────────────────────────────────────

function formatDate(value) {
  //'YYYY-MM-DD HH:MM' -> 'DD.MM.YYYY HH:MM'
  const m = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}:\d{2}))?/);
  if (!m) return escapeHtml(value || '—');
  return `${m[3]}.${m[2]}.${m[1]}${m[4] ? ' ' + m[4] : ''}`;
}

function statusBadge(status) {
  const s = String(status || '-');
  let cls = 'bg-secondary';
  if (/^(active|registered)$/i.test(s)) cls = 'bg-success';
  else if (/expired|hold|disabled|suspended|redemption|grace/i.test(s)) cls = 'bg-danger';
  else if (/locked|unverified|verification/i.test(s)) cls = 'bg-warning text-dark';
  return `<span class="badge ${cls}">${escapeHtml(s)}</span>`;
}

function render() {
  const container = document.getElementById('domainsContainer');
  document.getElementById('domainsCountBadge').textContent =
    state.filtered.length === state.domains.length ? `Доменів: ${state.domains.length}` : `Знайдено: ${state.filtered.length} з ${state.domains.length}`;
  if (!state.filtered.length) {
    container.innerHTML = '<div class="text-muted text-center py-3">Немає доменів для відображення</div>';
    document.getElementById('paginationNav').innerHTML = '';
    updateSelectedState();
    return;
  }
  const start = state.perPage ? (state.page - 1) * state.perPage : 0;
  const pageItems = state.perPage ? state.filtered.slice(start, start + state.perPage) : state.filtered;
  let rows = '';
  pageItems.forEach((d, i) => {
    const checked = state.selected.has(d.name) ? 'checked' : '';
    rows += `<tr>
      <td class="text-center"><input class="form-check-input domain-check" type="checkbox" value="${escapeHtml(d.name)}" ${checked}></td>
      <td class="text-muted small">${start + i + 1}</td>
      <td>${escapeHtml(d.name)}</td>
      <td class="ns-cell">${(d.ns || []).map(escapeHtml).join('<br>') || '—'}</td>
      <td class="text-nowrap">${formatDate(d.created)}</td>
      <td>${statusBadge(d.status)}</td>
    </tr>`;
  });
  const sortClass = field => state.sortField === field ? (state.sortDir === 'desc' ? 'sort-desc' : 'sort-asc') : '';
  container.innerHTML = `<div class="table-responsive"><table class="table table-bordered table-hover table-sm align-middle mb-0" id="regDomainsTable">
    <thead class="table-warning"><tr>
      <th style="width:40px" class="text-center"><input class="form-check-input" type="checkbox" id="selectPageCheck" title="Обрати всі на цій сторінці"></th>
      <th style="width:60px">#</th>
      <th class="sortable ${sortClass('name')}" data-sort="name">Домен:</th>
      <th class="sortable ${sortClass('ns')}" data-sort="ns">NS сервери:</th>
      <th class="sortable ${sortClass('created')}" data-sort="created" style="width:170px">Дата додавання:</th>
      <th style="width:200px">Стан:</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;
  renderPagination();
  updateSelectedState();
}

function renderPagination() {
  const nav = document.getElementById('paginationNav');
  const pages = totalPages();
  if (pages <= 1) {
    nav.innerHTML = '';
    return;
  }
  const item = (page, label, disabled, active) =>
    `<li class="page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}"><a class="page-link" href="#" data-page="${page}">${label}</a></li>`;
  let html = '<ul class="pagination pagination-sm flex-wrap justify-content-center mb-0">';
  html += item(state.page - 1, '«', state.page === 1, false);
  //compact window: first, last, and 2 pages around the current one
  let last = 0;
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - state.page) <= 2) {
      if (last && p - last > 1) html += '<li class="page-item disabled"><span class="page-link">…</span></li>';
      html += item(p, p, false, p === state.page);
      last = p;
    }
  }
  html += item(state.page + 1, '»', state.page === pages, false);
  html += '</ul>';
  nav.innerHTML = html;
}

// ── Selection ────────────────────────────────────────────────────────────────

function updateSelectedState() {
  const count = state.selected.size;
  document.getElementById('selectedCount').textContent = count;
  document.getElementById('changeNsBtn').disabled = count === 0;
  const pageCheck = document.getElementById('selectPageCheck');
  if (pageCheck) {
    const boxes = document.querySelectorAll('#regDomainsTable .domain-check');
    const checkedBoxes = document.querySelectorAll('#regDomainsTable .domain-check:checked');
    pageCheck.checked = boxes.length > 0 && boxes.length === checkedBoxes.length;
    pageCheck.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < boxes.length;
  }
}

// ── NS change modal ──────────────────────────────────────────────────────────

function collectNs() {
  const fromChecks = [].slice.call(document.querySelectorAll('#cfNsOptions .cf-ns-check:checked')).map(cb => cb.value);
  const manual = document.getElementById('manualNs').value.split(/[\s,;]+/);
  const result = [];
  fromChecks.concat(manual).forEach(ns => {
    ns = ns.trim().toLowerCase().replace(/\.$/, '');
    if (ns && !result.includes(ns)) result.push(ns);
  });
  return result;
}

function updateNsPreview() {
  const ns = collectNs();
  const preview = document.getElementById('nsPreview');
  preview.textContent = ns.length ? ns.join(', ') : '—';
  preview.classList.toggle('text-danger', ns.length > 0 && (ns.length < 2 || ns.length > 12));
  document.getElementById('submitNsBtn').disabled = ns.length < 2 || ns.length > 12 || state.selected.size === 0;
}

function submitNs() {
  const ns = collectNs();
  const domains = Array.from(state.selected);
  if (!confirm(`Встановити NS:\n${ns.join('\n')}\n\nдля ${domains.length} домен(ів) через API реєстратора ${state.registrator}?`)) return;
  const resultBox = document.getElementById('changeNsResult');
  const submitBtn = document.getElementById('submitNsBtn');
  submitBtn.disabled = true;
  resultBox.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm" role="status"></div> Встановлення NS... (по одному запиту на домен, може зайняти деякий час)</div>';
  fetch('/domain_registrators/set_ns/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ registrator: state.registrator, domains: domains, ns: ns })
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        resultBox.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка: ' + escapeHtml(data.error) + '</div>';
        submitBtn.disabled = false;
        return;
      }
      const cls = data.ok_count === data.total ? 'alert-success' : (data.ok_count === 0 ? 'alert-danger' : 'alert-warning');
      const lines = data.results.map(r => `${r.ok ? '✅' : '❌'} ${escapeHtml(r.domain)}: ${escapeHtml(r.message)}`).join('<br>');
      resultBox.innerHTML = `<div class="alert ${cls} py-2 mb-0"><strong>NS встановлено: ${data.ok_count} з ${data.total}</strong><br>${lines}</div>`;
      //reflect successful changes in the table right away, without re-querying the registrator
      const okDomains = new Set(data.results.filter(r => r.ok).map(r => r.domain));
      state.domains.forEach(d => { if (okDomains.has(d.name)) d.ns = data.ns.slice(); });
      okDomains.forEach(name => state.selected.delete(name));
      applyFilterAndSort();
      document.getElementById('changeNsDomainsCount').textContent = state.selected.size;
      updateNsPreview();
    })
    .catch(err => {
      resultBox.innerHTML = '<div class="alert alert-danger py-2 mb-0">Помилка: ' + escapeHtml(String(err)) + '</div>';
      submitBtn.disabled = false;
    });
}

// ── Wiring ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
  const regSelect = document.getElementById('registratorSelect');
  const sortSelect = document.getElementById('sortSelect');
  const perPageSelect = document.getElementById('perPageSelect');

  //restore saved settings
  const savedSort = getCookie(COOKIE_SORT);
  if (savedSort && [].slice.call(sortSelect.options).some(o => o.value === savedSort)) sortSelect.value = savedSort;
  [state.sortField, state.sortDir] = sortSelect.value.split(':');
  const savedPerPage = getCookie(COOKIE_PER_PAGE);
  if (savedPerPage !== null && [].slice.call(perPageSelect.options).some(o => o.value === savedPerPage)) perPageSelect.value = savedPerPage;
  state.perPage = parseInt(perPageSelect.value, 10) || 0;

  regSelect.addEventListener('change', function () {
    state.registrator = this.value;
    setCookie(COOKIE_REGISTRATOR, this.value, 365);
    loadDomains();
  });
  const savedReg = getCookie(COOKIE_REGISTRATOR);
  if (savedReg && [].slice.call(regSelect.options).some(o => o.value === savedReg)) {
    regSelect.value = savedReg;
    state.registrator = savedReg;
    loadDomains();
  }

  document.getElementById('reloadDomainsBtn').addEventListener('click', loadDomains);

  document.getElementById('domainSearch').addEventListener('input', function () {
    state.page = 1;
    applyFilterAndSort();
  });

  sortSelect.addEventListener('change', function () {
    [state.sortField, state.sortDir] = this.value.split(':');
    setCookie(COOKIE_SORT, this.value, 365);
    applyFilterAndSort();
  });

  perPageSelect.addEventListener('change', function () {
    state.perPage = parseInt(this.value, 10) || 0;
    state.page = 1;
    setCookie(COOKIE_PER_PAGE, this.value, 365);
    applyFilterAndSort();
  });

  document.getElementById('paginationNav').addEventListener('click', function (e) {
    const link = e.target.closest('a[data-page]');
    if (!link) return;
    e.preventDefault();
    const page = parseInt(link.dataset.page, 10);
    if (page >= 1 && page <= totalPages() && page !== state.page) {
      state.page = page;
      render();
      document.getElementById('domainsContainer').scrollIntoView({ behavior: 'smooth' });
    }
  });

  const container = document.getElementById('domainsContainer');
  container.addEventListener('change', function (e) {
    if (e.target.classList.contains('domain-check')) {
      if (e.target.checked) state.selected.add(e.target.value);
      else state.selected.delete(e.target.value);
      updateSelectedState();
    } else if (e.target.id === 'selectPageCheck') {
      container.querySelectorAll('.domain-check').forEach(cb => {
        cb.checked = e.target.checked;
        if (cb.checked) state.selected.add(cb.value);
        else state.selected.delete(cb.value);
      });
      updateSelectedState();
    }
  });

  //click on a sortable header - same as picking the option in the sort dropdown (and also saved to cookie)
  container.addEventListener('click', function (e) {
    const header = e.target.closest('th.sortable');
    if (!header) return;
    const field = header.dataset.sort;
    let dir = field === 'created' ? 'desc' : 'asc';
    if (state.sortField === field) dir = state.sortDir === 'asc' ? 'desc' : 'asc';
    sortSelect.value = `${field}:${dir}`;
    sortSelect.dispatchEvent(new Event('change'));
  });

  document.getElementById('selectFilteredBtn').addEventListener('click', function () {
    state.filtered.forEach(d => state.selected.add(d.name));
    render();
  });

  document.getElementById('deselectAllBtn').addEventListener('click', function () {
    state.selected.clear();
    render();
  });

  const nsModal = new bootstrap.Modal(document.getElementById('changeNsModal'));
  document.getElementById('changeNsBtn').addEventListener('click', function () {
    document.getElementById('changeNsDomainsCount').textContent = state.selected.size;
    document.getElementById('changeNsResult').innerHTML = '';
    updateNsPreview();
    nsModal.show();
  });
  document.getElementById('cfNsOptions').addEventListener('change', updateNsPreview);
  document.getElementById('manualNs').addEventListener('input', updateNsPreview);
  document.getElementById('submitNsBtn').addEventListener('click', submitNs);
});

// ── Loading spinner (shared behavior with other pages) ───────────────────────

function showLoading() {
  const spinner = document.getElementById("spinnerLoading");
  if (spinner) spinner.style.visibility = "visible";
}

function hideLoading() {
  const spinner = document.getElementById("spinnerLoading");
  if (spinner) spinner.style.visibility = "hidden";
}

document.addEventListener("DOMContentLoaded", hideLoading);

window.addEventListener("pageshow", function (event) {
  if (event.persisted) hideLoading();
});
