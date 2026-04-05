# EduPulse

EduPulse is a student performance analytics project built with React, Flask, Spark, and a lightweight ML pipeline. It shows subject-wise performance, attendance, and at-risk students across `CSE`, `DSAI`, and `ECE`.

The current version focuses on:

- subject-wise total marks
- attendance analysis
- at-risk identification
- branch-level summaries
- branch-wise risk comparison charts

## Features

- Subject dropdown for `BDA`, `DL`, `DSP`, and `DBMS`
- Per-student subject totals on a normalized `100`-point scale
- At-risk detection based on marks and attendance
- Overview cards for total students, at-risk count, marks, and attendance
- Branch-wise performance summary
- Search, branch filter, sorting, and pagination for student records
- Search in the at-risk view by student name or ID
- Risk-type filters for `Marks < 33%` and `Attendance < 75%`
- Subject-aware analytics charts built with Chart.js

## File Storage (HDFS)

All datasets in this project are stored in the Hadoop Distributed File System (HDFS), which is configured and run locally on the system.

Instead of relying on local file storage, the project uses HDFS to simulate a distributed data environment, enabling scalable data processing using Apache Spark.

### HDFS Directory Structure

```text
/students_data/
├── students/
│   ├── cse_students.csv
│   ├── dsai_students.csv
│   └── ece_students.csv
│
├── attendance/
│   ├── cse_attendance.csv
│   ├── dsai_attendance.csv
│   └── ece_attendance.csv
│
├── marks/
│   ├── cse_BDA_marks.csv
│   ├── cse_DL_marks.csv
│   ├── cse_DSP_marks.csv
│   ├── cse_DBMS_marks.csv
│   ├── dsai_BDA_marks.csv
│   ├── ...
│   └── ece_DBMS_marks.csv
│
└── processed_data/
    └── final_dataset.csv

## Marks Normalization

Each subject is normalized to `100` marks using this formula:

total_subject_marks =
  quiz1_marks
  + quiz2_marks
  + assignment_marks
  + (mid_sem_marks × 0.4)
  + (end_sem_marks × 0.4)
```

This means:

- `quiz1` remains as-is
- `quiz2` remains as-is
- `assignment` remains as-is
- `mid sem` is scaled from `50` to `20`
- `end sem` is scaled from `100` to `40`

So the final subject total is out of `100`.

## At-Risk Criteria

A student is marked as at-risk if either condition is true:

- subject total marks are below `33`
- attendance is below `75%`

In code terms:

```text
selected_marks < 33 OR attendance_pct < 0.75
```

Because the dashboard is subject-aware, the same student may be safe in one subject and at-risk in another.

## Tech Stack

- Frontend: React + Vite + Chart.js
- Backend API: Flask + Pandas
- Data processing: PySpark
- ML: Logistic Regression with Spark MLlib

## Project Structure

```text
BDA-Project-4th-Sem/
├── backend/
│   ├── flask/
│   │   └── app.py
│   ├── ml/
│   │   └── train_model.py
│   ├── raw_data/
│   │   ├── *_students.csv
│   │   ├── *_attendance.csv
│   │   └── *_marks.csv
│   └── spark/
│       └── pipeline.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── constants/
│   │   └── hooks/
│   ├── .env
│   └── package.json
└── README.md
```

## Backend Overview

### 1. Spark Processing

`backend/spark/pipeline.py` reads raw student, attendance, and marks CSV files, computes:

- attendance percentage
- normalized subject totals
- average marks across subjects
- binary at-risk label for the ML dataset

The processed dataset is written to:

```text
hdfs://localhost:9000/students_data/processed_data/final_dataset.csv
```

### 2. ML Pipeline

`backend/ml/train_model.py` trains a Logistic Regression model using:

- `avg_marks`
- `attendance_pct`

It outputs prediction data including:

- `prediction`
- `risk_score`

### 3. Flask API

`backend/flask/app.py` serves the dashboard data. It combines the processed predictions CSV with raw subject-mark files so the frontend can query subject-specific totals.

Available endpoints:

- `GET /health`
- `GET /data?subject=BDA`
- `GET /at-risk?subject=BDA`
- `GET /summary?subject=BDA`
- `GET /branch/<branch>`

The default subject is `BDA` if no subject is provided.

## Frontend Overview

The frontend is a React dashboard with these tabs:

- `Overview`
- `All Students`
- `At-Risk`
- `Analytics`

Main UI behavior:

- a global subject dropdown controls subject-specific marks
- all views update when the subject changes
- marks bars and charts use the normalized `100`-point scale
- the Analytics tab shows `Safe vs At-Risk by Branch`
- the Analytics tab can be filtered by `Marks < 33%` or `Attendance < 75%`
- the At-Risk tab can be filtered by risk reason and searched by student name or ID

## Environment Configuration

### Backend

`backend/.env`

```env
PROCESSED_CSV=data/predictions.csv
PORT=5000
HDFS_NAMENODE='http://localhost:9000'
SPARK_MASTER='local[*]'
```

## Running the Project

### 1. Start the Flask backend

From the project root:

```bash
cd backend/flask
python3 app.py
```

The API runs by default on `http://localhost:5000`.

### 2. Start the frontend

From the project root:

```bash
cd frontend
npm install
npm run dev
```

The Vite app will run on its local dev port and call the Flask API using `VITE_API_URL`.

## Team

- Aalekh Raghuvanshi
- Bhavya Khare
- Devam Sharma
- Hemant Kumar
- Saksham Kushwah



