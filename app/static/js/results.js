// Load page data when ready
document.addEventListener('DOMContentLoaded', function() {
  loadPageData();
  loadReviewData();
});

function loadPageData() {
  fetch('/api/page_data')
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              updateMetrics(data.stats);
              updateSidebar(data.quick_stats);
          }
      })
      .catch(error => console.error('Error loading page data:', error));
}

function updateMetrics(stats) {
  const metricsHtml = `
      <div class="row text-center">
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Original Entries</div>
                  <div class="metric-value">${stats.original_count}</div>
              </div>
          </div>
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Final Entries</div>
                  <div class="metric-value">${stats.final_count}</div>
              </div>
          </div>
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Duplicates Removed</div>
                  <div class="metric-value">${stats.duplicates_removed}</div>
              </div>
          </div>
          <div class="col-md-3">
              <div class="metric-item">
                  <div class="metric-label">Groups Created</div>
                  <div class="metric-value">${stats.clusters_created}</div>
              </div>
          </div>
      </div>
  `;
  document.getElementById('metricsRow').innerHTML = metricsHtml;
}

function updateSidebar(stats) {
  const filename = stats.original_filename || "Unknown"
  const sidebarHtml = `
      <p><strong>${filename}</strong></p>
      <p><strong>📝 ${stats.total_entries}</strong> entries</p>
      <p><strong>🌍 ${stats.source_lang}</strong> → <strong>${stats.target_lang}</strong></p>
      <p><strong>✅ ${stats.completion_rate}</strong> completion</p>
  `;
  document.getElementById('quickStats').innerHTML = sidebarHtml;
}

// Download handlers
document.getElementById('downloadVisualizer').addEventListener('click', function() {
  window.location.href = '/download/visualizer';
});

document.getElementById('downloadSpreadsheet').addEventListener('click', function() {
  window.location.href = '/download/spreadsheet';
});

// Review tab functionality
let reviewTable;

function loadReviewData(search = '', filter = 'all', page = 1, perPage = '100') {
  const params = new URLSearchParams({
      search: search,
      filter: filter,
      page: page,
      per_page: perPage
  });

  fetch(`/api/review_data?${params}`)
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              updateReviewTable(data);
              updateReviewStats(data.stats);
          } else {
              console.error('Error loading review data:', data.error);
          }
      })
      .catch(error => console.error('Error loading review data:', error));
}

function updateReviewTable(data) {
  // Destroy existing table if it exists to keep localStorage clean
  if (reviewTable) {
      reviewTable.destroy();
  }

  // Create table HTML
  const tableHtml = `
      <thead>
          <tr>
              <th>ID</th>
              <th>${data.columns.source_lang}</th>
              <th>${data.columns.target_lang}</th>
              <th>Occurrences</th>
          </tr>
      </thead>
      <tbody>
          ${data.data.map(row => `
              <tr>
                  <td><code>${row.strId}</code></td>
                  <td>${row.source}</td>
                  <td>${row.target}</td>
                  <td class="text-center">
                      <span class="badge ${row.occurrences > 5 ? 'bg-warning' : 'bg-secondary'}">
                          ${row.occurrences}
                      </span>
                  </td>
              </tr>
          `).join('')}
      </tbody>
  `;

  document.getElementById('reviewTable').innerHTML = tableHtml;

  // Initialize DataTable
  reviewTable = $('#reviewTable').DataTable({
      paging: false,
      searching: false,
      ordering: false,
      info: false,
      columnDefs: [
          { width: "60px", targets: 0 },
          { width: "80px", targets: 3, className: "text-center" }
      ]
  });   
}

function updateReviewStats(stats) {
  // For future self: use this for debugs on the reviews
  console.log('Review stats:', stats);
}

// Event handlers for review controls
document.getElementById('reviewSearch').addEventListener('input', function(e) {
  clearTimeout(this.searchTimeout);
  this.searchTimeout = setTimeout(() => {
      loadReviewData(e.target.value, document.getElementById('reviewFilter').value);
  }, 500);
});

document.getElementById('reviewFilter').addEventListener('change', function(e) {
  loadReviewData(document.getElementById('reviewSearch').value, e.target.value);
});

document.getElementById('reviewPerPage').addEventListener('change', function(e) {
  loadReviewData(
      document.getElementById('reviewSearch').value,
      document.getElementById('reviewFilter').value,
      1,
      e.target.value
  );
});

// Load review data when tab is shown
document.getElementById('review-tab').addEventListener('shown.bs.tab', function() {
  if (!reviewTable) {
      loadReviewData();
  }
});

// Validation functionality
document.getElementById('runValidation').addEventListener('click', function() {
  const button = this;
  const originalText = button.innerHTML;

  // Show loading state
  button.innerHTML = '🔄 Running Validation...';
  button.disabled = true;

  fetch('/api/run_validation', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      }
  })
  .then(response => response.json())
  .then(data => {
      button.innerHTML = originalText;
      button.disabled = false;
    
      if (data.success) {
          showValidationResults(data);
      } else {
          alert('Validation failed: ' + data.error);
      }
  })
  .catch(error => {
      button.innerHTML = originalText;
      button.disabled = false;
      alert('Validation failed: ' + error);
  });
});

