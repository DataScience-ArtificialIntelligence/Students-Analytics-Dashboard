import React, { useState, useMemo, useEffect } from "react";
import { useApi } from "../hooks/useApi";
import SubjectSelect from "./SubjectSelect";

const BRANCHES = ["ALL", "CSE", "DSAI", "ECE"];

export default function StudentTable({ subject, onSubjectChange }) {
  const { data, loading, error } = useApi(`/data?subject=${encodeURIComponent(subject)}`);

  const [search, setSearch]   = useState("");
  const [branch, setBranch]   = useState("ALL");
  const [sortKey, setSortKey] = useState("student_id");
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage]       = useState(1);

  const PAGE_SIZE = 15;

  // ✅ Safe access (important)
  const students = data?.students ?? [];

  // ✅ Filtering + sorting
  const filtered = useMemo(() => {
    let list = [...students];

    if (branch !== "ALL") {
      list = list.filter(s => s.branch === branch);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(s =>
        s.name.toLowerCase().includes(q) ||
        String(s.student_id).includes(q)   // ✅ FIXED HERE
      );
    }

    // ✅ Safer sorting
    list.sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";

      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return list;
  }, [students, branch, search, sortKey, sortDir]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [subject]);

  const handleSort = key => {
    if (key === sortKey) {
      setSortDir(d => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(1);
  };

  const arrow = key =>
    sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : "";

  // ✅ Loading / error states
  if (loading) return <div className="loading-row">Loading students…</div>;
  if (error)   return <div className="error-row">Error: {error}</div>;

  return (
    <section className="table-section">
      <div className="section-head">
        <h2 className="section-title">All Students</h2>
        <SubjectSelect value={subject} onChange={onSubjectChange} />
      </div>

      {/* Filters */}
      <div className="filters-row">
        <input
          className="search-input"
          placeholder="Search name or ID…"
          value={search}
          onChange={e => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />

        <div className="filter-group">
          {BRANCHES.map(b => (
            <button
              key={b}
              className={`filter-btn ${branch === b ? "active" : ""}`}
              onClick={() => {
                setBranch(b);
                setPage(1);
              }}
            >
              {b}
            </button>
          ))}
        </div>

        <span className="result-count">
          {filtered.length} students
        </span>
      </div>

      {/* Table */}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {[
                ["student_id", "ID"],
                ["name", "Name"],
                ["branch", "Branch"],
                ["year", "Year"],
                ["selected_marks", `${subject} Total`],
                ["attendance_pct", "Attendance"],
                ["subject_risk", "Status"],
              ].map(([key, label]) => (
                <th
                  key={key}
                  onClick={() => handleSort(key)}
                  className="sortable"
                >
                  {label}{arrow(key)}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {paged.map(s => (
              <tr
                key={s.student_id}
                className={s.subject_risk === 1 ? "row-risk" : ""}
              >
                <td className="mono">{s.student_id}</td>

                <td>{s.name}</td>

                <td>
                  <span className="branch-badge">{s.branch}</span>
                </td>

                <td>{s.year}</td>

                <td>
                  <div className="marks-bar-wrap">
                    <div
                      className="marks-bar"
                      style={{
                        width: `${Math.min((s.selected_marks / data.subject_max_marks) * 100, 100)}%`,
                        background:
                          s.selected_marks < data.marks_threshold ? "#ff4757" : "#2ed573",
                      }}
                    />
                    <span>{s.selected_marks}</span>
                  </div>
                </td>

                <td>
                  <span
                    className={
                      s.attendance_pct < 0.75 ? "pct-low" : "pct-ok"
                    }
                  >
                    {(s.attendance_pct * 100).toFixed(1)}%
                  </span>
                </td>

                <td>
                  {s.subject_risk === 1 ? (
                    <span className="badge-risk">At-Risk</span>
                  ) : (
                    <span className="badge-safe">Safe</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            ‹ Prev
          </button>

          <span>
            Page {page} / {totalPages}
          </span>

          <button
            disabled={page === totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            Next ›
          </button>
        </div>
      )}
    </section>
  );
}
