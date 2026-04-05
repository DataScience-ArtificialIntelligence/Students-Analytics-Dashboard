import React from "react";

const OPTIONS = [
  { value: "marks", label: "Marks < 33%" },
  { value: "attendance", label: "Attendance < 75%" },
];

export default function RiskTypeSelect({ value, onChange }) {
  return (
    <label className="subject-select-wrap">
      <span className="subject-select-label">Filter</span>
      <select
        className="subject-select"
        value={value}
        onChange={e => onChange(e.target.value)}
      >
        {OPTIONS.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
