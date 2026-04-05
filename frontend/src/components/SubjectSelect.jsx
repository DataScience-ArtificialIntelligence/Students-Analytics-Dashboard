import React from "react";
import { SUBJECTS } from "../constants/subjects";

export default function SubjectSelect({ value, onChange, compact = false }) {
  return (
    <label className={`subject-select-wrap ${compact ? "subject-select-wrap--compact" : ""}`}>
      <span className="subject-select-label">Subject</span>
      <select
        className="subject-select"
        value={value}
        onChange={e => onChange(e.target.value)}
      >
        {SUBJECTS.map(subject => (
          <option key={subject} value={subject}>
            {subject}
          </option>
        ))}
      </select>
    </label>
  );
}
