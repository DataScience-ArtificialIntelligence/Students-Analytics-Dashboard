import React, { useState } from "react";
import { useApi } from "../hooks/useApi";
import SubjectSelect from "./SubjectSelect";
import RiskTypeSelect from "./RiskTypeSelect";

function RiskBar({ score }) {
  const pct = Math.round((score ?? 0) * 100);
  const color = pct > 75 ? "#ff2d55" : pct > 50 ? "#ff9f0a" : "#ffd60a";
  return (
    <div className="risk-bar-wrap">
      <div className="risk-bar-track">
        <div className="risk-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="risk-bar-label">{pct}%</span>
    </div>
  );
}

export default function AtRiskPanel({ subject, onSubjectChange }) {
  const { data, loading, error } = useApi(`/at-risk?subject=${encodeURIComponent(subject)}`);
  const [expanded, setExpanded]  = useState(null);
  const [search, setSearch] = useState("");
  const [riskType, setRiskType] = useState("marks");

  if (loading) return <div className="loading-row">Loading at-risk data…</div>;
  if (error)   return <div className="error-row">Error: {error}</div>;

  const students = data?.students ?? [];
  const filteredStudents = students.filter(student => {
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || (
      student.name.toLowerCase().includes(query)
      || String(student.student_id).includes(query)
    );
    const matchesRiskType = riskType === "marks"
      ? student.selected_marks < data.marks_threshold
      : student.attendance_pct < 0.75;
    return matchesSearch && matchesRiskType;
  });

  return (
    <section className="atrisk-section">
      <div className="atrisk-header">
        <h2 className="section-title">At-Risk Students</h2>
        <SubjectSelect value={subject} onChange={onSubjectChange} />
        <RiskTypeSelect value={riskType} onChange={setRiskType} />
        <span className="risk-count-badge">{filteredStudents.length} flagged</span>
      </div>

      <div className="filters-row">
        <input
          className="search-input"
          placeholder="Search student name or ID…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {filteredStudents.length === 0 ? (
        <div className="empty-state">✓ No students match this at-risk filter</div>
      ) : (
        <div className="risk-cards">
          {filteredStudents.map(s => (
            <div
              key={s.student_id}
              className={`risk-card ${expanded === s.student_id ? "risk-card--open" : ""}`}
              onClick={() => setExpanded(expanded === s.student_id ? null : s.student_id)}
            >
              <div className="risk-card-top">
                <div className="risk-card-info">
                  <span className="risk-card-name">{s.name}</span>
                  <span className="risk-card-meta">
                    {s.branch} · Year {s.year} · <span className="mono">{s.student_id}</span>
                  </span>
                </div>
                <div className="risk-card-score">
                  {s.risk_score != null && <RiskBar score={s.risk_score} />}
                </div>
                <span className="risk-card-chevron">{expanded === s.student_id ? "▲" : "▼"}</span>
              </div>

              {expanded === s.student_id && (
                <div className="risk-card-detail">
                  <div className="detail-row">
                    <span className="detail-label">{data.subject} Total Marks</span>
                    <span className={`detail-val ${s.selected_marks < data.marks_threshold ? "val-danger" : ""}`}>
                      {s.selected_marks}
                      {s.selected_marks < data.marks_threshold && ` ⚠ Below ${data.marks_threshold}`}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Attendance</span>
                    <span className={`detail-val ${s.attendance_pct < 0.75 ? "val-danger" : ""}`}>
                      {(s.attendance_pct * 100).toFixed(1)}%
                      {s.attendance_pct < 0.75 && " ⚠ Below 75%"}
                    </span>
                  </div>
                  <div className="risk-reasons">
                    <strong>Reasons flagged:</strong>
                    <ul>
                      {s.selected_marks < data.marks_threshold && (
                        <li>{data.subject} total marks below 33% threshold ({data.marks_threshold}/{data.subject_max_marks})</li>
                      )}
                      {s.attendance_pct < 0.75 && <li>Attendance below 75%</li>}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
