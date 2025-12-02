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
  let field = document.getElementById('selected_account');
  if (!field.value) {
    field.classList.add('is-invalid');
    e.preventDefault();
    e.stopPropagation();
  } else {
    field.classList.remove('is-invalid');
  }
});
