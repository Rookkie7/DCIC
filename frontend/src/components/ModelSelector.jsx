const MODELS = [
  {
    id: 'dino_cnn',
    label: 'DINO + CNN',
    tag: 'Supervised',
    desc: 'DINOv2-Large backbone with CNN decoder. Trained on DCIC data. Supports pixel-level localization.',
  },
  {
    id: 'fakeshield',
    label: 'FakeShield',
    tag: 'MLLM · ICLR 2025',
    desc: 'Multimodal LLM pipeline (DTE-FDM + MFLM). Produces natural-language explanations and segmentation masks.',
  },
  {
    id: 'rigid',
    label: 'RIGID',
    tag: 'Training-free',
    desc: 'Compares DINOv2 feature similarity under Gaussian noise perturbation. Classification only.',
  },
  {
    id: 'warpad',
    label: 'WaRPAD',
    tag: 'Training-free · NeurIPS 2025',
    desc: 'Wavelet-patch robustness analysis with DINOv2. Classification only; limited on traditional manipulations.',
  },
];

export default function ModelSelector({ selected, onChange, disabled }) {
  return (
    <div>
      <div style={{
        fontSize: 12,
        fontFamily: 'var(--mono)',
        color: 'var(--text-mute)',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        marginBottom: 12,
      }}>
        Detection Model
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {MODELS.map((m) => {
          const active = selected === m.id;
          return (
            <label
              key={m.id}
              style={{
                display: 'flex',
                gap: 14,
                padding: '12px 16px',
                borderRadius: 'var(--radius)',
                border: `1px solid ${active ? 'var(--blue)' : 'var(--border)'}`,
                background: active ? 'var(--blue-glow)' : 'var(--bg-card)',
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.5 : 1,
                transition: 'all 0.18s ease',
              }}
            >
              {/* Radio dot */}
              <div style={{
                marginTop: 2,
                width: 16,
                height: 16,
                borderRadius: '50%',
                border: `2px solid ${active ? 'var(--blue)' : 'var(--border-hi)'}`,
                background: active ? 'var(--blue)' : 'transparent',
                flexShrink: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.18s ease',
              }}>
                {active && (
                  <div style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: '#fff',
                  }} />
                )}
              </div>

              <input
                type="radio"
                name="model"
                value={m.id}
                checked={active}
                onChange={() => !disabled && onChange(m.id)}
                style={{ display: 'none' }}
              />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 3,
                }}>
                  <span style={{
                    fontWeight: 500,
                    fontSize: 14,
                    color: active ? 'var(--text)' : 'var(--text-dim)',
                  }}>
                    {m.label}
                  </span>
                  <span style={{
                    fontSize: 10,
                    fontFamily: 'var(--mono)',
                    color: active ? 'var(--blue)' : 'var(--text-mute)',
                    background: active ? 'rgba(59,130,246,0.12)' : 'transparent',
                    border: `1px solid ${active ? 'rgba(59,130,246,0.3)' : 'transparent'}`,
                    borderRadius: 4,
                    padding: '1px 6px',
                    letterSpacing: '0.04em',
                    flexShrink: 0,
                  }}>
                    {m.tag}
                  </span>
                </div>
                <div style={{
                  fontSize: 12,
                  color: 'var(--text-mute)',
                  lineHeight: 1.5,
                }}>
                  {m.desc}
                </div>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
