// static/script.js

function showLoader() {
    document.getElementById("loader").classList.remove("hidden");
}

// Drag & drop logic
let dropArea = document.getElementById("drop-area");
let fileInput = document.getElementById("fileElem");

dropArea.addEventListener("click", () => fileInput.click());

dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("border-blue-400");
});

dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("border-blue-400");
});

dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("border-blue-400");

    fileInput.files = e.dataTransfer.files;
    dropArea.innerHTML = `<p class="text-green-400">Selected: ${fileInput.files[0].name}</p>`;
});

function prepareCSV() {
    const results = {{ results | tojson | safe }};
    document.getElementById("resultsData").value = JSON.stringify(results);
}
