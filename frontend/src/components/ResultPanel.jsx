const NO_LOC_MODELS = new Set(['rigid', 'warpad']);

const MODEL_LABELS = {
  dino_cnn:   'DINO + CNN',
  fakeshield: 'FakeShield',
  rigid:      'RIGID',
  warpad:     'WaRPAD',
};

function VerdictBadge({ label, confidence }) {
  const isFake = label === 'fake';
  return (
    <div style={{
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 6,
      padding: '18px 36px',
      borderRadius: 'var(--radius-lg)',
      background: isFake ? 'var(--red-dim)' : 'var(--green-dim)',
      border: `1px solid ${isFake ? 'rgba(239,68,68,0.35)' : 'rgba(34,197,94,0.35)'}`,
      animation: 'verdict-enter 0.4s cubic-bezier(0.34,1.56,0.64,1) both',
    }}>
      <div style={{
        fontFamily: 'var(--mono)',
        fontSize: 28,
        fontWeight: 600,
        letterSpacing: '0.12em',
        color: isFake ? 'var(--red)' : 'var(--green)',
        lineHeight: 1,
      }}>
        {isFake ? 'FORGED' : 'AUTHENTIC'}
      </div>
      {confidence != null && (
        <div style={{
          fontFamily: 'var(--mono)',
          fontSize: 13,
          color: isFake ? 'rgba(239,68,68,0.7)' : 'rgba(34,197,94,0.7)',
          letterSpacing: '0.04em',
        }}>
          {(confidence * 100).toFixed(1)}% confidence
        </div>
      )}
    </div>
  );
}

function MetaRow({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
      <span style={{
        fontSize: 11,
        fontFamily: 'var(--mono)',
        color: 'var(--text-mute)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        width: 80,
        flexShrink: 0,
      }}>
        {label}
      </span>
      <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>{value}</span>
    </div>
  );
}

function ImagePane({ src, caption, dataType }) {
  const prefix = dataType === 'jpeg'
    ? 'data:image/jpeg;base64,'
    : 'data:image/png;base64,';
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{
        fontSize: 11,
        fontFamily: 'var(--mono)',
        color: 'var(--text-mute)',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        marginBottom: 8,
      }}>
        {caption}
      </div>
      <div style={{
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        background: '#080e1a',
      }}>
        <img
          src={prefix + src}
          alt={caption}
          style={{ width: '100%', display: 'block', maxHeight: 280, objectFit: 'contain' }}
        />
      </div>
    </div>
  );
}

export default function ResultPanel({ result, originalFile }) {
  if (!result) return null;

  const { label, confidence, overlay_base64, mask_base64, explanation, model, elapsed_ms } = result;
  const noLoc = NO_LOC_MODELS.has(model);
  const hasOverlay = !noLoc && overlay_base64;
  const originalUrl = originalFile ? URL.createObjectURL(originalFile) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }} className="animate-fadein">

      {/* Verdict */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <VerdictBadge label={label} confidence={confidence} />
      </div>

      {/* Meta info */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}>
        <MetaRow label="Model"   value={MODEL_LABELS[model] ?? model} />
        <MetaRow label="Elapsed" value={elapsed_ms != null ? `${elapsed_ms} ms` : '—'} />
        {result.raw_score != null && (
          <MetaRow label="Score" value={result.raw_score.toFixed(6)} />
        )}
      </div>

      {/* Image comparison */}
      {hasOverlay && originalUrl && (
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 11,
              fontFamily: 'var(--mono)',
              color: 'var(--text-mute)',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              marginBottom: 8,
            }}>Original</div>
            <div style={{
              borderRadius: 'var(--radius)',
              overflow: 'hidden',
              border: '1px solid var(--border)',
              background: '#080e1a',
            }}>
              <img
                src={originalUrl}
                alt="original"
                style={{ width: '100%', display: 'block', maxHeight: 280, objectFit: 'contain' }}
              />
            </div>
          </div>
          <ImagePane src={overlay_base64} caption="Localization" dataType="jpeg" />
        </div>
      )}

      {/* No localization notice */}
      {noLoc && (
        <div style={{
          fontSize: 12,
          fontFamily: 'var(--mono)',
          color: 'var(--text-mute)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '10px 14px',
          letterSpacing: '0.02em',
        }}>
          This model does not support spatial localization.
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <div>
          <div style={{
            fontSize: 11,
            fontFamily: 'var(--mono)',
            color: 'var(--text-mute)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginBottom: 8,
          }}>
            Analysis
          </div>
          <div style={{
            fontSize: 13,
            color: 'var(--text-dim)',
            lineHeight: 1.7,
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '14px 16px',
          }}>
            {explanation}
          </div>
        </div>
      )}
    </div>
  );
}
