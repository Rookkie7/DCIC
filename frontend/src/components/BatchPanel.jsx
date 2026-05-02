import { useMemo, useState } from 'react';
import ModelSelector from './ModelSelector';
import { pollBatchStatus, submitBatch } from '../api';

const card = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-lg)',
  padding: 24,
};

const sectionLabel = {
  fontSize: 12,
  fontFamily: 'var(--mono)',
  color: 'var(--text-mute)',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  marginBottom: 12,
};

const inputStyle = {
  width: '100%',
  background: 'var(--bg-panel)',
  border: '1px solid var(--border-hi)',
  borderRadius: 'var(--radius)',
  color: 'var(--text)',
  fontSize: 15,
  lineHeight: 1.4,
  padding: '12px 14px',
  outline: 'none',
};

function BatchSummary({ batch }) {
  if (!batch) return null;

  const total = batch.total || 0;
  const finished = (batch.completed || 0) + (batch.failed || 0);
  const pct = total ? Math.round((finished / total) * 100) : 0;
  const running = batch.status === 'queued' || batch.status === 'running';

  return (
    <div style={card} className="animate-fadein">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        gap: 16,
        marginBottom: 12,
      }}>
        <div>
          <div style={sectionLabel}>Batch Status</div>
          <div style={{ fontSize: 22, fontWeight: 650, color: 'var(--text)' }}>
            {finished} / {total} images
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--mono)',
          fontSize: 13,
          color: batch.failed ? 'var(--red)' : running ? 'var(--blue)' : 'var(--green)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}>
          {batch.status}
        </div>
      </div>

      <div style={{
        height: 8,
        background: 'var(--border)',
        borderRadius: 999,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: batch.failed ? 'var(--red)' : 'var(--blue)',
          borderRadius: 999,
          transition: 'width 0.25s ease',
        }} />
      </div>

      <div style={{
        display: 'flex',
        gap: 16,
        marginTop: 12,
        fontFamily: 'var(--mono)',
        fontSize: 12,
        color: 'var(--text-dim)',
      }}>
        <span>Completed: {batch.completed || 0}</span>
        <span>Failed: {batch.failed || 0}</span>
      </div>
      {batch.error && (
        <div style={{
          marginTop: 12,
          color: 'var(--red)',
          fontSize: 13,
          wordBreak: 'break-word',
        }}>
          {batch.error}
        </div>
      )}
    </div>
  );
}

