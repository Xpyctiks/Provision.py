document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

document.querySelectorAll('.dropdown-item.Account').forEach(item => {
  item.addEventListener('click', function () {
    let value2 = this.getAttribute('data-value');
    document.getElementById('selected_account').value = value2;
    document.getElementById('Account').innerText = value2;
  });
}); 

document.querySelectorAll('.dropdown-item.Server').forEach(item => {
  item.addEventListener('click', function () {
    let value2 = this.getAttribute('data-value');
    document.getElementById('selected_server').value = value2;
    document.getElementById('Server').innerText = value2;
  });
});

document.getElementById("postform").addEventListener("submit", function(event) {
  const input = document.getElementById("domain");
  const value = input.value.trim();
  if (value === "") {
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
    document.getElementById("spinnerLoading").style.visibility = "hidden";
    event.preventDefault();
  } else {
    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
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

document.getElementById("Validate").addEventListener("click", function () {
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
  formData.append("selected_server", document.getElementById("selected_server").value);
  const checkbox = document.getElementById("not-a-subdomain");
  formData.append("not-a-subdomain", checkbox.checked ? "1" : "0");
  fetch("/validate/", {
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
