document.addEventListener('DOMContentLoaded', function () {
    showAllBootstrapToasts();
});

function showAllBootstrapToasts() {
    const toasts = document.querySelectorAll('.toast');

    for (const toast of toasts) {
        const toastInstance = new bootstrap.Toast(toast);
        toastInstance.show();
    }
}