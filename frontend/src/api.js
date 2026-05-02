const POLL_INTERVAL_MS = 2000;
const MAX_POLL_MS      = 310_000;
const MAX_BATCH_POLL_MS = 43_200_000;

/**
 * Submit an image for inference.
 * @param {File}   file
 * @param {string} model  one of dino_cnn | fakeshield | rigid | warpad
 * @param {string} explainMode  template | llm
 * @returns {Promise<string>} task_id
 */
export async function submitImage(file, model, explainMode = 'template') {
  const body = new FormData();
  body.append('file', file);
  body.append('model', model);
  body.append('explain_mode', explainMode);

  const res = await fetch('/api/submit', { method: 'POST', body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Submit failed');
  }
  const data = await res.json();
  return data.task_id;
}

/**
 * Poll /api/status/{taskId} until terminal state.
 * Calls onUpdate(statusObj) on every poll.
 * Resolves with the final status object.
 */
export async function pollStatus(taskId, onUpdate) {
  const deadline = Date.now() + MAX_POLL_MS;

  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const res = await fetch(`/api/status/${taskId}`);
        if (!res.ok) throw new Error(`Status check failed: ${res.status}`);
        const data = await res.json();
        onUpdate(data);

        if (['done', 'timeout', 'error'].includes(data.status)) {
          resolve(data);
          return;
        }
        if (Date.now() >= deadline) {
          resolve({ ...data, status: 'timeout' });
          return;
        }
        setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        reject(err);
      }
    };
    setTimeout(tick, POLL_INTERVAL_MS);
  });
}

/**
 * Submit a folder path for batch inference.
 * The folder must be visible to the local backend process.
 */
export async function submitBatch(folderPath, model, explainMode = 'template', recursive = false, saveDir = '') {
  const body = new FormData();
  body.append('folder_path', folderPath);
  body.append('model', model);
  body.append('explain_mode', explainMode);
  body.append('recursive', recursive ? 'true' : 'false');
  if (saveDir.trim()) {
    body.append('save_dir', saveDir.trim());
  }

  const res = await fetch('/api/batch/submit', { method: 'POST', body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Batch submit failed');
  }
  return res.json();
}

/**
 * Poll /api/batch/status/{batchId} until the batch is complete.
 */
export async function pollBatchStatus(batchId, onUpdate) {
  const deadline = Date.now() + MAX_BATCH_POLL_MS;

  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const res = await fetch(`/api/batch/status/${batchId}`);
        if (!res.ok) throw new Error(`Batch status check failed: ${res.status}`);
        const data = await res.json();
        onUpdate(data);

        if (['done', 'error'].includes(data.status)) {
          resolve(data);
          return;
        }
        if (Date.now() >= deadline) {
          resolve({ ...data, status: 'timeout' });
          return;
        }
        setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        reject(err);
      }
    };
    setTimeout(tick, POLL_INTERVAL_MS);
  });
}
