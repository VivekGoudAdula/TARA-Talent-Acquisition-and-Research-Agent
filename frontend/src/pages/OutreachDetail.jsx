import React, { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Calendar, Users, Megaphone, TrendingUp,
  UploadCloud, Phone, CheckCircle, AlertTriangle, FileText, X
} from 'lucide-react';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import SectionPanel from '../components/ui/SectionPanel';
import KpiCard from '../components/ui/KpiCard';
import PageHeader from '../components/ui/PageHeader';
import { ErrorState } from '../components/ui/States';
import { useCampaigns } from '../context/CampaignContext';

// ─── CSV Parser ────────────────────────────────────────────────────────────────

/**
 * Parse a raw CSV string into an array of objects keyed by header row.
 * Handles quoted fields and trims whitespace from all values.
 * @param {string} text - raw CSV file content
 * @returns {{ rows: object[], headers: string[], errors: string[] }}
 */
function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return { rows: [], headers: [], errors: ['CSV must have a header row and at least one data row.'] };

  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  const rows = [];
  const errors = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
    if (values.length !== headers.length) {
      errors.push(`Row ${i + 1}: column count mismatch — skipped.`);
      continue;
    }
    const obj = {};
    headers.forEach((h, idx) => { obj[h] = values[idx]; });

    // Normalise common field aliases to name / phone / email
    obj.name = obj.name || obj.Name || obj.full_name || obj['Full Name'] || obj.customer_name || `Contact ${i}`;
    obj.phone = obj.phone || obj.Phone || obj.mobile || obj.Mobile || obj.phone_number || '—';
    obj.email = obj.email || obj.Email || '—';

    rows.push(obj);
  }

  return { rows, headers, errors };
}

// ─── CSV Upload Panel ──────────────────────────────────────────────────────────

