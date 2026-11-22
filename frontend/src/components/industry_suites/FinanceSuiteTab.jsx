import 'react';
import EconomicsSummaryPanel from '/src/components/EconomicsSummaryPanel.jsx';

/** @param {{backendUrl?: string}} props */
export default function FinanceSuiteTab({ backendUrl }) {
  return <EconomicsSummaryPanel title="Finance records" apiBase={backendUrl} />;
}
