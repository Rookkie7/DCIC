const POLL_INTERVAL_MS = 2000;
const MAX_POLL_MS      = 310_000;

/**
 * Submit an image for inference.
 * @param {File}   file
 * @param {string} model  one of dino_cnn | fakeshield | rigid | warpad
 * @returns {Promise<string>} task_id
 */
export async function submitImage(file, model) {
  const body = new FormData();
  body.append('file', file);
  body.append('model', model);

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
