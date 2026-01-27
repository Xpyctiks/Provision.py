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

function copyText(elementId) {
  const text = document.getElementById(elementId).innerText;
  navigator.clipboard.writeText(text).then(() => {
    alert("Скопійовано в буфер обміну!");
  }).catch(err => {
    console.error("Помилка копіювання:", err);
  });
}

document.addEventListener("submit", function (e) {
  const btn = e.submitter;

  if (btn && btn.classList.contains("delDomain-btn")) {
    if (!confirm("Видалити цей домен з аккаунту?")) {
      e.preventDefault();
    }
  }
});

