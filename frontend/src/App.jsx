import React, { useState } from "react";
import SummaryStats  from "./components/SummaryStats";
import StudentTable  from "./components/StudentTable";
import AtRiskPanel   from "./components/AtRiskPanel";
import Charts        from "./components/Charts";
import SubjectSelect from "./components/SubjectSelect";
import "./App.css";

const TABS = [
  { id: "overview",  label: "Overview",      icon: "◈" },
  { id: "students",  label: "All Students",  icon: "◉" },
  { id: "atrisk",    label: "At-Risk",       icon: "⚠" },
  { id: "charts",    label: "Analytics",     icon: "◎" },
];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [subject, setSubject] = useState("BDA");

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-icon">⬡</span>
          <div>
            <div className="brand-title">EduPulse</div>
            <div className="brand-sub">Student Performance Analytics · Hadoop + Spark + ML</div>
          </div>
        </div>
        <div className="header-status">
          <SubjectSelect value={subject} onChange={setSubject} compact />
          <span className="status-dot" />
          <span>Live</span>
        </div>
      </header>

      {/* Nav */}
      <nav className="app-nav">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`nav-tab ${tab === t.id ? "nav-tab--active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <span className="nav-icon">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="app-main">
        {tab === "overview"  && <SummaryStats subject={subject} onSubjectChange={setSubject} />}
        {tab === "students"  && <StudentTable subject={subject} onSubjectChange={setSubject} />}
        {tab === "atrisk"    && <AtRiskPanel subject={subject} onSubjectChange={setSubject} />}
        {tab === "charts"    && <Charts subject={subject} onSubjectChange={setSubject} />}
      </main>

      <footer className="app-footer">
        EduPulse · CSE / DSAI / ECE · Subjects: BDA · DL · DSP · DBMS
      </footer>
    </div>
  );
}
