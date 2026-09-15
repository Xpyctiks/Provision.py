document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

// ── Cookie helpers (persist selected account across reloads) ────────────────

function setCookie(name, value, days) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/; SameSite=Lax';
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

(function restoreSelectedAccount() {
  const saved = getCookie('provision_cf_account');
  if (!saved) return;
  const item = document.querySelector('.dropdown-item.account[data-value="' + CSS.escape(saved) + '"]');
  if (!item) return;
  document.getElementById('selected_account').value = saved;
  document.getElementById('Account').innerText = saved;
})();

document.querySelectorAll('.dropdown-item.account').forEach(item => {
  item.addEventListener('click', function () {
    const value = this.getAttribute('data-value');
    document.getElementById('selected_account').value = value;
    document.getElementById('Account').innerText = value;
    setCookie('provision_cf_account', value, 365);
  });
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

// ── Loading the domain list for the selected account ─────────────────────────

document.getElementById("buttonShowCacheDomains").addEventListener("click", function () {
  const card = document.getElementById("cacheDomainsCard");
  const container = document.getElementById("cacheDomainsContainer");
  card.style.display = "";
  container.innerHTML = `
  <div class="text-center py-3">
    <div class="spinner-border" role="status"></div>
    <div>Завантаження...</div>
  </div>`;
  showLoading();

  const formData = new FormData();
  formData.append("selected_account", document.getElementById("selected_account").value);
  fetch("/cloudflare_cache/domains/", {
    method: "POST",
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    container.innerHTML = data.message;
    hideLoading();
  })
  .catch(error => {
    container.innerHTML = `<div class="alert alert-danger">Помилка: ${error}</div>`;
    hideLoading();
  });
});

// ── Bulk selection (select-all + submit button state) ────────────────────────

function updateBulkPurgeState() {
  const checkedCount = document.querySelectorAll("#cacheDomainsContainer .cache-domain-check:checked").length;
  const btn = document.getElementById("bulkPurgeBtn");
  const countSpan = document.getElementById("bulkPurgeCount");
  if (btn) btn.disabled = checkedCount === 0;
  if (countSpan) countSpan.textContent = checkedCount;
}

document.addEventListener("change", function (e) {
  if (e.target.id === "selectAllCacheDomains") {
    document.querySelectorAll("#cacheDomainsContainer .cache-domain-check").forEach(function (cb) {
      cb.checked = e.target.checked;
    });
    updateBulkPurgeState();
  } else if (e.target.classList.contains("cache-domain-check")) {
    if (!e.target.checked) {
      const selectAll = document.getElementById("selectAllCacheDomains");
      if (selectAll) selectAll.checked = false;
    }
    updateBulkPurgeState();
  }
});

// ── Confirmation dialogs before purging (individual and bulk) ────────────────

document.addEventListener("submit", function (e) {
  const btn = e.submitter;
  if (btn && btn.classList.contains("purgeCache-btn")) {
    if (!confirm(`⚠Очистити кеш Cloudflare для домену "${btn.value}"?`)) {
      e.preventDefault();
    }
    return;
  }
  if (btn && btn.id === "bulkPurgeBtn") {
    const count = document.querySelectorAll("#cacheDomainsContainer .cache-domain-check:checked").length;
    if (!confirm(`⚠Очистити кеш Cloudflare для ${count} обраних доменів?`)) {
      e.preventDefault();
    }
  }
});

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
})
