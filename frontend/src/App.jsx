import { useCallback, useState } from 'react';
import BatchPanel from './components/BatchPanel';
import UploadPanel from './components/UploadPanel';
import ModelSelector from './components/ModelSelector';
import StatusBar from './components/StatusBar';
import ResultPanel from './components/ResultPanel';
import { submitImage, pollStatus } from './api';

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

function Header({ view, onViewChange }) {
  const tabs = [
    { id: 'single', label: 'Single Image' },
    { id: 'batch', label: 'Batch Folder' },
  ];

  return (
    <header className="app-header">
      <div className="brand-group">
        <div className="brand-mark">DCIC</div>
        <div>
          <div className="brand-title">Forgery Analysis Console</div>
          <div className="brand-subtitle">Image authentication and localization</div>
        </div>
      </div>

      <nav className="view-tabs" aria-label="Workflow">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`view-tab ${view === tab.id ? 'active' : ''}`}
            onClick={() => onViewChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </header>
  );
}

function SingleImagePanel() {
  const [file, setFile] = useState(null);
  const [model, setModel] = useState('');
  const [explainMode, setExplainMode] = useState('template');
  const [phase, setPhase] = useState('idle');
  const [statusObj, setStatusObj] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const isProcessing = phase === 'submitting' || phase === 'polling';
  const canDetect = file && model && phase === 'idle';
  const showStatus = phase !== 'idle' && statusObj;
  const showResult = phase === 'done' && result;

  const handleFileChange = useCallback((nextFile) => {
    setFile(nextFile);
    if (phase !== 'idle') {
      setPhase('idle');
      setResult(null);
      setStatusObj(null);
      setErrorMsg('');
    }
  }, [phase]);

  const handleModelChange = (nextModel) => {
    setModel(nextModel);
    if (nextModel !== 'dino_cnn') {
      setExplainMode('template');
    }
  };

  const handleDetect = async () => {
    if (!canDetect) return;
    setPhase('submitting');
    setResult(null);
    setErrorMsg('');
    setStatusObj(null);
    setStartTime(Date.now());

    try {
      const taskId = await submitImage(file, model, explainMode);
      setPhase('polling');
      setStatusObj({ status: 'queued', task_id: taskId, model, explain_mode: explainMode });

      const final = await pollStatus(taskId, setStatusObj);

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
    setExplainMode('template');
    setPhase('idle');
    setResult(null);
    setStatusObj(null);
    setErrorMsg('');
    setStartTime(null);
  };

  return (
    <div className="workspace-grid">
      <div className="control-stack">
        <div style={card}>
          <UploadPanel file={file} onFileChange={handleFileChange} />
        </div>

        <div style={card}>
          <ModelSelector selected={model} onChange={handleModelChange} disabled={isProcessing} />
        </div>

        {model === 'dino_cnn' && (
          <div style={card}>
            <div style={sectionLabel}>Report Mode</div>
            <label className="switch-row">
              <span>Qwen2-VL report</span>
              <input
                type="checkbox"
                checked={explainMode === 'llm'}
                disabled={isProcessing}
                onChange={(e) => setExplainMode(e.target.checked ? 'llm' : 'template')}
              />
            </label>
          </div>
        )}

        <button
          onClick={handleDetect}
          disabled={!canDetect}
          className="primary-action"
        >
          {isProcessing ? 'Processing...' : 'Detect Image'}
        </button>

        {phase !== 'idle' && !isProcessing && (
          <button onClick={handleReset} className="ghost-action">New Detection</button>
        )}
      </div>

      <div className="result-stack">
        {showStatus && (
          <div style={card}>
            <StatusBar status={statusObj.status} startTime={startTime} errorMsg={errorMsg} />
          </div>
        )}

        {showResult && (
          <div style={card}>
            <ResultPanel result={result} originalFile={file} />
          </div>
        )}

        {phase === 'error' && !showStatus && (
          <div style={{ ...card, borderColor: 'rgba(239,68,68,0.3)', color: 'var(--red)' }}>
            {errorMsg}
          </div>
        )}

        {phase === 'idle' && (
          <div className="empty-panel">
            <div className="empty-icon">S</div>
            <div>Upload an image and select a model to begin analysis.</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState('single');

  return (
    <div className="app-shell">
      <Header view={view} onViewChange={setView} />
      <main className="app-main">
        {view === 'batch' ? <BatchPanel /> : <SingleImagePanel />}
      </main>
    </div>
  );
}
