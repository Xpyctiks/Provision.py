document.querySelectorAll('.dropdown-item.template').forEach(item => {
    item.addEventListener('click', function () {
        let value = this.getAttribute('data-value');
        document.getElementById('selected_template').value = value;
        document.getElementById('Template').innerText = value;
    });
}); 

document.querySelectorAll('.dropdown-item.account').forEach(item => {
    item.addEventListener('click', function () {
        let value2 = this.getAttribute('data-value');
        document.getElementById('selected_account').value = value2;
        document.getElementById('Account').innerText = value2;
    });
}); 

document.querySelectorAll('.dropdown-item.server').forEach(item => {
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

document.getElementById('postform').addEventListener('submit', function (e) {
    let account = document.getElementById('selected_account');
    let template = document.getElementById('selected_template');
    let server = document.getElementById('selected_server');
    if (!account.value) {
        account.setCustomValidity("invalid");
    } else {
        account.setCustomValidity("");
    }
    if (!template.value) {
        template.setCustomValidity("invalid");
    } else {
        template.setCustomValidity("");
    }
    if (!server.value) {
        server.setCustomValidity("invalid");
    } else {
        server.setCustomValidity("");
    }
    if (!this.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
    }
    this.classList.add('was-validated');
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
    fetch("/validate", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("modalResultBody").innerHTML =
            `<div class="alert alert-info">${data.message}</div>`;
        modal.show();
    })
    .catch(error => {
        document.getElementById("modalResultBody").innerHTML =
            `<div class="alert alert-danger">Ошибка: ${error}</div>`;
        modal.show();
    });
});

document.getElementById("postform").addEventListener("submit", function(event) {
const input = document.getElementById("fileUpload");
const value = input.value.trim();
if (value === "") {
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
    event.preventDefault();
} else {
    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
}
});