function ResultTable({ items }) {
  if (!items?.length) return null;

  return (
    <div style={card} className="animate-fadein">
      <div style={sectionLabel}>Batch Results</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 14,
          minWidth: 720,
        }}>
          <thead>
            <tr style={{ color: 'var(--text-mute)', fontFamily: 'var(--mono)', fontSize: 11 }}>
              <th style={th}>File</th>
              <th style={th}>Status</th>
              <th style={th}>Verdict</th>
              <th style={th}>Confidence</th>
              <th style={th}>Elapsed</th>
              <th style={th}>Message</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const result = item.result || {};
              const isFake = result.label === 'fake';
              return (
                <tr key={item.file_path} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ ...td, color: 'var(--text)', maxWidth: 260 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.file_name}
                    </div>
                  </td>
                  <td style={td}>
                    <span style={{
                      color: item.status === 'error' ? 'var(--red)' : item.status === 'done' ? 'var(--green)' : 'var(--blue)',
                      fontFamily: 'var(--mono)',
                      textTransform: 'uppercase',
                      fontSize: 12,
                    }}>
                      {item.status}
                    </span>
                  </td>
                  <td style={td}>
                    {result.label ? (
                      <span style={{
                        color: isFake ? 'var(--red)' : 'var(--green)',
                        fontWeight: 650,
                        textTransform: 'uppercase',
                      }}>
                        {isFake ? 'Forged' : 'Authentic'}
                      </span>
                    ) : '-'}
                  </td>
                  <td style={td}>
                    {result.confidence != null ? `${(result.confidence * 100).toFixed(1)}%` : '-'}
                  </td>
                  <td style={td}>
                    {result.elapsed_ms != null ? `${result.elapsed_ms} ms` : '-'}
                  </td>
                  <td style={{ ...td, color: item.error ? 'var(--red)' : 'var(--text-mute)', maxWidth: 320 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.error || result.explanation || '-'}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th = {
  textAlign: 'left',
  padding: '0 12px 10px 0',
  fontWeight: 500,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
};

const td = {
  padding: '12px 12px 12px 0',
  color: 'var(--text-dim)',
  verticalAlign: 'top',
};

export default function BatchPanel() {
  const [folderPath, setFolderPath] = useState('');
  const [recursive, setRecursive] = useState(false);
  const [model, setModel] = useState('');
  const [explainMode, setExplainMode] = useState('template');
  const [phase, setPhase] = useState('idle');
  const [batch, setBatch] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const isProcessing = phase === 'submitting' || phase === 'polling';
  const canStart = folderPath.trim() && model && !isProcessing;

  const visibleItems = useMemo(() => batch?.items || [], [batch]);

  const handleModelChange = (nextModel) => {
    setModel(nextModel);
    if (nextModel !== 'dino_cnn') {
      setExplainMode('template');
    }
  };

  const handleSubmit = async () => {
    if (!canStart) return;
    setPhase('submitting');
    setErrorMsg('');
    setBatch(null);

    try {
      const created = await submitBatch(folderPath.trim(), model, explainMode, recursive);
      setBatch({ ...created, model, explain_mode: explainMode, items: [] });
      setPhase('polling');

      const final = await pollBatchStatus(created.batch_id, setBatch);
      setBatch(final);
      setPhase(final.status === 'done' || final.status === 'error' ? 'done' : 'error');
      if (final.status === 'timeout') {
        setErrorMsg('Batch polling timed out.');
      }
    } catch (err) {
      setPhase('error');
      setErrorMsg(err.message || 'Batch request failed.');
    }
  };

  const reset = () => {
    setPhase('idle');
    setBatch(null);
    setErrorMsg('');
  };

  return (
    <div className="workspace-grid">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={card}>
          <div style={sectionLabel}>Image Folder</div>
          <input
            value={folderPath}
            disabled={isProcessing}
            onChange={(e) => setFolderPath(e.target.value)}
            placeholder="E:\\sensing_project\\data\\images"
            style={inputStyle}
          />
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            marginTop: 14,
            color: 'var(--text-dim)',
            fontSize: 14,
            cursor: isProcessing ? 'not-allowed' : 'pointer',
            opacity: isProcessing ? 0.6 : 1,
          }}>
            <input
              type="checkbox"
              checked={recursive}
              disabled={isProcessing}
              onChange={(e) => setRecursive(e.target.checked)}
              style={{ width: 17, height: 17 }}
            />
            Include subfolders
          </label>
        </div>

        <div style={card}>
          <ModelSelector selected={model} onChange={handleModelChange} disabled={isProcessing} />
        </div>

        {model === 'dino_cnn' && (
          <div style={card}>
            <div style={sectionLabel}>Report Mode</div>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 16,
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              opacity: isProcessing ? 0.5 : 1,
            }}>
              <span style={{ fontSize: 15, color: 'var(--text-dim)' }}>Qwen2-VL report</span>
              <input
                type="checkbox"
                checked={explainMode === 'llm'}
                disabled={isProcessing}
                onChange={(e) => setExplainMode(e.target.checked ? 'llm' : 'template')}
                style={{ width: 18, height: 18, flexShrink: 0 }}
              />
            </label>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!canStart}
          className="primary-action"
        >
          {isProcessing ? 'Processing...' : 'Run Batch'}
        </button>

        {phase !== 'idle' && !isProcessing && (
          <button onClick={reset} className="ghost-action">New Batch</button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {batch ? <BatchSummary batch={batch} /> : (
          <div className="empty-panel">
            <div className="empty-icon">B</div>
            <div>Enter a folder path, select one model, and start a batch run.</div>
          </div>
        )}

        {errorMsg && (
          <div style={{ ...card, borderColor: 'rgba(239,68,68,0.3)', color: 'var(--red)' }}>
            {errorMsg}
          </div>
        )}

        <ResultTable items={visibleItems} />
      </div>
    </div>
  );
}
