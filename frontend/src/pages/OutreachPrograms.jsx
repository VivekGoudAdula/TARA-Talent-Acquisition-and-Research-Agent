import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Megaphone, Target, CheckCircle, BarChart3, Plus, X } from 'lucide-react';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import SectionPanel from '../components/ui/SectionPanel';
import KpiCard from '../components/ui/KpiCard';
import PageHeader from '../components/ui/PageHeader';
import { useCampaigns } from '../context/CampaignContext';

const CHANNELS = ['Email', 'SMS', 'WhatsApp', 'Voice', 'Multi-Channel'];

// ─── New Campaign Modal ────────────────────────────────────────────────────────

function NewCampaignModal({ onClose, onSave }) {
  const [form, setForm] = useState({
    name: '',
    product: '',
    target_audience: '',
    channel: 'Email',
    start_date: '',
    end_date: '',
  });
  const [errors, setErrors] = useState({});

  /** Update a single form field. */
  function handleChange(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }));
  }

  /** Validate required fields before saving. */
  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = 'Campaign name is required.';
    if (!form.product.trim()) e.product = 'Product is required.';
    if (!form.target_audience.trim()) e.target_audience = 'Target audience is required.';
    if (!form.start_date) e.start_date = 'Start date is required.';
    if (!form.end_date) e.end_date = 'End date is required.';
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      e.end_date = 'End date must be after start date.';
    }
    return e;
  }

  function handleSubmit(e) {
    e.preventDefault();
    const e2 = validate();
    if (Object.keys(e2).length > 0) { setErrors(e2); return; }
    onSave(form);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
          <div>
            <h2 className="text-base font-bold text-neutral-900">New Campaign</h2>
            <p className="text-xs text-neutral-400 mt-0.5">Fill in the details below to create a new outreach campaign.</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-neutral-100 text-neutral-500 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <label className="form-label">Campaign Name *</label>
            <input
              className={`form-input ${errors.name ? 'border-danger-400' : ''}`}
              placeholder="e.g. Q4 Home Loan Blitz"
              value={form.name}
              onChange={e => handleChange('name', e.target.value)}
            />
            {errors.name && <p className="text-xs text-danger-500 mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="form-label">Product *</label>
            <input
              className={`form-input ${errors.product ? 'border-danger-400' : ''}`}
              placeholder="e.g. Home Loan, Credit Card"
              value={form.product}
              onChange={e => handleChange('product', e.target.value)}
            />
            {errors.product && <p className="text-xs text-danger-500 mt-1">{errors.product}</p>}
          </div>

          <div>
            <label className="form-label">Target Audience *</label>
            <input
              className={`form-input ${errors.target_audience ? 'border-danger-400' : ''}`}
              placeholder="e.g. Salaried Metro Professionals"
              value={form.target_audience}
              onChange={e => handleChange('target_audience', e.target.value)}
            />
            {errors.target_audience && <p className="text-xs text-danger-500 mt-1">{errors.target_audience}</p>}
          </div>

          <div>
            <label className="form-label">Outreach Channel</label>
            <select
              className="form-select"
              value={form.channel}
              onChange={e => handleChange('channel', e.target.value)}
            >
              {CHANNELS.map(ch => <option key={ch}>{ch}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="form-label">Start Date *</label>
              <input
                type="date"
                className={`form-input ${errors.start_date ? 'border-danger-400' : ''}`}
                value={form.start_date}
                onChange={e => handleChange('start_date', e.target.value)}
              />
              {errors.start_date && <p className="text-xs text-danger-500 mt-1">{errors.start_date}</p>}
            </div>
            <div>
              <label className="form-label">End Date *</label>
              <input
                type="date"
                className={`form-input ${errors.end_date ? 'border-danger-400' : ''}`}
                value={form.end_date}
                onChange={e => handleChange('end_date', e.target.value)}
              />
              {errors.end_date && <p className="text-xs text-danger-500 mt-1">{errors.end_date}</p>}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2 border-t border-neutral-100">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" className="btn btn-primary">
              <Plus size={14} /> Create Campaign
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function OutreachPrograms() {
  const navigate = useNavigate();
  const { campaigns, addCampaign } = useCampaigns();
  const [showModal, setShowModal] = useState(false);

  const activeCount = campaigns.filter(c => c.status === 'Active').length;
  const totalLeads = campaigns.reduce((sum, c) => sum + c.qualified_leads, 0);
  const avg = campaigns.length > 0
    ? (campaigns.reduce((sum, c) => sum + c.conversion_rate, 0) / campaigns.length).toFixed(1)
    : '0.0';

  /** Handle modal save — create the campaign then navigate to its detail page. */
  function handleSave(formData) {
    const created = addCampaign(formData);
    setShowModal(false);
    navigate(`/outreach/${created.campaign_id}`);
  }

  const columns = [
    {
      header: 'Campaign Name', accessor: 'name',
      cell: row => <div className="font-medium text-neutral-800">{row.name}</div>
    },
    { header: 'Product', accessor: 'product' },
    {
      header: 'Target Audience', accessor: 'target_audience',
      cell: row => <span className="text-xs text-neutral-600">{row.target_audience}</span>
    },
    { header: 'Channel', accessor: 'channel', cell: row => <Badge>{row.channel}</Badge> },
    {
      header: 'Status', accessor: 'status',
      cell: row => {
        const variant = row.status === 'Active' ? 'green' : row.status === 'Completed' ? 'blue' : row.status === 'Draft' ? 'neutral' : 'amber';
        return <Badge variant={variant}>{row.status}</Badge>;
      }
    },
    { header: 'Start Date', accessor: 'start_date' },
    { header: 'End Date', accessor: 'end_date' },
    {
      header: 'Qualified Leads', accessor: 'qualified_leads',
      cell: row => row.qualified_leads.toLocaleString()
    },
    {
      header: 'Conversion', accessor: 'conversion_rate',
      cell: row => <span className="font-semibold">{row.conversion_rate}%</span>
    },
  ];

  return (
    <>
      {showModal && (
        <NewCampaignModal
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}

      <div className="space-y-6">
        <PageHeader
          title="Outreach Programs"
          subtitle="Manage and track campaign performance."
          actions={
            <button onClick={() => setShowModal(true)} className="btn btn-primary">
              <Plus size={16} /> New Campaign
            </button>
          }
        />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Total Campaigns" value={campaigns.length} icon={Megaphone} color="blue" />
          <KpiCard label="Active Programs" value={activeCount} icon={Target} color="green" />
          <KpiCard label="Total Leads Reached" value={totalLeads.toLocaleString()} icon={CheckCircle} color="amber" />
          <KpiCard label="Avg Conversion" value={`${avg}%`} icon={BarChart3} color="blue" />
        </div>

        <SectionPanel
          title="Campaigns Dashboard"
          subtitle="Click any campaign to view details, upload contacts, and launch calls"
        >
          <DataTable
            columns={columns}
            data={campaigns}
            onRowClick={row => navigate(`/outreach/${row.campaign_id}`)}
            pageSize={10}
            emptyMessage="No outreach programs found — create one to get started"
          />
        </SectionPanel>
      </div>
    </>
  );
}
