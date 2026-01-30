document.addEventListener("DOMContentLoaded", function() {
    const isVirtualCheckbox = document.querySelector("#id_is_virtual");
    const virtualUrlWrapper = document.querySelector("#div_id_virtual_url");

    function toggleVirtualFields() {
        if (isVirtualCheckbox.checked) {
            virtualUrlWrapper.style.display = "block";
        } else {
            virtualUrlWrapper.style.display = "none";
        }
    }

    toggleVirtualFields();

    isVirtualCheckbox.addEventListener("change", toggleVirtualFields);
});