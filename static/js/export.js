/* export.js — CSV download helpers for screener, portfolio, watchlist, transactions */

/**
 * Trigger a CSV download from the backend export API.
 * @param {'screener'|'portfolio'|'watchlist'|'transactions'} type
 */
function exportCSV(type) {
  const validTypes = ['screener', 'portfolio', 'watchlist', 'transactions'];
  if (!validTypes.includes(type)) return;

  const btn = document.querySelector(`[data-export="${type}"]`);
  if (btn) {
    btn.disabled = true;
    btn.classList.add('btn-loading');
  }

  fetch(`/api/export/${type}`, { credentials: 'include' })
    .then(res => {
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      return res.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Extract filename from type + date
      const ts = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      a.download = `${type}_${ts}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    })
    .catch(err => {
      console.error('Export error:', err);
      alert('Export failed. Please try again.');
    })
    .finally(() => {
      if (btn) {
        btn.disabled = false;
        btn.classList.remove('btn-loading');
      }
    });
}
