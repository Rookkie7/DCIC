import { useState, useCallback } from 'react';
import UploadPanel    from './components/UploadPanel';
import ModelSelector  from './components/ModelSelector';
import StatusBar      from './components/StatusBar';
import ResultPanel    from './components/ResultPanel';
import { submitImage, pollStatus } from './api';

/* ── Shared card style ──────────────────────────────────────────────────────── */
const card = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-lg)',
  padding: 24,
};

export default function App() {
  const [file,        setFile]        = useState(null);
  const [model,       setModel]       = useState('');
  const [phase,       setPhase]       = useState('idle');  // idle | submitting | polling | done | error
  const [statusObj,   setStatusObj]   = useState(null);
  const [startTime,   setStartTime]   = useState(null);
  const [result,      setResult]      = useState(null);
  const [errorMsg,    setErrorMsg]    = useState('');

  const canDetect = file && model && phase === 'idle';

  const handleFileChange = useCallback((f) => {
    setFile(f);
    // Reset results when a new file is chosen
    if (phase !== 'idle') {
      setPhase('idle');
      setResult(null);
      setStatusObj(null);
      setErrorMsg('');
    }
  }, [phase]);

  const handleDetect = async () => {
    if (!canDetect) return;
    setPhase('submitting');
    setResult(null);
    setErrorMsg('');
    setStatusObj(null);
    setStartTime(Date.now());

    try {
      const taskId = await submitImage(file, model);
      setPhase('polling');
      setStatusObj({ status: 'queued', task_id: taskId, model });

      const final = await pollStatus(taskId, (s) => setStatusObj(s));

      if (final.status === 'done' && final.result) {
        setResult(final.result);
        setPhase('done');
      } else if (final.status === 'timeout') {
        setPhase('error');
        setErrorMsg('Inference timed out after 5 minutes.');
      } else {
        setPhase('error');
        setErrorMsg(final.error ?? 'An unknown error occurred.');
      }
    } catch (err) {
      setPhase('error');
      setErrorMsg(err.message ?? 'Network error.');
    }
  };

  const handleReset = () => {
    setFile(null);
    setModel('');
    setPhase('idle');
    setResult(null);
    setStatusObj(null);
    setErrorMsg('');
    setStartTime(null);
  };

  const isProcessing = phase === 'submitting' || phase === 'polling';
  const showStatus   = phase !== 'idle' && statusObj;
  const showResult   = phase === 'done' && result;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header style={{
        borderBottom: '1px solid var(--border)',
        padding: '0 32px',
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* NUS wordmark placeholder */}
          <div style={{
            fontFamily: 'var(--mono)',
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--blue)',
            letterSpacing: '0.08em',
            padding: '3px 8px',
            border: '1px solid var(--blue-dim)',
            borderRadius: 4,
          }}>
            NUS
          </div>
          <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
          <div style={{ fontWeight: 500, color: 'var(--text)', letterSpacing: '0.01em' }}>
            Image Forgery Detection
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--mono)',
          fontSize: 11,
          color: 'var(--text-mute)',
          letterSpacing: '0.06em',
        }}>
          ISY5004 · 2025
        </div>
      </header>

      {/* ── Main layout ────────────────────────────────────────────────────── */}
      <main style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '380px 1fr',
        gap: 24,
        padding: 24,
        maxWidth: 1200,
        width: '100%',
        margin: '0 auto',
        alignItems: 'start',
      }}>

        {/* ── Left column: controls ───────────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Upload */}
          <div style={card}>
            <UploadPanel file={file} onFileChange={handleFileChange} />
          </div>

          {/* Model selector */}
          <div style={card}>
            <ModelSelector
              selected={model}
              onChange={setModel}
              disabled={isProcessing}
            />
          </div>

          {/* Detect button */}
          <button
            onClick={handleDetect}
            disabled={!canDetect}
            style={{
              width: '100%',
              padding: '13px 0',
              borderRadius: 'var(--radius)',
              border: 'none',
              background: canDetect ? 'var(--blue)' : 'var(--bg-card)',
              color: canDetect ? '#fff' : 'var(--text-mute)',
              fontFamily: 'var(--mono)',
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              cursor: canDetect ? 'pointer' : 'not-allowed',
              border: `1px solid ${canDetect ? 'var(--blue)' : 'var(--border)'}`,
              transition: 'all 0.18s ease',
            }}
          >
            {isProcessing ? 'Processing...' : 'Detect'}
          </button>

          {/* Reset button (visible after processing) */}
          {phase !== 'idle' && !isProcessing && (
            <button
              onClick={handleReset}
              style={{
                width: '100%',
                padding: '10px 0',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--border)',
                background: 'transparent',
                color: 'var(--text-mute)',
                fontFamily: 'var(--mono)',
                fontSize: 12,
                letterSpacing: '0.06em',
                cursor: 'pointer',
                transition: 'all 0.18s ease',
              }}
            >
              New Detection
            </button>
          )}
        </div>

        {/* ── Right column: status + results ──────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Status bar */}
          {showStatus && (
            <div style={card}>
              <StatusBar
                status={statusObj.status}
                startTime={startTime}
                errorMsg={errorMsg}
              />
            </div>
          )}

          {/* Result panel */}
          {showResult && (
            <div style={card}>
              <ResultPanel result={result} originalFile={file} />
            </div>
          )}

          {/* Error with no result */}
          {phase === 'error' && !showStatus && (
            <div style={{
              ...card,
              borderColor: 'rgba(239,68,68,0.3)',
              color: 'var(--red)',
              fontFamily: 'var(--mono)',
              fontSize: 13,
            }}>
              {errorMsg}
            </div>
          )}

          {/* Empty state */}
          {phase === 'idle' && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 300,
              gap: 16,
              color: 'var(--text-mute)',
            }}>
              <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                style={{ opacity: 0.3 }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                  d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
              <div style={{ fontSize: 13, textAlign: 'center', maxWidth: 260, lineHeight: 1.6 }}>
                Upload an image and select a model to begin forgery analysis.
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
