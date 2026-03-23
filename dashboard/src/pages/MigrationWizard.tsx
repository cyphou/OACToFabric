import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, ChevronRight, ChevronLeft, Rocket } from "lucide-react";
import { useCreateMigration } from "../hooks/useMigrations";
import type { MigrationCreateRequest, MigrationMode } from "../api/types";

const SOURCE_OPTIONS = [
  { value: "oac", label: "Oracle Analytics Cloud" },
  { value: "obiee", label: "OBIEE" },
  { value: "tableau", label: "Tableau" },
  { value: "cognos", label: "Cognos" },
  { value: "qlik", label: "Qlik" },
];

const STEPS = ["Source", "Configure", "Review"] as const;

export default function MigrationWizard() {
  const navigate = useNavigate();
  const create = useCreateMigration();

  const [step, setStep] = useState(0);
  const [form, setForm] = useState<MigrationCreateRequest>({
    name: "",
    source_type: "oac",
    config: {},
    mode: "full" as MigrationMode,
    wave: null,
    dry_run: false,
  });

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  const submit = async () => {
    const result = await create.mutateAsync(form);
    navigate(`/migrations/${result.id}`);
  };

  const canProceedStep0 = form.name.trim().length > 0;

  return (
    <div className="page">
      <header className="page-header">
        <h1>New Migration</h1>
      </header>

      {/* Step indicators */}
      <div className="wizard-steps">
        {STEPS.map((label, i) => (
          <div key={label} className={`wizard-step ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}>
            <span className="step-number">{i + 1}</span>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      <div className="card wizard-card">
        {/* Step 0: Source */}
        {step === 0 && (
          <div className="wizard-body">
            <h2>Select Source & Name</h2>
            <label className="field-label">Migration Name</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Q4 Finance Reports"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />

            <label className="field-label">Source Platform</label>
            <div className="radio-group">
              {SOURCE_OPTIONS.map((opt) => (
                <label key={opt.value} className={`radio-card ${form.source_type === opt.value ? "selected" : ""}`}>
                  <input
                    type="radio"
                    name="source"
                    value={opt.value}
                    checked={form.source_type === opt.value}
                    onChange={() => setForm({ ...form, source_type: opt.value })}
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Step 1: Configure */}
        {step === 1 && (
          <div className="wizard-body">
            <h2>Configure Migration</h2>

            <label className="field-label">Mode</label>
            <select
              className="input"
              value={form.mode}
              onChange={(e) => setForm({ ...form, mode: e.target.value as MigrationMode })}
            >
              <option value="full">Full Migration</option>
              <option value="incremental">Incremental Sync</option>
            </select>

            <label className="field-label">Wave (optional)</label>
            <input
              type="number"
              className="input"
              placeholder="All waves"
              value={form.wave ?? ""}
              onChange={(e) =>
                setForm({ ...form, wave: e.target.value ? parseInt(e.target.value, 10) : null })
              }
            />

            <label className="field-label checkbox-label">
              <input
                type="checkbox"
                checked={form.dry_run}
                onChange={(e) => setForm({ ...form, dry_run: e.target.checked })}
              />
              Dry run (validate only, no deployment)
            </label>
          </div>
        )}

        {/* Step 2: Review */}
        {step === 2 && (
          <div className="wizard-body">
            <h2>Review & Launch</h2>
            <dl className="meta-list">
              <dt>Name</dt><dd>{form.name}</dd>
              <dt>Source</dt><dd>{form.source_type}</dd>
              <dt>Mode</dt><dd>{form.mode}</dd>
              <dt>Wave</dt><dd>{form.wave ?? "All"}</dd>
              <dt>Dry Run</dt><dd>{form.dry_run ? "Yes" : "No"}</dd>
            </dl>
          </div>
        )}

        {/* Navigation */}
        <div className="wizard-actions">
          {step > 0 && (
            <button className="btn btn-ghost" onClick={prev}>
              <ChevronLeft size={16} /> Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          {step < STEPS.length - 1 ? (
            <button className="btn btn-primary" onClick={next} disabled={step === 0 && !canProceedStep0}>
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button className="btn btn-primary" onClick={submit} disabled={create.isPending}>
              {create.isPending ? <Loader2 size={16} className="spin" /> : <Rocket size={16} />}
              Launch Migration
            </button>
          )}
        </div>

        {create.isError && (
          <p className="text-danger" style={{ marginTop: 8 }}>
            Error: {(create.error as Error).message}
          </p>
        )}
      </div>
    </div>
  );
}
