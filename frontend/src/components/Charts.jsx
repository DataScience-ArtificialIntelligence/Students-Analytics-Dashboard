import React from "react";
import { Bar } from "react-chartjs-2";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { useApi } from "../hooks/useApi";
import SubjectSelect from "./SubjectSelect";
import RiskTypeSelect from "./RiskTypeSelect";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
);

const AXIS_TICK_COLOR = "#888";
const GRID_COLOR = "rgba(255,255,255,0.06)";
const THRESHOLD_COLOR = "#ff4757";
const SAFE_COLOR = "#2ed573";

function buildBarData(students, riskType, marksThreshold) {
  const grouped = students.reduce((acc, student) => {
    const branch = student.branch;
    if (!acc[branch]) {
      acc[branch] = { total: 0, atRisk: 0 };
    }

    acc[branch].total += 1;
    const isAtRisk = riskType === "marks"
      ? student.selected_marks < marksThreshold
      : student.attendance_pct < 0.75;
    if (isAtRisk) {
      acc[branch].atRisk += 1;
    }

    return acc;
  }, {});

  const labels = Object.keys(grouped);
  const safeCounts = labels.map(branch => grouped[branch].total - grouped[branch].atRisk);
  const atRiskCounts = labels.map(branch => grouped[branch].atRisk);

  return {
    labels,
    datasets: [
      {
        label: "Safe",
        data: safeCounts,
        backgroundColor: SAFE_COLOR,
        borderRadius: 4,
        stack: "students",
      },
      {
        label: "At-Risk",
        data: atRiskCounts,
        backgroundColor: THRESHOLD_COLOR,
        borderRadius: 4,
        stack: "students",
      },
    ],
  };
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: AXIS_TICK_COLOR,
      },
    },
    tooltip: {
      callbacks: {
        label(context) {
          return `${context.dataset.label}: ${context.parsed.y}`;
        },
      },
    },
  },
  scales: {
    x: {
      stacked: true,
      ticks: { color: AXIS_TICK_COLOR },
      grid: { color: GRID_COLOR, display: false },
    },
    y: {
      stacked: true,
      beginAtZero: true,
      ticks: { color: AXIS_TICK_COLOR, precision: 0 },
      grid: { color: GRID_COLOR },
    },
  },
};

export default function Charts({ subject, onSubjectChange }) {
  const { data, loading, error } = useApi(`/data?subject=${encodeURIComponent(subject)}`);
  const [riskType, setRiskType] = React.useState("marks");

  if (loading) return <div className="loading-row">Loading charts…</div>;
  if (error) return <div className="error-row">Error: {error}</div>;

  const students = data?.students ?? [];
  const marksThreshold = data?.marks_threshold ?? 33;
  const branchBarData = buildBarData(students, riskType, marksThreshold);
  const riskSubtitle = riskType === "marks"
    ? `${subject} totals under the 33% risk line`
    : "attendance under 75%";

  return (
    <section className="charts-section">
      <div className="section-head">
        <h2 className="section-title">Performance Analysis</h2>
        <SubjectSelect value={subject} onChange={onSubjectChange} />
        <RiskTypeSelect value={riskType} onChange={setRiskType} />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3 className="chart-title">Safe vs At-Risk by Branch</h3>
          <p className="chart-subtitle">Counts based on {riskSubtitle}</p>
          <div className="chart-canvas-wrap">
            <Bar data={branchBarData} options={barOptions} />
          </div>
        </div>
      </div>
    </section>
  );
}
