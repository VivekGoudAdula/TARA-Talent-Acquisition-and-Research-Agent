import React, { useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, User, DollarSign, Activity, Heart, RefreshCw, FileText, CheckCircle } from 'lucide-react';
import SectionPanel, { FieldRow, ScoreBar } from '../components/ui/SectionPanel';
import PageHeader from '../components/ui/PageHeader';
import Badge from '../components/ui/Badge';
import DataTable from '../components/ui/DataTable';
import { PageSpinner, ErrorState } from '../components/ui/States';
import {
  useCrmCustomer,
  useCustomer360,
  useFinancial,
  useBehaviour,
  useRelationship,
  useTransactions,
  useBehaviourSummary,
  useExplainReport,
  useExternalProfile,
  useExternalAnalytics,
  useExternalIntelligence
} from '../api/hooks';
import { mergeBehaviourProfile, mergeRelationshipProfile, buildDummyExplainReport } from '../api/dummyData';

export default function CustomerDetail() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const isExternal = location.pathname.startsWith('/lead');
  const [activeTab, setActiveTab] = useState('360');

  // Queries for internal customer
  const crmCustomer = useCrmCustomer(!isExternal ? id : null);
  const c360 = useCustomer360(!isExternal ? id : null);
  const financial = useFinancial(!isExternal ? id : null);
  const behaviour = useBehaviour(id);
  const relationship = useRelationship(id);
  const transactions = useTransactions(!isExternal ? id : null);
  const summary = useBehaviourSummary(!isExternal ? id : null);

  // Queries for external lead
  const extProfile = useExternalProfile(isExternal ? id : null);
  const extAnalytics = useExternalAnalytics(isExternal ? id : null);
  const extIntel = useExternalIntelligence(isExternal ? id : null);

  // Shared explainability
  const explain = useExplainReport(id);

  const isLoading = isExternal
    ? extProfile.isLoading
    : (crmCustomer.isLoading || c360.isLoading);

  if (isLoading) return <PageSpinner />;

  // Resolve profile details based on customer type
  const profile = isExternal ? extProfile.data : c360.data;
  const name = isExternal
    ? (profile?.lead_profile?.full_name || 'External Lead')
    : (crmCustomer.data?.full_name || crmCustomer.data?.lead?.full_name || profile?.personal_info?.full_name || 'Internal Customer');

  const tabs = isExternal
    ? [
        { id: '360', label: 'Lead Profile' },
        { id: 'behaviour', label: 'Behaviour' },
        { id: 'relationship', label: 'Relationship' },
        { id: 'analytics', label: 'Analytics' },
        { id: 'intel', label: 'Intelligence' },
        { id: 'explain', label: 'AI Explainability' },
        { id: 'timeline', label: 'Engagement Timeline' }
      ]
    : [
        { id: '360', label: 'Customer 360' },
        { id: 'financial', label: 'Financial Profiles' },
        { id: 'behaviour', label: 'Behaviour' },
        { id: 'relationship', label: 'Relationship' },
        { id: 'transactions', label: 'Transactions' },
        { id: 'explain', label: 'AI Explainability' },
        { id: 'timeline', label: 'Engagement Timeline' }
      ];

  const profileCtx = { id, name, isExternal };

  const renderBehaviourPanels = (bd) => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <SectionPanel title={isExternal ? 'Lead Digital Behaviour' : 'Digital Engagement'}>
        <FieldRow label="Digital Platform Usage" value={<Badge>{bd.digital_adoption_tier || '—'}</Badge>} />
        <FieldRow label={isExternal ? 'Avg Touchpoints/Month' : 'Avg Logins/Month'} value={bd.monthly_login_frequency} />
        <FieldRow label="Preferred Channel" value={bd.preferred_transaction_channel} />
        <FieldRow label="Last Activity Date" value={bd.last_transaction_date ? new Date(bd.last_transaction_date).toLocaleDateString() : '—'} />
        {bd.top_interest && <FieldRow label="Top Interest" value={bd.top_interest} />}
      </SectionPanel>

      <SectionPanel title="Campaign Response & Feedback">
        <FieldRow label="Email Open Rate" value={bd.email_open_rate != null ? `${(bd.email_open_rate * 100).toFixed(0)}%` : '—'} />
        <FieldRow label="SMS Click Rate" value={bd.sms_click_rate != null ? `${(bd.sms_click_rate * 100).toFixed(0)}%` : '—'} />
        <FieldRow label="Ad Clicks (Social)" value={bd.social_media_click_count} />
        <FieldRow label="Last Outreach Outcome" value={<Badge>{bd.last_call_outcome || '—'}</Badge>} />
      </SectionPanel>

      {(bd.shopping_score != null || bd.investment_score != null) && (
        <SectionPanel title="Behaviour Category Scores" className="md:col-span-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {bd.shopping_score != null && <ScoreBar label="Shopping" value={bd.shopping_score} max={100} color="primary" />}
            {bd.travel_score != null && <ScoreBar label="Travel" value={bd.travel_score} max={100} color="primary" />}
            {bd.food_score != null && <ScoreBar label="Food & Dining" value={bd.food_score} max={100} color="green" />}
            {bd.investment_score != null && <ScoreBar label="Investments" value={bd.investment_score} max={100} color="green" />}
            {bd.entertainment_score != null && <ScoreBar label="Entertainment" value={bd.entertainment_score} max={100} color="amber" />}
            {bd.healthcare_score != null && <ScoreBar label="Healthcare" value={bd.healthcare_score} max={100} color="amber" />}
          </div>
          {bd.lifestyle_tags?.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {bd.lifestyle_tags.map(tag => <Badge key={tag}>{tag}</Badge>)}
            </div>
          )}
        </SectionPanel>
      )}
    </div>
  );

  const renderRelationshipPanels = (rd) => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <SectionPanel title={isExternal ? 'Prospect Relationship Value' : 'Bank Relationship Value'}>
        <FieldRow
          label="Relationship Tenure"
          value={rd.tenure_months ? `${rd.tenure_months} months` : (isExternal ? 'New Prospect' : '—')}
        />
        <FieldRow label="Active Products Count" value={rd.active_products_count ?? (isExternal ? 0 : '—')} />
        <FieldRow label="Customer Lifetime Value (CLV)" value={rd.clv_score ? `₹${Number(rd.clv_score).toLocaleString('en-IN')}` : '—'} />
        <FieldRow label="Relationship Strength" value={<Badge>{rd.relationship_strength_level || '—'}</Badge>} />
        {rd.cross_sell_potential && (
          <FieldRow label="Cross-sell Potential" value={<Badge variant="blue">{rd.cross_sell_potential}</Badge>} />
        )}
      </SectionPanel>

      <SectionPanel title={isExternal ? 'Engagement & Fit' : 'Risk Profile'}>
        <FieldRow label="Risk Rating" value={<Badge>{rd.risk_rating || '—'}</Badge>} />
        <FieldRow
          label={isExternal ? 'Engagement Score' : 'Churn Probability'}
          value={
            isExternal
              ? (rd.engagement_score != null ? `${rd.engagement_score}%` : '—')
              : (rd.churn_probability != null ? `${(rd.churn_probability * 100).toFixed(1)}%` : '—')
          }
        />
        <FieldRow label={isExternal ? 'Relationship Potential' : 'NPS Score'} value={isExternal ? rd.relationship_potential : rd.nps_score} />
        {rd.loyalty_score != null && <FieldRow label="Loyalty Score" value={`${rd.loyalty_score}%`} />}
        {rd.product_penetration_score != null && (
          <FieldRow label="Product Penetration" value={`${rd.product_penetration_score}%`} />
        )}
      </SectionPanel>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case '360':
        if (isExternal) {
          const lp = profile?.lead_profile || {};
          const statusInfo = profile?.enrichment_status || {};
          return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <SectionPanel title="Personal Details">
                <FieldRow label="Full Name" value={lp.full_name} />
                <FieldRow label="Email Address" value={lp.email} />
                <FieldRow label="Phone Number" value={lp.phone_number} />
                <FieldRow label="Age / Gender" value={`${lp.age || '—'} / ${lp.gender || '—'}`} />
                <FieldRow label="City / State" value={`${lp.city || '—'}, ${lp.state || '—'}`} />
                <FieldRow label="Preferred Language" value={lp.preferred_language} />
              </SectionPanel>

              <SectionPanel title="Lead Status">
                <FieldRow label="Status" value={<Badge>{lp.lead_status}</Badge>} />
                <FieldRow label="Campaign" value={lp.campaign} />
                <FieldRow label="Referral Source" value={lp.referral_source} />
                <FieldRow label="Consent Granted" value={<Badge>{lp.consent ? 'Yes' : 'No'}</Badge>} />
                <FieldRow label="Enrichment Status" value={<Badge>{statusInfo.status}</Badge>} />
                <FieldRow label="Last Processed" value={statusInfo.last_processed ? new Date(statusInfo.last_processed).toLocaleString() : '—'} />
              </SectionPanel>
            </div>
          );
        } else {
          // Internal Customer 360
          const pi = profile?.personal_info || {};
          const score = profile?.intelligence_scores || {};
          const alerts = profile?.system_alerts || [];
          return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <SectionPanel title="Personal Information">
                <FieldRow label="Full Name" value={pi.full_name} />
                <FieldRow label="Gender / Age" value={`${pi.gender || '—'} / ${pi.age || '—'}`} />
                <FieldRow label="Occupation" value={pi.occupation} />
                <FieldRow label="Monthly Income" value={pi.monthly_income ? `₹${Number(pi.monthly_income).toLocaleString('en-IN')}` : '—'} />
                <FieldRow label="Address" value={`${pi.city || '—'}, ${pi.state || '—'}`} />
                <FieldRow label="Language" value={pi.preferred_language} />
              </SectionPanel>

              <SectionPanel title="Intelligence Scores">
                <div className="space-y-4">
                  <ScoreBar label="Credit Score" value={score.credit_score} max={900} color="primary" />
                  <ScoreBar label="Financial Health" value={score.financial_health_score} max={100} color="green" />
                  <ScoreBar label="Repayment Score" value={score.repayment_behaviour_score} max={100} color="green" />
                  <ScoreBar label="Digital Adoption" value={score.digital_adoption_score} max={100} color="primary" />
                  <ScoreBar label="Relationship Strength" value={score.relationship_strength_score} max={100} color="green" />
                </div>
              </SectionPanel>

              {alerts.length > 0 && (
                <SectionPanel title="Active Alerts" className="md:col-span-2">
                  <div className="space-y-2">
                    {alerts.map((al, idx) => (
                      <div key={idx} className="flex items-center gap-2 p-3 bg-danger-50 text-danger-600 rounded text-sm font-medium">
                        <span>⚠️</span>
                        <span>{al}</span>
                      </div>
                    ))}
                  </div>
                </SectionPanel>
              )}
            </div>
          );
        }

      case 'financial':
        if (financial.isLoading) return <PageSpinner />;
        const fd = financial.data || {};
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SectionPanel title="Income & Wealth Metrics">
              <FieldRow label="Monthly Income" value={fd.monthly_income ? `₹${Number(fd.monthly_income).toLocaleString()}` : '—'} />
              <FieldRow label="Annual Income" value={fd.annual_income ? `₹${Number(fd.annual_income).toLocaleString()}` : '—'} />
              <FieldRow label="Estimated Wealth" value={fd.estimated_net_worth ? `₹${Number(fd.estimated_net_worth).toLocaleString()}` : '—'} />
              <FieldRow label="EMI Burden" value={fd.emi_burden_ratio ? `${(fd.emi_burden_ratio * 100).toFixed(1)}%` : '—'} />
            </SectionPanel>

            <SectionPanel title="Accounts Details">
              <FieldRow label="Savings Balance" value={fd.savings_balance ? `₹${Number(fd.savings_balance).toLocaleString()}` : '—'} />
              <FieldRow label="Investments Balance" value={fd.investments_balance ? `₹${Number(fd.investments_balance).toLocaleString()}` : '—'} />
              <FieldRow label="Outstanding Loans" value={fd.total_loan_outstanding ? `₹${Number(fd.total_loan_outstanding).toLocaleString()}` : '—'} />
              <FieldRow label="Repayment Capacity" value={<Badge>{fd.repayment_capacity_class}</Badge>} />
            </SectionPanel>
          </div>
        );

      case 'behaviour': {
        if (behaviour.isLoading) return <PageSpinner />;
        const bd = mergeBehaviourProfile(behaviour.isError ? null : behaviour.data, profileCtx);
        return renderBehaviourPanels(bd);
      }

      case 'relationship': {
        if (relationship.isLoading) return <PageSpinner />;
        const rd = mergeRelationshipProfile(relationship.isError ? null : relationship.data, profileCtx);
        return renderRelationshipPanels(rd);
      }

      case 'transactions':
        if (transactions.isLoading) return <PageSpinner />;
        const txs = transactions.data || [];
        const columns = [
          { header: 'Transaction ID', accessor: 'transaction_id' },
          { header: 'Date', accessor: 'date', cell: row => new Date(row.date).toLocaleString() },
          { header: 'Amount', accessor: 'amount', cell: row => `₹${Number(row.amount).toLocaleString()}` },
          { header: 'Category', accessor: 'category' },
          { header: 'Type', accessor: 'transaction_type', cell: row => <Badge variant={row.transaction_type === 'credit' ? 'green' : 'amber'}>{row.transaction_type}</Badge> },
          { header: 'Merchant', accessor: 'merchant' },
          { header: 'Channel', accessor: 'channel' }
        ];
        return (
          <SectionPanel title="Recent Transactions">
            <DataTable columns={columns} data={txs} pageSize={10} searchable={false} />
          </SectionPanel>
        );

      case 'analytics':
        if (extAnalytics.isLoading) return <PageSpinner />;
        const ad = extAnalytics.data || {};
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SectionPanel title="Lead Financial Analytics">
              <FieldRow label="Credit Score Band" value={<Badge>{ad.credit_score_band}</Badge>} />
              <FieldRow label="Income Category" value={ad.income_category} />
              <FieldRow label="Debt Capacity Estimate" value={ad.estimated_debt_capacity ? `₹${Number(ad.estimated_debt_capacity).toLocaleString()}` : '—'} />
            </SectionPanel>

            <SectionPanel title="Engagement Analytics">
              <FieldRow label="Conversion Probability" value={ad.conversion_probability != null ? `${Number(ad.conversion_probability) <= 1 ? (Number(ad.conversion_probability) * 100).toFixed(1) : Number(ad.conversion_probability).toFixed(1)}%` : '—'} />
              <FieldRow label="Best Contact Channel" value={ad.best_contact_channel} />
              <FieldRow label="Recommended Campaign" value={ad.recommended_campaign} />
            </SectionPanel>
          </div>
        );

      case 'intel':
        if (extIntel.isLoading) return <PageSpinner />;
        const intelData = extIntel.data || {};
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SectionPanel title="KYC & Identity Verification">
              <FieldRow label="KYC Readiness" value={<Badge>{intelData.kyc_readiness}</Badge>} />
              <FieldRow label="Lead Authenticity Score" value={intelData.lead_authenticity_score != null ? `${intelData.lead_authenticity_score}%` : '—'} />
              <FieldRow label="Fraud Screening Check" value={<Badge>{intelData.fraud_screening_result}</Badge>} />
            </SectionPanel>

            <SectionPanel title="Income Verification">
              <FieldRow label="Self-Reported Income" value={intelData.reported_income ? `₹${Number(intelData.reported_income).toLocaleString()}` : '—'} />
              <FieldRow label="Income Confidence Score" value={intelData.income_confidence_score != null ? `${intelData.income_confidence_score}%` : '—'} />
              <FieldRow label="Income Verification Method" value={intelData.income_verification_method} />
            </SectionPanel>
          </div>
        );

      case 'explain': {
        if (explain.isLoading) return <PageSpinner />;
        if (explain.isError) return <ErrorState message="No Explainable AI report found for this profile." />;

        const explainCtx = {
          id,
          customer_id: id,
          entity_id: id,
          full_name: name,
          name,
          isExternal,
          profile_type: isExternal ? 'External' : 'Internal',
          recommended_product: isExternal
            ? (extAnalytics.data?.recommended_campaign || profile?.recommended_product)
            : (crmCustomer.data?.recommended_product || profile?.recommended_product),
          recommended_campaign: extAnalytics.data?.recommended_campaign,
          conversion_probability: isExternal
            ? extAnalytics.data?.conversion_probability
            : crmCustomer.data?.conversion_probability,
          repayment_capacity: isExternal
            ? (extAnalytics.data?.credit_score_band || 'Medium')
            : (crmCustomer.data?.repayment_capacity || financial.data?.repayment_capacity_class),
        };
        const apiReport = explain.data;
        if (!apiReport) return <ErrorState message="No Explainable AI report found for this profile in the database. Please run the Explainability Pipeline first." />;
        const exp = apiReport;
        const narrative = exp.narrative || exp.explanation?.summary || '';
        const reasonCodes = exp.reason_codes || [];

        return (
          <div className="space-y-6">
            <SectionPanel title="narrative summary" subtitle="AI generated explainability report">
              <div className="text-sm leading-relaxed text-neutral-700 whitespace-pre-line bg-neutral-50 p-4 rounded border border-neutral-200">
                {narrative}
              </div>
            </SectionPanel>

            {reasonCodes.length > 0 && (
              <SectionPanel title="Reason Codes & Feature Factors">
                <div className="space-y-2">
                  {reasonCodes.map((rc, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 bg-white border border-neutral-200 rounded">
                      <span className="text-primary-500 font-bold">#{rc.code}</span>
                      <div>
                        <div className="text-sm font-semibold text-neutral-800">{rc.feature}</div>
                        <div className="text-xs text-neutral-500 mt-0.5">{rc.explanation}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </SectionPanel>
            )}
          </div>
        );
      }

      case 'timeline': {
        const events = profile?.engagement?.events || [];
        const columns = [
          { header: 'Date', accessor: 'created_at', cell: row => new Date(row.created_at).toLocaleString() },
          { header: 'Channel', accessor: 'channel', cell: row => <Badge>{row.channel}</Badge> },
          { header: 'Recipient', accessor: 'recipient' },
          { header: 'Status', accessor: 'status', cell: row => <Badge variant={row.success ? 'green' : 'danger'}>{row.status}</Badge> },
          { header: 'Message / Event Details', accessor: 'message_preview' }
        ];
        return (
          <SectionPanel title="Engagement & Campaign History" subtitle="Live history of sent messages, emails, and voice interactions">
            {events.length === 0 ? (
              <div className="text-center py-6 text-neutral-400 text-sm">No outreach events recorded for this profile yet.</div>
            ) : (
              <DataTable columns={columns} data={events} pageSize={10} searchable={false} />
            )}
          </SectionPanel>
        );
      }

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <button className="btn btn-secondary btn-sm" onClick={() => navigate(-1)}>
        <ArrowLeft size={14} /> Back
      </button>
      <PageHeader
        title={name}
        subtitle={isExternal ? 'Enriched External Lead' : 'Unified SBI Customer Profile'}
      />

      {/* Tabs */}
      <div className="flex border-b border-neutral-200">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab ${activeTab === tab.id ? 'tab-active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content wrapper */}
      <div className="min-h-[300px]">
        {renderTabContent()}
      </div>
    </div>
  );
}
