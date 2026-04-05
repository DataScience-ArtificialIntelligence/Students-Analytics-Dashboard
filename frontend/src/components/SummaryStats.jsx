import React from "react";
import { useApi } from "../hooks/useApi";
import SubjectSelect from "./SubjectSelect";

const ICONS = {
  total:       "◈",
  at_risk:     "⚠",
  avg_marks:   "◎",
  attendance:  "◷",
};

function StatCard({ icon, label, value, sub, accent }) {
  return (
    <div className={`stat-card ${accent ? "stat-card--accent" : ""}`}>
      <span className="stat-icon">{icon}</span>
      <div className="stat-body">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
        {sub && <span className="stat-sub">{sub}</span>}
      </div>
    </div>
  );
}

export default function SummaryStats({ subject, onSubjectChange }) {
  const { data, loading, error } = useApi(`/summary?subject=${encodeURIComponent(subject)}`);

  if (loading) return <div className="loading-row">Loading summary…</div>;
  if (error)   return <div className="error-row">Error: {error}</div>;

  const o = data.overall;

  return (
    <section className="summary-section">
      <div className="section-head">
        <h2 className="section-title">Overview</h2>
        <SubjectSelect value={subject} onChange={onSubjectChange} />
      </div>
      <div className="stats-grid">
        <StatCard icon={ICONS.total}      label="Total Students"    value={o.total_students} />
        <StatCard icon={ICONS.at_risk}    label="At-Risk Students"  value={o.at_risk_count}
                  sub={`${o.at_risk_pct}% of total`} accent />
        <StatCard icon={ICONS.avg_marks}  label={`${data.subject} Total Marks`}
                  value={o.subject_marks_mean}
                  sub={`${o.subject_marks_min} – ${o.subject_marks_max} · Risk < ${data.marks_threshold}`} />
        <StatCard icon={ICONS.attendance} label="Avg Attendance"
                  value={`${(o.attendance_mean * 100).toFixed(1)}%`} />
      </div>

      <h2 className="section-title" style={{ marginTop: "2.5rem" }}>Branch Breakdown</h2>
      <div className="branch-table-wrap">
        <table className="branch-table">
          <thead>
            <tr>
              <th>Branch</th><th>Students</th><th>At-Risk</th>
              <th>{data.subject} Avg Total</th><th>Avg Attendance</th>
            </tr>
          </thead>
          <tbody>
            {data.by_branch.map(b => (
              <tr key={b.branch}>
                <td><span className="branch-badge">{b.branch}</span></td>
                <td>{b.total}</td>
                <td className={b.at_risk > 0 ? "risk-cell" : ""}>{b.at_risk}</td>
                <td>{b.subject_marks}</td>
                <td>{(b.avg_attendance * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
