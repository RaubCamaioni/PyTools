const dropArea = document.getElementById('drop-area');
const uploadForm = document.getElementById('upload-form');
const fileElem = document.getElementById('fileElem');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false)
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => highlight(dropArea), false)
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => unhighlight(dropArea), false)
});

function highlight(e) {
    e.classList.add('highlight');
}

function unhighlight(e) {
    e.classList.remove('highlight');
}

dropArea.addEventListener('drop', handleDrop, false);
dropArea.addEventListener('click', () => fileElem.click());

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFiles(files) {
    files = [...files];
    files.forEach(uploadFile);
}

function uploadFile(file) {
    const url = uploadForm.action;
    const formData = new FormData();
    formData.append('files', file);

    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error converting file');
        }

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'download.zip';

        if (contentDisposition && contentDisposition.indexOf('attachment') !== -1) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch.length === 2) {
                filename = filenameMatch[1];
            }
        }

        return response.blob().then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        });
    })
    .catch(() => { });
}
