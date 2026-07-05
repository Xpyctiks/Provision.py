document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

document.querySelectorAll('.dropdown-item.account').forEach(item => {
  item.addEventListener('click', function () {
    let value2 = this.getAttribute('data-value');
    document.getElementById('selected_account').value = value2;
    document.getElementById('Account').innerText = value2;
    const dnsAccount = document.getElementById('dns_account');
    if (dnsAccount) {
      dnsAccount.value = value2;
      loadDnsDomains(value2);
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
  }
  const recordType = document.getElementById('recordType');
  if (recordType) {
    recordType.addEventListener('change', function () {
      const type = this.value;
      document.getElementById('priorityWrapper').style.display = (type === 'MX') ? 'block' : 'none';
      document.getElementById('proxiedWrapper').style.display = (['A', 'AAAA', 'CNAME'].includes(type)) ? 'flex' : 'none';
    });
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