function showValidationResults(data) {
  const resultsContainer = document.getElementById('validationResults');

  if (data.summary.issues_found === 0) {
      resultsContainer.innerHTML = `
          <div class="alert alert-success mt-4">
              <h5>No validation issues found!</h5>
              <p class="mb-0">All ${data.summary.total_strings} strings passed validation.</p>
          </div>
      `;
  } else {
      let resultsHtml = `
          <div class="mt-4">
              <h6>📊 Validation Summary</h6>
              <div class="row mb-3">
                  <div class="col-md-3">
                      <div class="card text-center">
                          <div class="card-body">
                              <h5>${data.summary.total_strings}</h5>
                              <small>Total Strings</small>
                          </div>
                      </div>
                  </div>
                  <div class="col-md-3">
                      <div class="card text-center">
                          <div class="card-body">
                              <h5>${data.summary.issues_found}</h5>
                              <small>Issues Found</small>
                          </div>
                      </div>
                  </div>
                  <div class="col-md-3">
                      <div class="card text-center border-danger">
                          <div class="card-body">
                              <h5 class="text-danger">${data.summary.critical_issues}</h5>
                              <small>Critical Issues</small>
                          </div>
                      </div>
                  </div>
                  <div class="col-md-3">
                      <div class="card text-center border-warning">
                          <div class="card-body">
                              <h5 class="text-warning">${data.summary.warnings}</h5>
                              <small>Warnings</small>
                          </div>
                      </div>
                  </div>
              </div>
    
              <div class="row mb-3">
                  <div class="col-md-6">
                      <h6>🔍 Issue Details</h6>
                  </div>
                  <div class="col-md-6 text-end">
                      <button class="btn btn-sm btn-outline-secondary me-2" onclick="filterValidationIssues('all')">All Issues</button>
                      <button class="btn btn-sm btn-outline-danger me-2" onclick="filterValidationIssues('critical')">Critical Only</button>
                      <button class="btn btn-sm btn-outline-warning" onclick="filterValidationIssues('warning')">Warnings Only</button>
                  </div>
              </div>
              <div id="validationIssuesList">
      `;        

      // LQA Validation "categorization"
      data.issues.forEach((issue, index) => {
          const severityClass = issue.severity === 'CRITICAL' ? 'danger' : 'warning';
          const severityIcon = issue.severity === 'CRITICAL' ? '🚨' : '⚠️';
          const severityBadge = issue.severity === 'CRITICAL' ? 'bg-danger' : 'bg-warning';
        
        resultsHtml += `
            <div class="card mb-2 validation-issue" data-severity="${issue.severity.toLowerCase()}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <button class="btn btn-link text-${severityClass}" type="button" data-bs-toggle="collapse" data-bs-target="#issue${index}">
                            ${severityIcon} ${issue.str_id} - ${issue.type}
                        </button>
                    </h6>
                    <span class="badge ${severityBadge}">${issue.severity}</span>
                </div>
                <div id="issue${index}" class="collapse">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-2"><strong>String ID:</strong></div>
                            <div class="col-md-10"><code>${issue.str_id}</code></div>
                        </div>
                        <div class="row">
                            <div class="col-md-2"><strong>Issue:</strong></div>
                            <div class="col-md-10">${issue.type} - ${issue.detail}</div>
                        </div>
                        <div class="row">
                            <div class="col-md-2"><strong>English:</strong></div>
                            <div class="col-md-10"><code>${issue.en_text}</code></div>
                        </div>
                        <div class="row">
                            <div class="col-md-2"><strong>${data.target_lang}:</strong></div>
                            <div class="col-md-10"><code>${issue.target_text}</code></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
      });
    
      resultsHtml += '</div>';
      resultsContainer.innerHTML = resultsHtml;
  }

  resultsContainer.style.display = 'block';
}

function filterValidationIssues(type) {
  const issues = document.querySelectorAll('.validation-issue');
  issues.forEach(issue => {
      if (type === 'all' || issue.dataset.severity === type) {
          issue.style.display = 'block';
      } else {
          issue.style.display = 'none';
      }
  });
}

// String Comparison
document.getElementById('compareStrings').addEventListener('click', function() {
  const string1 = document.getElementById('string1').value;
  const string2 = document.getElementById('string2').value;

  if (!string1 || !string2) {
      alert('Please enter both strings to compare');
      return;
  }

  compareStrings(string1, string2);
});

document.getElementById('clearComparison').addEventListener('click', function() {
  document.getElementById('string1').value = '';
  document.getElementById('string2').value = '';
  document.getElementById('comparisonResults').style.display = 'none';
});

function compareStrings(str1, str2) {
  const areEqual = str1 === str2;

  let html = `
      <div class="alert ${areEqual ? 'alert-success' : 'alert-danger'}">
          <h5>${areEqual ? '✅ Strings are EQUAL' : '❌ Strings are NOT equal'}</h5>
      </div>
  `;

  <!-- Note for future self: -->
  <!-- This part should be improved to properly highlight the differences -->
  if (!areEqual) {
      html += `
          <div class="row">
              <div class="col-md-6">
                  <h6>String 1 (${str1.length} chars)</h6>
                  <!-- <div class="border p-2" style="background-color: var(--bg-secondary); font-family: monospace; white-space: pre-wrap; word-break: break-all;">${escapeHtml(str1)}</div> -->
              </div>
              <div class="col-md-6">
                  <h6>String 2 (${str2.length} chars)</h6>
                  <!-- <div class="border p-2" style="background-color: var(--bg-secondary); font-family: monospace; white-space: pre-wrap; word-break: break-all;">${escapeHtml(str2)}</div> -->
              </div>
          </div>
      `;
  }

  document.getElementById('comparisonResults').innerHTML = html;
  document.getElementById('comparisonResults').style.display = 'block';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
