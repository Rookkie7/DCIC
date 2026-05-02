const NO_LOC_MODELS = new Set(['rigid', 'warpad']);

const MODEL_LABELS = {
  dino_cnn: 'DINO + CNN',
  fakeshield: 'FakeShield',
  rigid: 'RIGID',
  warpad: 'WaRPAD',
};

function VerdictBadge({ label, confidence }) {
  const isFake = label === 'fake';
  return (
    <div style={{
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 8,
      padding: '20px 40px',
      borderRadius: 'var(--radius-lg)',
      background: isFake ? 'var(--red-dim)' : 'var(--green-dim)',
      border: `1px solid ${isFake ? 'rgba(255,92,122,0.35)' : 'rgba(61,220,151,0.35)'}`,
      animation: 'verdict-enter 0.35s cubic-bezier(0.34,1.56,0.64,1) both',
    }}>
      <div style={{
        fontFamily: 'var(--mono)',
        fontSize: 30,
        fontWeight: 700,
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
          color: isFake ? 'rgba(255,92,122,0.75)' : 'rgba(61,220,151,0.75)',
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
        width: 84,
        flexShrink: 0,
      }}>
        {label}
      </span>
      <span style={{ fontSize: 14, color: 'var(--text-dim)' }}>{value}</span>
    </div>
  );
}

function ImagePane({ src, caption, dataType = 'png' }) {
  const prefix = dataType === 'jpeg' ? 'data:image/jpeg;base64,' : 'data:image/png;base64,';
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{
        fontSize: 11,
        fontFamily: 'var(--mono)',
        color: 'var(--text-mute)',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        marginBottom: 8,
      }}>
        {caption}
      </div>
      <div style={{
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        background: 'var(--bg-panel)',
      }}>
        <img
          src={prefix + src}
          alt={caption}
          style={{ width: '100%', display: 'block', maxHeight: 300, objectFit: 'contain' }}
        />
      </div>
    </div>
  );
}

export default function ResultPanel({ result, originalFile, originalUrl: originalUrlProp }) {
  if (!result) return null;

  const {
    label,
    confidence,
    overlay_base64,
    mask_base64,
    explanation,
    model,
    elapsed_ms,
    explanation_source,
  } = result;
  const noLoc = NO_LOC_MODELS.has(model);
  const hasOverlay = !noLoc && overlay_base64;
  const hasMask = !noLoc && mask_base64;
  const originalUrl = originalUrlProp || (originalFile ? URL.createObjectURL(originalFile) : null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }} className="animate-fadein">
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <VerdictBadge label={label} confidence={confidence} />
      </div>

      <div style={{
        background: 'var(--bg-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}>
        <MetaRow label="Model" value={MODEL_LABELS[model] ?? model} />
        <MetaRow label="Elapsed" value={elapsed_ms != null ? `${elapsed_ms} ms` : '-'} />
        {result.raw_score != null && <MetaRow label="Score" value={result.raw_score.toFixed(6)} />}
        {explanation_source && (
          <MetaRow label="Report" value={explanation_source === 'qwen2_vl' ? 'Qwen2-VL' : 'Template'} />
        )}
      </div>

      {originalUrl && (
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{
              fontSize: 11,
              fontFamily: 'var(--mono)',
              color: 'var(--text-mute)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginBottom: 8,
            }}>
              Original
            </div>
            <div style={{
              borderRadius: 'var(--radius)',
              overflow: 'hidden',
              border: '1px solid var(--border)',
              background: 'var(--bg-panel)',
            }}>
              <img
                src={originalUrl}
                alt="original"
                style={{ width: '100%', display: 'block', maxHeight: 300, objectFit: 'contain' }}
              />
            </div>
          </div>
          {hasOverlay && <ImagePane src={overlay_base64} caption="Localization" dataType="jpeg" />}
          {hasMask && <ImagePane src={mask_base64} caption="Mask" dataType="png" />}
        </div>
      )}

      {noLoc && (
        <div style={{
          fontSize: 13,
          fontFamily: 'var(--mono)',
          color: 'var(--text-mute)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '11px 14px',
          letterSpacing: '0.02em',
        }}>
          This model does not support spatial localization.
        </div>
      )}

      {explanation && (
        <div>
          <div style={{
            fontSize: 11,
            fontFamily: 'var(--mono)',
            color: 'var(--text-mute)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 8,
          }}>
            Analysis
          </div>
          <div style={{
            fontSize: 15,
            color: 'var(--text-dim)',
            lineHeight: 1.75,
            background: 'var(--bg-panel)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '16px 18px',
          }}>
            {explanation}
          </div>
        </div>
      )}
    </div>
  );
}
