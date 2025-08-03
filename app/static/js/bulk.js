// Bulk upload and generation handling
$(document).ready(function() {
    $('#bulkFile').change(function() {
        if (this.files.length > 0) {
            uploadBulkFile();
        }
    });
    
    $('#generateBulkBtn').click(function() {
        generateBulkVisualizers();
    });
    
    $('#selectAll').click(function() {
        $('#languageCheckboxes input[type="checkbox"]').prop('checked', true);
    });
    
    $('#selectNone').click(function() {
        $('#languageCheckboxes input[type="checkbox"]').prop('checked', false);
    });
});

function uploadBulkFile() {
    const formData = new FormData();
    const fileInput = document.getElementById('bulkFile');
    formData.append('file', fileInput.files[0]);
    
    showBulkProgress(0, 'Uploading file...');
    
    $.ajax({
        url: '/bulk/upload',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                displayLanguageSelection(response);
                hideBulkProgress();
            } else {
                alert('Error: ' + response.error);
                hideBulkProgress();
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Upload failed';
            alert('Error: ' + error);
            hideBulkProgress();
        }
    });
}

function displayLanguageSelection(data) {
    // Show detected info
    $('#bulkDetectedInfo').html(`
        <strong>✅ File processed successfully!</strong><br>
        📊 ${data.total_entries} total entries<br>
        🔑 String ID: <code>${data.str_id_col}</code><br>
        🇬🇧 Source: <code>${data.source_col}</code><br>
        🌍 ${data.languages_count} target languages detected
    `);
    
    // Create checkboxes for each language
    const checkboxContainer = $('#languageCheckboxes');
    checkboxContainer.empty();
    
    data.target_languages.forEach(function(lang) {
        checkboxContainer.append(`
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${lang}" id="lang_${lang}" checked>
                <label class="form-check-label" for="lang_${lang}">
                    ${lang}
                </label>
            </div>
        `);
    });
    
    // Show the language selection section
    $('#bulkLanguageSelection').show();
    
    // Update preview
    $('#bulkWelcomeContent').hide();
    $('#bulkPreviewContent').show();
    
    $('#bulkFileStats').html(`
        <div class="col-md-3">
            <div class="stat-card">
                <h6>📊 Total Entries</h6>
                <span class="stat-number">${data.total_entries.toLocaleString()}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card">
                <h6>🌍 Languages</h6>
                <span class="stat-number">${data.languages_count}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card">
                <h6>🔑 ID Column</h6>
                <span class="stat-text">${data.str_id_col}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stat-card">
                <h6>🇬🇧 Source</h6>
                <span class="stat-text">${data.source_col}</span>
            </div>
        </div>
    `);
}

function generateBulkVisualizers() {
    // Get selected languages
    const selectedLanguages = [];
    $('#languageCheckboxes input[type="checkbox"]:checked').each(function() {
        selectedLanguages.push($(this).val());
    });
    
    if (selectedLanguages.length === 0) {
        alert('Please select at least one language to generate visualizers for.');
        return;
    }
    
    showBulkProgress(0, `Generating visualizers for ${selectedLanguages.length} language(s)...`);
    
    $.ajax({
        url: '/bulk/generate',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            selectedLanguages: selectedLanguages
        }),
        xhrFields: {
            responseType: 'blob'
        },
        success: function(data, status, xhr) {
            // Handle ZIP file download
            const blob = new Blob([data], { type: 'application/zip' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get filename from response header
            const contentDisposition = xhr.getResponseHeader('Content-Disposition');
            let filename = 'bulk_visualizers.zip';
            if (contentDisposition) {
                const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (matches && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            hideBulkProgress();
            // alert(`✅ Successfully generated ${selectedLanguages.length} visualizers!`);
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Generation failed';
            alert('Error: ' + error);
            hideBulkProgress();
        }
    });
}

function showBulkProgress(percent, message) {
    $('#bulkProgressContainer').show();
    $('#bulkProgressBar').css('width', percent + '%');
    $('#bulkStatusText').text(message);
}

function hideBulkProgress() {
    $('#bulkProgressContainer').hide();
}
