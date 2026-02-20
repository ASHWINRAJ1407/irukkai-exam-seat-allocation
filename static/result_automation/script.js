// Minimal JS for file upload UX used by mark analysis page
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const form = document.getElementById('markAnalysisForm');
    const progress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadProgressBar');
    const generateBtn = document.getElementById('generateBtn');

    const showPreview = () => {
        filePreview.innerHTML = '';
        const files = fileInput.files;
        if(!files || files.length === 0){
            filePreview.innerHTML = '<div class="alert alert-info alert-sm py-2 mb-0" role="alert"><i class="bi bi-info-circle me-2"></i>No files selected</div>';
            return;
        }
        const preview = document.createElement('div');
        preview.className = 'alert alert-light border py-2 mb-0';
        preview.innerHTML = '<div class="small"><strong>Selected Files:</strong></div>';
        const ul = document.createElement('ul');
        ul.className = 'mb-0 mt-1 ms-3';
        for(let i=0; i<files.length; i++){
            const f = files[i];
            const li = document.createElement('li');
            li.className = 'small text-truncate';
            li.innerHTML = `<i class="bi bi-file-pdf me-2 text-danger"></i>${f.name} (${Math.round(f.size/1024)} KB)`;
            ul.appendChild(li);
        }
        preview.appendChild(ul);
        filePreview.appendChild(preview);
    };

    fileInput.addEventListener('change', () => {
        showPreview();
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const examType = document.querySelector('input[name="exam_type"]:checked');
        const collegeName = document.querySelector('input[name="college_name"]').value.trim();
        const files = fileInput.files;
        
        if(!examType) {
            alert('Please select an exam type (IA1 / IA2 / MODEL)');
            return;
        }
        
        if(!collegeName) {
            alert('Please enter a college/institute name');
            return;
        }
        
        if(!files || files.length === 0){
            alert('Please select at least one PDF file');
            return;
        }

        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Processing...';

        // prepare form data
        const fd = new FormData(form);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', form.action || window.location.pathname);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.upload.addEventListener('progress', (ev) => {
            if(ev.lengthComputable){
                const pct = Math.round((ev.loaded/ev.total)*100);
                progress.style.display = 'block';
                progressBar.style.width = pct + '%';
                progressBar.textContent = pct + '%';
            }
        });

        xhr.onreadystatechange = function(){
            if(xhr.readyState === 4){
                progress.style.display = 'none';
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="bi bi-play-circle me-2"></i>Generate Report';
                
                if(xhr.status >= 200 && xhr.status < 300){
                    try {
                        const res = JSON.parse(xhr.responseText);
                        if(res.success){
                            // Show success message
                            const alertDiv = document.createElement('div');
                            alertDiv.className = 'alert alert-success alert-dismissible fade show mt-3';
                            alertDiv.innerHTML = `
                                <i class="bi bi-check-circle me-2"></i>
                                <strong>Success!</strong> ${res.message || 'Report generated successfully!'}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            `;
                            form.parentElement.insertBefore(alertDiv, form);
                            
                            // Refresh generated reports list with files from response
                            if(typeof initializeGeneratedReports === 'function') {
                                initializeGeneratedReports(res.files || []);
                            }
                            
                            // Reset form
                            form.reset();
                            filePreview.innerHTML = '';
                            
                            // Auto-close alert after 5 seconds
                            setTimeout(() => {
                                if(alertDiv.parentElement) {
                                    alertDiv.remove();
                                }
                            }, 5000);
                        } else {
                            const alertDiv = document.createElement('div');
                            alertDiv.className = 'alert alert-warning alert-dismissible fade show mt-3';
                            alertDiv.innerHTML = `
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                <strong>Processing Failed</strong> ${res.message || 'Unable to generate report'}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            `;
                            form.parentElement.insertBefore(alertDiv, form);
                        }
                    } catch(e){
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
                        alertDiv.innerHTML = `
                            <i class="bi bi-x-circle me-2"></i>
                            <strong>Error</strong> Server returned unexpected response
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        `;
                        form.parentElement.insertBefore(alertDiv, form);
                    }
                } else {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
                    alertDiv.innerHTML = `
                        <i class="bi bi-x-circle me-2"></i>
                        <strong>Upload Failed</strong> Status ${xhr.status}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    form.parentElement.insertBefore(alertDiv, form);
                }
            }
        };

        // append files explicitly (some browsers may not include file inputs in FormData automatically)
        for(let i=0;i<files.length;i++){
            fd.append('files', files[i], files[i].name);
        }

        xhr.send(fd);
    });
});
