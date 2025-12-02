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
    document.getElementById("spinnerLoading").style.visibility = "visible";
}

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("spinnerLoading").style.visibility = "hidden";
});

function deleteLoading() {
    document.getElementById("spinnerLoading").className = "spinner-border text-danger";
    document.getElementById("spinnerLoading").style.visibility = "visible";
}

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
