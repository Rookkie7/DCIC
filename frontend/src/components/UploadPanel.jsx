import { useCallback, useRef, useState } from 'react';

const s = {
  zone: (active) => ({
    border: `2px dashed ${active ? 'var(--blue)' : 'var(--border-hi)'}`,
    borderRadius: 'var(--radius-lg)',
    background: active ? 'var(--blue-glow)' : 'transparent',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 14,
    padding: 34,
    minHeight: 220,
    position: 'relative',
  }),
  preview: {
    width: '100%',
    borderRadius: 'var(--radius)',
    overflow: 'hidden',
    border: '1px solid var(--border)',
    position: 'relative',
  },
  img: {
    width: '100%',
    display: 'block',
    maxHeight: 340,
    objectFit: 'contain',
    background: 'var(--bg-panel)',
  },
  clearBtn: {
    position: 'absolute',
    top: 8,
    right: 8,
    background: 'rgba(15,19,25,0.9)',
    border: '1px solid var(--border-hi)',
    borderRadius: 6,
    color: 'var(--text-dim)',
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: 'var(--mono)',
    letterSpacing: '0.04em',
    backdropFilter: 'blur(4px)',
  },
  label: {
    fontSize: 12,
    fontFamily: 'var(--mono)',
    color: 'var(--text-mute)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
  hint: {
    fontSize: 15,
    color: 'var(--text-dim)',
    textAlign: 'center',
    lineHeight: 1.5,
  },
  icon: {
    width: 42,
    height: 42,
    color: 'var(--text-mute)',
  },
};

export default function UploadPanel({ file, onFileChange }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const nextFile = e.dataTransfer.files[0];
    if (nextFile && nextFile.type.startsWith('image/')) onFileChange(nextFile);
  }, [onFileChange]);

  const handleChange = (e) => {
    const nextFile = e.target.files[0];
    if (nextFile) onFileChange(nextFile);
    e.target.value = '';
  };

  const preview = file ? URL.createObjectURL(file) : null;

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <span style={s.label}>Input Image</span>
      </div>

      {!file ? (
        <div
          style={s.zone(dragging)}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <svg style={s.icon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          <div style={s.hint}>
            <div style={{ color: 'var(--text-dim)', marginBottom: 4 }}>
              Drop an image here or click to browse
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-mute)' }}>
              JPEG, PNG / max 20 MB
            </div>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/jpg"
            style={{ display: 'none' }}
            onChange={handleChange}
          />
        </div>
      ) : (
        <div style={s.preview} className="animate-fadein">
          <img src={preview} alt="preview" style={s.img} />
          <button style={s.clearBtn} onClick={() => onFileChange(null)}>
            Remove
          </button>
          <div style={{
            padding: '8px 12px',
            fontSize: 12,
            fontFamily: 'var(--mono)',
            color: 'var(--text-mute)',
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-card)',
          }}>
            {file.name} &nbsp;/&nbsp; {(file.size / 1024).toFixed(0)} KB
          </div>
        </div>
      )}
    </div>
  );
}
