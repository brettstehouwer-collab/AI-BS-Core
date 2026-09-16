import React, { useState } from 'react';
import './AgentPlanReviewCard.css';

export default function AgentPlanReviewCard({ planData, onExecutePlan, onRequestRevisions }) {
  if (!planData) return null;

  const [approvedSteps, setApprovedSteps] = useState(planData.steps ? planData.steps.map(s => s.step_num) : []);

  const toggleStep = (stepNum) => {
    if (approvedSteps.includes(stepNum)) {
      setApprovedSteps(approvedSteps.filter(s => s !== stepNum));
    } else {
      setApprovedSteps([...approvedSteps, stepNum]);
    }
  };

  const handleExecute = () => {
    onExecutePlan(planData.plan_id, approvedSteps);
  };

  return (
    <div className="agent-plan-review-card">
      <div className="plan-header">
        <h3 className="plan-title">📜 {planData.title || "Implementation Plan"}</h3>
        <p className="plan-summary">{planData.summary}</p>
      </div>

      <div className="plan-files">
        <h4>📁 Affected Files</h4>
        <div className="file-pills">
          {planData.affected_files && planData.affected_files.map((file, idx) => (
            <span key={idx} className="file-pill">{file}</span>
          ))}
        </div>
      </div>

      <div className="plan-steps">
        <h4>🔢 Execution Steps</h4>
        <ul className="step-list">
          {planData.steps && planData.steps.map((step, idx) => (
            <li key={idx} className={`step-item ${approvedSteps.includes(step.step_num) ? 'approved' : 'rejected'}`}>
              <label>
                <input 
                  type="checkbox" 
                  checked={approvedSteps.includes(step.step_num)} 
                  onChange={() => toggleStep(step.step_num)}
                />
                <span className="step-desc"><strong>Step {step.step_num}:</strong> {step.description}</span>
                <span className={`step-risk risk-${step.risk?.toLowerCase() || 'unknown'}`}>{step.risk?.toUpperCase()}</span>
              </label>
            </li>
          ))}
        </ul>
      </div>

      <div className="plan-actions">
        <button className="btn-revise" onClick={onRequestRevisions}>
          ✏️ Request Revisions
        </button>
        <button className="btn-execute" onClick={handleExecute} disabled={approvedSteps.length === 0}>
          🚀 Accept & Execute Plan
        </button>
      </div>
    </div>
  );
}
