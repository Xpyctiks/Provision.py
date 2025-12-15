document.addEventListener("DOMContentLoaded", function () {
    const modalElement = document.getElementById("myModal");
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }

    document.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", e => {
        const mainSite = btn.dataset.site;
        const selectedSites = Array.from(
            document.querySelectorAll(".selected-site:checked")
        ).map(chk => chk.value);
        if (!selectedSites.includes(mainSite)) {
            selectedSites.push(mainSite);
        }
        const sitesList = selectedSites.join(", ");
        if (!confirm(
            `Ви дійсно хочете видалити наступні сайти?\n\n${sitesList}`
        )) {
            e.preventDefault();
            }
        });
    });

    document.querySelectorAll(".gitpull-btn").forEach(btn => {
    btn.addEventListener("click", e => {
        const mainSite = btn.dataset.site;
        const selectedSites = Array.from(
            document.querySelectorAll(".selected-site:checked")
        ).map(chk => chk.value);
        if (!selectedSites.includes(mainSite)) {
            selectedSites.push(mainSite);
        }
        const sitesList = selectedSites.join(", ");
        if (!confirm(
            `Оновити код до актуального на наступних сайтах?\n\n${sitesList}`
        )) {
            e.preventDefault();
            }
        });
    });
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

window.addEventListener("pageshow", function (event) {
    if (event.persisted) {
        resetLoadingState();
    }
});

function resetLoadingState() {
    const loader = document.getElementById("loader");
    loader.classList.remove("active");
}

const checkboxes = document.querySelectorAll('.chk');
let lastChecked = null;
checkboxes.forEach(chk => {
    chk.addEventListener('click', function (e) {
    if (e.shiftKey && lastChecked) {
        let inRange = false;
        checkboxes.forEach(box => {
        if (box === this || box === lastChecked) {
            inRange = !inRange;
        }
        if (inRange) {
            box.checked = lastChecked.checked;
        }
        });
    }
    lastChecked = this;
    });
});

function checkAll(bx) {
    var cbs = document.getElementsByTagName('input');
    for(var i=0; i < cbs.length; i++) {
    if(cbs[i].type == 'checkbox') {
        cbs[i].checked = bx.checked;
    }
    }
}
