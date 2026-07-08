import { useEffect, useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, XCircle } from 'lucide-react';
import api from '../api/client';
import { Panel, Button, EmptyState } from '../components/ui';

const STATUS_STYLES = {
  processed: { icon: CheckCircle2, color: 'var(--accent-teal)' },
  validated: { icon: CheckCircle2, color: 'var(--accent-teal)' },
  invalid: { icon: XCircle, color: 'var(--accent-danger)' },
  uploaded: { icon: FileText, color: 'var(--text-secondary)' },
};

export default function DatasetUpload() {
  const [datasets, setDatasets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const fileInput = useRef(null);

  const load = async () => {
    const res = await api.get('/api/datasets');
    setDatasets(res.data);
  };

  useEffect(() => {
    load();
  }, []);

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setLastResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post('/api/datasets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setLastResult({ ok: true, ...res.data });
    } catch (err) {
      setLastResult({ ok: false, detail: err.response?.data?.detail || 'Upload failed' });
    } finally {
      setUploading(false);
      load();
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Datasets</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          Upload CSV files with columns: <span className="font-mono-data text-[var(--text-primary)]">timestamp, device_id, energy_kwh</span>{' '}
          (optional <span className="font-mono-data text-[var(--text-primary)]">temperature_c</span>).
        </p>
      </div>

      <Panel className="mb-6">
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            handleFile(e.dataTransfer.files[0]);
          }}
          onClick={() => fileInput.current?.click()}
          className="border-2 border-dashed border-[var(--border-bright)] rounded-[var(--radius-md)] py-10 text-center cursor-pointer hover:border-[var(--accent-amber)]/60 transition-colors"
        >
          <UploadCloud size={28} className="mx-auto text-[var(--text-muted)] mb-3" />
          <p className="text-sm font-medium">Drop a CSV file here, or click to browse</p>
          <p className="text-xs text-[var(--text-muted)] mt-1">Malformed rows and unknown devices are reported, not silently dropped</p>
          <input
            ref={fileInput}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
        </div>

        {uploading && <p className="text-sm text-[var(--text-secondary)] mt-3">Uploading and validating…</p>}

        {lastResult && (
          <div
            className={`mt-4 p-3 rounded-[var(--radius-sm)] text-sm border ${
              lastResult.ok
                ? 'bg-[var(--accent-teal)]/10 border-[var(--accent-teal)]/30 text-[var(--text-primary)]'
                : 'bg-[var(--accent-danger)]/10 border-[var(--accent-danger)]/30 text-[var(--accent-danger)]'
            }`}
          >
            {lastResult.ok ? (
              <>
                <p className="font-medium">{lastResult.rows_inserted} rows inserted</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1">{lastResult.notes}</p>
              </>
            ) : (
              <p>{lastResult.detail}</p>
            )}
          </div>
        )}
      </Panel>

      <Panel title="Upload history">
        {datasets.length === 0 ? (
          <EmptyState title="No datasets uploaded yet" />
        ) : (
          <div className="divide-y divide-[var(--border)] -m-5">
            {datasets.map((d) => {
              const style = STATUS_STYLES[d.status] || STATUS_STYLES.uploaded;
              const Icon = style.icon;
              return (
                <div key={d.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <Icon size={16} style={{ color: style.color }} />
                    <div>
                      <div className="text-sm font-medium">{d.filename}</div>
                      <div className="text-xs text-[var(--text-muted)]">{d.validation_notes || '—'}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-mono-data uppercase" style={{ color: style.color }}>{d.status}</div>
                    <div className="text-xs text-[var(--text-muted)]">{d.row_count ?? 0} rows</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
