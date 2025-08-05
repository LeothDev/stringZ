// Update range sliders
document.getElementById('similarityThreshold').addEventListener('input', function(e) {
  document.getElementById('thresholdValue').textContent = e.target.value;
});

document.getElementById('maxClusterSize').addEventListener('input', function(e) {
  document.getElementById('clusterValue').textContent = e.target.value;
});

document.getElementById('minSubstringLength').addEventListener('input', function(e) {
  document.getElementById('substringValue').textContent = e.target.value;
});

// File upload handling
document.getElementById('file').addEventListener('change', function(e) {
  if (e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
  }
});

function uploadFile(file) {
  console.log('=== UPLOAD DEBUG ===');
  console.log('File:', file);

  const formData = new FormData();
  formData.append('file', file);

  console.log('About to call showProgress...');

  try {
      showProgress('📤 Uploading file...');
      console.log('showProgress called successfully');
  } catch (error) {
      console.error('Error in showProgress:', error);
      return;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000)
  fetch('/upload', {
      method: 'POST',
      body: formData,
      signal: controller.signal
  })
  .then(response => {
      clearTimeout(timeoutId);
      console.log('Response received:', response);
      if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
  })
  .then(data => {
      console.log('Data received:', data);
      hideProgress();
      if (data.success) {
          showLanguageSelection(data);
      } else {
          alert('Error: ' + data.error);
      }
  })
  .catch(error => {
      clearTimeout(timeoutId);
      console.error('Fetch error details:', error);
      hideProgress();

      let errorMessage = 'Upload failed: ';
      if (error.name === 'AbortError') {
          errorMessage += 'Request timed out';
      } else if (error.message.includes('Failed to fetch')) {
          errorMessage += 'Cannot connect to server';
      } else {
          errorMessage += error.message;
      }
      alert(errorMessage);
  });
}

function showLanguageSelection(data) {
  // Make sure the language selection div is visible first
  const languageSelectionDiv = document.getElementById('languageSelection');
  if (languageSelectionDiv) {
      languageSelectionDiv.style.display = 'block';
  }

  // Display which languages were found 
  const detectedColumns = document.getElementById('detectedColumns');
  if (detectedColumns) {
      detectedColumns.innerHTML = 
          `✅ Detected: <strong>${data.str_id_col}</strong> (ID) + <strong>${data.source_col}</strong> (Source)`;
  }

  const select = document.getElementById('targetLanguage');
  if (select) {
      select.innerHTML = '';
      data.lang_columns.forEach(lang => {
          const option = document.createElement('option');
          option.value = lang;
          option.textContent = lang;
          select.appendChild(option);
      });
  }
}

function showProgress(message) {
  console.log('showProgress called with:', message);
  const statusText = document.getElementById('statusText');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');

  console.log('Elements found:', {statusText, progressContainer, progressBar});

  if (statusText) statusText.textContent = message;
  if (progressContainer) progressContainer.style.display = 'block';
  if (progressBar) progressBar.style.width = '50%';
}

function hideProgress() {
  document.getElementById('progressContainer').style.display = 'none';
}

// Load Data button handler
document.getElementById('loadDataBtn').addEventListener('click', function() {
  const targetLanguage = document.getElementById('targetLanguage').value;

  showProgress('📊 Loading data...');

  fetch('/load_data', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          targetLanguage: targetLanguage
      })
  })
  .then(response => response.json())
  .then(data => {
      hideProgress();
      if (data.success) {
          showDataPreview(data);
          showProcessingOptions();
      } else {
          alert('Error: ' + data.error);
      }
  })
  .catch(error => {
      hideProgress();
      alert('Load failed: ' + error.message);
  });
});

function showDataPreview(data) {
  // Hide welcome content and show preview
  <!-- console.log('Hiding welcome content...') -->
  document.getElementById('welcomeContent').style.display = 'none';
  <!-- console.log('Showing preview content...') -->
  document.getElementById('previewContent').style.display = 'block';

  // Show stats
  const statsHtml = `
      <div class="row text-center">
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Total Entries</div>
                  <div class="metric-value">${data.stats.total_entries}</div>
              </div>
          </div>
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Duplicate Groups</div>
                  <div class="metric-value">${data.stats.duplicate_groups}</div>
              </div>
          </div>
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Completion Rate</div>
                  <div class="metric-value">${data.stats.completion_rate}</div>
              </div>
          </div>
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Avg Length</div>
                  <div class="metric-value">${data.stats.avg_length}</div>
              </div>
          </div>
      </div>
  `;
  document.getElementById('fileStats').innerHTML = statsHtml;

  // Show preview table
  let tableHtml = `
      <div class="table-responsive">
          <table class="table table-striped">
              <thead>
                  <tr>
                      <th>ID</th>
                      <th>${data.source_lang}</th>
                      <th>${data.target_lang}</th>
                  </tr>
              </thead>
              <tbody>
  `;

  data.preview_data.forEach(row => {
      tableHtml += `
          <tr>
              <td><code>${row.strId}</code></td>
              <td>${row.source}</td>
              <td>${row.target}</td>
          </tr>
      `;
  });

  tableHtml += `
              </tbody>
          </table>
      </div>
      <p class="text-muted">Showing first 10 of ${data.stats.total_entries} entries</p>
  `;

  document.getElementById('previewTable').innerHTML = tableHtml;
}

function showProcessingOptions() {
  document.getElementById('processingOptions').style.display = 'block';
}

// Process form handler
document.getElementById('uploadForm').addEventListener('submit', function(e) {
  e.preventDefault();

  // Get form data
  const formData = new FormData(e.target);
  const processData = {
      removeDuplicates: formData.get('removeDuplicates') === 'on',
      sortByCorrelation: formData.get('sortByCorrelation') === 'on',
      correlationStrategy: formData.get('correlationStrategy'),
      similarityThreshold: parseFloat(formData.get('similarityThreshold')),
      maxClusterSize: parseInt(formData.get('maxClusterSize')),
      minSubstringLength: parseInt(formData.get('minSubstringLength'))
  };

  showProgress('🚀 Processing file...');
  updateProgressBar(20);

  fetch('/process', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify(processData)
  })
  .then(response => response.json())
  .then(data => {
      updateProgressBar(100);
      setTimeout(() => {
          hideProgress();
          if (data.success) {
              showProcessingResults(data.stats);
              // Redirect to results page after showing success
              setTimeout(() => {
                  window.location.href = '/results';
              }, 2000);
          } else {
              alert('Error: ' + data.error);
          }
      }, 500);
  })
  .catch(error => {
      hideProgress();
      alert('Processing failed: ' + error.message);
  });
});

function updateProgressBar(percentage) {
  document.getElementById('progressBar').style.width = percentage + '%';
}

function showProcessingResults(stats) {
  const resultsHtml = `
      <div class="alert alert-success">
          <h5>✅ Processing Completed!</h5>
          <ul class="mb-0">
              <li><strong>${stats.original_count}</strong> → <strong>${stats.final_count}</strong> entries</li>
              <li><strong>${stats.duplicates_removed}</strong> duplicates removed</li>
              <li><strong>${stats.clusters_created}</strong> similarity clusters created</li>
              <li><strong>${stats.word_count}</strong> words to translate</li>
              <li>Completed in <strong>${stats.processing_time}</strong></li>
          </ul>
          <p class="mt-2 mb-0">Redirecting to results...</p>
      </div>
  `;

  document.getElementById('previewContent').innerHTML = resultsHtml;
}