function CsvUploadPanel({ campaignId, onUpload }) {
  const fileInputRef = useRef(null);
  const [preview, setPreview] = useState(null);  // { rows, headers, errors }
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState(null);

  function readFile(file) {
    if (!file || !file.name.endsWith('.csv')) {
      alert('Please upload a valid .csv file.');
      return;
    }
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const parsed = parseCsv(e.target.result);
      setPreview(parsed);
    };
    reader.readAsText(file);
  }

  function handleFileChange(e) { readFile(e.target.files[0]); }
  function handleDrop(e) {
    e.preventDefault(); setDragOver(false);
    readFile(e.dataTransfer.files[0]);
  }

  function handleConfirm() {
    onUpload(preview.rows);
    setPreview(null);
    setFileName(null);
  }

  function handleClear() { setPreview(null); setFileName(null); }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      {!preview && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center cursor-pointer transition-colors ${
            dragOver ? 'border-primary-400 bg-primary-50' : 'border-neutral-300 hover:border-primary-300 hover:bg-neutral-50'
          }`}
        >
          <UploadCloud size={32} className={`mb-3 ${dragOver ? 'text-primary-500' : 'text-neutral-400'}`} />
          <p className="text-sm font-medium text-neutral-700">Drop a CSV file here, or click to browse</p>
          <p className="text-xs text-neutral-400 mt-1">
            Expected columns: <code className="bg-neutral-100 px-1 py-0.5 rounded text-neutral-600">name, phone, email</code> (others are accepted too)
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* Parse result */}
      {preview && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-primary-500" />
              <span className="text-sm font-medium text-neutral-800">{fileName}</span>
              <Badge variant="blue">{preview.rows.length} rows</Badge>
            </div>
            <button onClick={handleClear} className="p-1 hover:bg-neutral-100 rounded text-neutral-400">
              <X size={15} />
            </button>
          </div>

          {/* Parse errors */}
          {preview.errors.length > 0 && (
            <div className="p-3 rounded-md bg-warning-50 border border-warning-200 text-xs text-warning-700 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold"><AlertTriangle size={12} /> Parse warnings:</div>
              {preview.errors.map((err, i) => <div key={i}>• {err}</div>)}
            </div>
          )}

          {/* Preview table */}
          {preview.rows.length > 0 && (
            <div className="border border-neutral-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    {['Name', 'Phone', 'Email'].map(h => (
                      <th key={h} className="table-header">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.slice(0, 5).map((row, i) => (
                    <tr key={i} className="table-row">
                      <td className="table-cell font-medium">{row.name}</td>
                      <td className="table-cell">{row.phone}</td>
                      <td className="table-cell text-neutral-400">{row.email}</td>
                    </tr>
                  ))}
                  {preview.rows.length > 5 && (
                    <tr>
                      <td colSpan={3} className="px-4 py-2 text-xs text-neutral-400 text-center">
                        + {preview.rows.length - 5} more contacts
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {preview.rows.length > 0 && (
            <div className="flex justify-end gap-3">
              <button onClick={handleClear} className="btn btn-secondary">Discard</button>
              <button onClick={handleConfirm} className="btn btn-primary">
                <CheckCircle size={14} /> Upload {preview.rows.length} Contacts
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function OutreachDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { campaigns, addContactsToCampaign, launchCalls } = useCampaigns();
  const [launching, setLaunching] = useState(false);
  const [launched, setLaunched] = useState(false);

  const campaign = campaigns.find(c => c.campaign_id === id);

  if (!campaign) {
    return <ErrorState message="Campaign not found." />;
  }

  /** Upload parsed CSV contacts into the campaign. */
  function handleUpload(contacts) {
    addContactsToCampaign(id, contacts);
  }

  /** Launch calls for all pending leads and navigate to the monitor. */
  function handleLaunchCalls() {
    setLaunching(true);
    setTimeout(() => {
      launchCalls(id);
      setLaunching(false);
      setLaunched(true);
      // Navigate to Live Contact Monitor after short delay so user sees feedback
      setTimeout(() => navigate('/monitor'), 800);
    }, 1200);
  }

  const leads = campaign.assigned_leads || [];
  const hasPendingLeads = leads.some(l => l.status !== 'Converted');

  const columns = [
    { header: 'Lead Name', accessor: 'name', cell: row => <span className="font-medium">{row.name}</span> },
    {
      header: 'Status', accessor: 'status',
      cell: row => {
        const variant = row.status === 'Converted' ? 'green' : row.status === 'Pending' ? 'amber' : 'neutral';
        return <Badge variant={variant}>{row.status}</Badge>;
      }
    },
    { header: 'Contact', accessor: 'contact' },
    { header: 'Lead Score', accessor: 'score', cell: row => <span className="text-sm font-semibold">{row.score}</span> },
  ];

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/outreach')}
        className="btn btn-secondary btn-sm"
        title="Back to Campaigns"
      >
        <ArrowLeft size={14} /> Back
      </button>
      <PageHeader
        title={campaign.name}
        subtitle={
          <span className="flex items-center gap-2">
            <span>{campaign.product}</span>
            <span className="text-neutral-300">•</span>
            <Badge variant={campaign.status === 'Active' ? 'green' : campaign.status === 'Draft' ? 'neutral' : 'amber'}>
              {campaign.status}
            </Badge>
          </span>
        }
        actions={
          hasPendingLeads ? (
            <button
              onClick={handleLaunchCalls}
              disabled={launching || launched}
              className={`btn btn-primary flex items-center gap-2 ${launching || launched ? 'opacity-75 cursor-not-allowed' : ''}`}
            >
              {launching ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Launching…
                </>
              ) : launched ? (
                <><CheckCircle size={16} /> Calls Launched</>
              ) : (
                <><Phone size={16} /> Launch Calls</>
              )}
            </button>
          ) : null
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Target Audience" value={campaign.target_audience} icon={Users} color="blue" />
        <KpiCard label="Channel" value={campaign.channel} icon={Megaphone} color="amber" />
        <KpiCard label="Duration" value={`${campaign.start_date} → ${campaign.end_date}`} icon={Calendar} color="neutral" />
        <KpiCard label="Conversion Rate" value={`${campaign.conversion_rate}%`} icon={TrendingUp} color="green" />
      </div>

      {/* CSV Upload */}
      <SectionPanel
        title="Upload Contacts"
        subtitle="Upload a CSV file to add contacts to this campaign"
      >
        <CsvUploadPanel campaignId={id} onUpload={handleUpload} />
      </SectionPanel>

      {/* Assigned Leads table */}
      <SectionPanel
        title="Assigned Contacts"
        subtitle={`${leads.length.toLocaleString()} contact${leads.length !== 1 ? 's' : ''} in this campaign`}
        actions={
          hasPendingLeads && (
            <button
              onClick={handleLaunchCalls}
              disabled={launching || launched}
              className="btn btn-primary btn-sm"
            >
              <Phone size={12} /> Launch Calls
            </button>
          )
        }
      >
        <DataTable
          columns={columns}
          data={leads}
          pageSize={10}
          emptyMessage="No contacts yet — upload a CSV above to get started"
        />
      </SectionPanel>
    </div>
  );
}
