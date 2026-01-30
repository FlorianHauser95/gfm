document.addEventListener("DOMContentLoaded", () => {

    const groupInputs = document.querySelectorAll('input[id^="id_groups_field_"]');
    const studentBlocks = document.querySelectorAll(".student-only");

    function isStudentSelected() {
        let selected = false;
        for (const group of groupInputs) {
            if (group.checked && group.value === "student") {
                selected = true;
            }
        }
        return selected;
    }

    function toggleStudentFields() {
        const show = isStudentSelected();
        studentBlocks.forEach(el => el.classList.toggle("hidden", !show));
    }

    toggleStudentFields();
    groupInputs.forEach(cb => cb.addEventListener("change", toggleStudentFields));
});
