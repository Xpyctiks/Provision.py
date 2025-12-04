document.addEventListener("DOMContentLoaded", function () {
    const modalElement = document.getElementById("myModal");
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
});

document.addEventListener('show.bs.collapse', async function (event) {
    let button = event.target.previousElementSibling.querySelector("button");
    let path = button.dataset.path;
    let body = event.target.querySelector(".accordion-body");
    body.innerHTML = "Завантажую...";
    let response = await fetch(`/action?showstructure=${encodeURIComponent(path)}`);
    let html = await response.text();
    body.innerHTML = html;
});

document.getElementById("closeAll").addEventListener("click", function () {
    document.querySelectorAll(".accordion .collapse.show").forEach(el => {
        let bsCollapse = bootstrap.Collapse.getInstance(el);
        if (!bsCollapse) {
        bsCollapse = new bootstrap.Collapse(el, { toggle: false });
        }
        bsCollapse.hide();
    });
});

function showLoading() {
    document.getElementById("spinnerLoading").style.visibility = "visible";
}

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("spinnerLoading").style.visibility = "hidden";
});
