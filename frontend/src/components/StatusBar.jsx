import { useEffect, useState } from 'react';

const STATUS_META = {
  queued:  { color: 'var(--text-mute)', label: 'Queued',           spin: false },
  running: { color: 'var(--blue)',      label: 'Running inference', spin: true  },
  done:    { color: 'var(--green)',     label: 'Complete',          spin: false },
  timeout: { color: 'var(--red)',       label: 'Timeout',           spin: false },
  error:   { color: 'var(--red)',       label: 'Error',             spin: false },
};

export default function StatusBar({ status, startTime, errorMsg }) {
  const [elapsed, setElapsed] = useState(0);
  const meta = STATUS_META[status] ?? STATUS_META.queued;

  useEffect(() => {
    if (!startTime || status === 'done' || status === 'timeout' || status === 'error') return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [startTime, status]);

  const pct = Math.min((elapsed / 300) * 100, 100);

  return (
    <div style={{ animation: 'fadeIn 0.3s ease both' }} className="animate-fadein">
      {/* Status row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        marginBottom: 10,
      }}>
        {/* Spinner or dot */}
        <div style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          border: meta.spin ? `2px solid ${meta.color}` : 'none',
          borderTopColor: meta.spin ? 'transparent' : undefined,
          background: meta.spin ? 'transparent' : meta.color,
          animation: meta.spin ? 'spin 0.8s linear infinite' : 'none',
          flexShrink: 0,
        }} />
        <span style={{
          fontFamily: 'var(--mono)',
          fontSize: 12,
          color: meta.color,
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
        }}>
          {meta.label}
        </span>
        {(status === 'queued' || status === 'running') && (
          <span style={{
            marginLeft: 'auto',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: 'var(--text-mute)',
          }}>
            {elapsed}s / 300s
          </span>
        )}
        {status === 'done' && (
          <span style={{
            marginLeft: 'auto',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: 'var(--text-mute)',
          }}>
            {elapsed}s
          </span>
        )}
      </div>

      {/* Progress bar */}
      {(status === 'queued' || status === 'running') && (
        <div style={{
          height: 3,
          background: 'var(--border)',
          borderRadius: 2,
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${pct}%`,
            background: 'var(--blue)',
            borderRadius: 2,
            transition: 'width 1s linear',
          }} />
        </div>
      )}

      {/* Error message */}
      {status === 'error' && errorMsg && (
        <div style={{
          marginTop: 8,
          fontSize: 12,
          color: 'var(--red)',
          fontFamily: 'var(--mono)',
          background: 'rgba(239,68,68,0.08)',
          border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: 'var(--radius)',
          padding: '8px 12px',
          wordBreak: 'break-word',
        }}>
          {errorMsg}
        </div>
      )}
    </div>
  );
}
