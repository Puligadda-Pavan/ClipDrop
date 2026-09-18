const form = document.querySelector('#download-form');
const urlInput = document.querySelector('#url');
const submitButton = document.querySelector('#submit-button');
const progressPanel = document.querySelector('#progress-panel');
const progressLabel = document.querySelector('#progress-label');
const progressPercent = document.querySelector('#progress-percent');
const progressBar = document.querySelector('#progress-bar');
const progressDetail = document.querySelector('#progress-detail');
const progressEta = document.querySelector('#progress-eta');
const completeActions = document.querySelector('#complete-actions');
const fileName = document.querySelector('#file-name');
const saveLink = document.querySelector('#save-link');
const errorMessage = document.querySelector('#error-message');
const apiBaseUrl = (window.DOWNLOADER_API_URL || window.location.origin).replace(/\/$/, '');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  setLoading(true);
  resetPanel();
  progressPanel.hidden = false;
  progressLabel.textContent = 'Preparing your download';
  progressDetail.textContent = 'Connecting...';

  try {
    const response = await fetch(`${apiBaseUrl}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlInput.value })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not start the download.');
    pollJob(data.job_id);
  } catch (error) {
    showError(error.message);
    setLoading(false);
  }
});

async function pollJob(jobId) {
  try {
    const response = await fetch(`${apiBaseUrl}/api/download/${jobId}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error || 'Could not read download status.');
    updateProgress(job);
    if (job.status === 'complete' || job.status === 'error') {
      setLoading(false);
      return;
    }
    window.setTimeout(() => pollJob(jobId), 900);
  } catch (error) {
    showError(error.message);
    setLoading(false);
  }
}

function updateProgress(job) {
  const percent = Number(job.progress || 0);
  progressPercent.textContent = `${percent}%`;
  progressBar.style.width = `${percent}%`;
  progressDetail.textContent = job.status === 'processing' ? 'Finishing the MP4...' : `${job.speed || 'Downloading'}${job.eta ? `, ${job.eta} remaining` : ''}`;
  if (job.status === 'complete') {
    progressLabel.textContent = 'Your video is ready';
    progressDetail.textContent = 'Download complete';
    completeActions.hidden = false;
    fileName.textContent = job.filename;
    saveLink.href = job.download_url.startsWith('http')
      ? job.download_url
      : `${apiBaseUrl}${job.download_url}`;
  } else if (job.status === 'error') {
    showError(job.error || 'The download could not be completed.');
  } else {
    progressLabel.textContent = job.status === 'processing' ? 'Wrapping up your download' : 'Downloading your video';
  }
}

function resetPanel() {
  completeActions.hidden = true;
  saveLink.removeAttribute('href');
  fileName.textContent = '';
  errorMessage.hidden = true;
  progressBar.style.width = '0%';
  progressPercent.textContent = '0%';
}

function showError(message) {
  progressPanel.hidden = false;
  completeActions.hidden = true;
  saveLink.removeAttribute('href');
  errorMessage.textContent = message;
  errorMessage.hidden = false;
  progressLabel.textContent = 'Something needs attention';
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.querySelector('span:first-child').textContent = isLoading ? 'Working...' : 'Download';
}
