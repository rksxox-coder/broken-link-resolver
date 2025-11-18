const dropArea = document.getElementById("drop-area");
const fileInput = document.getElementById("file-input");

// Click to open file browser
dropArea.addEventListener("click", () => fileInput.click());

// Highlight on drag
dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("dragover");
});

// Remove highlight
dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("dragover");
});

// Handle drop
dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        dropArea.innerHTML = "File Selected: " + files[0].name;
    }
});
