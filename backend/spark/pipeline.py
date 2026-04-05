"""
Spark Processing Pipeline
Raw CSV from HDFS → Feature Engineering → Processed Data back to HDFS
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudentPipeline")

HDFS_BASE     = "hdfs://localhost:9000/students_data"
BRANCHES      = ["cse", "dsai", "ece"]
SUBJECTS      = ["BDA", "DL", "DSP", "DBMS"]
OUTPUT_PATH   = f"{HDFS_BASE}/processed_data/final_dataset.csv"
SUBJECT_RISK_THRESHOLD = 33.0


def create_spark_session():
    return (
        SparkSession.builder
        .appName("StudentPerformanceAnalytics")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


# ─────────────────────────────────────────────
# 1. LOAD STUDENTS
# ─────────────────────────────────────────────
def load_students(spark):
    dfs = []
    for branch in BRANCHES:
        path = f"{HDFS_BASE}/students/{branch}_students.csv"
        df = spark.read.csv(path, header=True, inferSchema=True)
        dfs.append(df)
        logger.info(f"Loaded students: {branch} ({df.count()} rows)")
    return dfs[0].unionByName(dfs[1]).unionByName(dfs[2])


# ─────────────────────────────────────────────
# 2. LOAD & PROCESS ATTENDANCE
# ─────────────────────────────────────────────
def load_attendance(spark):
    """
    Wide format → long format → attendance_pct per student.
    attendance.csv columns: student_id, date1, date2, ..., dateN  (1=present, 0=absent)
    """
    dfs = []
    for branch in BRANCHES:
        path = f"{HDFS_BASE}/attendance/{branch}_attendance.csv"
        df = spark.read.csv(path, header=True, inferSchema=True)

        date_cols = [c for c in df.columns if c != "student_id"]
        total_days = len(date_cols)

        # Sum all date columns to get days present
        present_expr = sum(F.col(c).cast(DoubleType()) for c in date_cols)
        df = df.withColumn("days_present", present_expr) \
               .withColumn("total_days", F.lit(total_days)) \
               .withColumn("attendance_pct",
                           F.round(F.col("days_present") / F.lit(total_days), 4)) \
               .select("student_id", "days_present", "total_days", "attendance_pct")

        dfs.append(df)
        logger.info(f"Processed attendance: {branch} ({df.count()} rows, {total_days} days)")

    return dfs[0].unionByName(dfs[1]).unionByName(dfs[2])


# ─────────────────────────────────────────────
# 3. LOAD & PROCESS MARKS
# ─────────────────────────────────────────────
def load_marks(spark):
    """
    Load marks for all branch × subject combinations.
    marks.csv columns: student_id, quiz1_marks, quiz2_marks,
                       assignment_marks, mid_sem_marks, end_sem_marks
    Compute total_marks per subject, then average across subjects.
    """
    all_marks = []

    for branch in BRANCHES:
        subject_dfs = []
        for subject in SUBJECTS:
            path = f"{HDFS_BASE}/marks/{branch}_{subject}_marks.csv"
            df = spark.read.csv(path, header=True, inferSchema=True)

            total_expr = (
                F.col("quiz1_marks").cast(DoubleType())
                + F.col("quiz2_marks").cast(DoubleType())
                + F.col("assignment_marks").cast(DoubleType())
                + (F.col("mid_sem_marks").cast(DoubleType()) * F.lit(0.4))
                + (F.col("end_sem_marks").cast(DoubleType()) * F.lit(0.4))
            )

            df = df.withColumn(f"total_{subject}",
                               F.round(total_expr, 2)) \
                   .select("student_id", f"total_{subject}")

            subject_dfs.append(df)
            logger.info(f"Loaded marks: {branch}_{subject}")

        # Join all subjects for this branch
        branch_marks = subject_dfs[0]
        for sdf in subject_dfs[1:]:
            branch_marks = branch_marks.join(sdf, on="student_id", how="inner")

        # Average across subjects
        subject_total_cols = [f"total_{s}" for s in SUBJECTS]
        avg_expr = sum(F.col(c) for c in subject_total_cols) / len(subject_total_cols)
        branch_marks = branch_marks.withColumn("avg_marks", F.round(avg_expr, 2))

        all_marks.append(branch_marks)

    combined = all_marks[0]
    for mdf in all_marks[1:]:
        combined = combined.unionByName(mdf)

    return combined


# ─────────────────────────────────────────────
# 4. JOIN & LABEL
# ─────────────────────────────────────────────
def build_final_dataset(students, attendance, marks):
    """
    Join all datasets and create at-risk label.
    Label = 1 if avg_marks < 33 OR attendance_pct < 0.75
    """
    df = students \
        .join(attendance, on="student_id", how="inner") \
        .join(marks.select("student_id", "avg_marks"), on="student_id", how="inner")

    df = df.withColumn(
        "label",
        F.when(
            (F.col("avg_marks") < SUBJECT_RISK_THRESHOLD) | (F.col("attendance_pct") < 0.75),
            F.lit(1)
        ).otherwise(F.lit(0))
    )

    final = df.select(
        "student_id", "name", "branch", "year",
        "attendance_pct", "avg_marks", "label"
    )

    logger.info(f"Final dataset: {final.count()} rows")
    at_risk = final.filter(F.col("label") == 1).count()
    logger.info(f"At-risk students: {at_risk}")

    return final


# ─────────────────────────────────────────────
# 5. SAVE TO HDFS
# ─────────────────────────────────────────────
def save_to_hdfs(df):
    df.coalesce(1) \
      .write \
      .mode("overwrite") \
      .option("header", "true") \
      .csv(OUTPUT_PATH)
    logger.info(f"Saved processed data to: {OUTPUT_PATH}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        logger.info("=== Loading students ===")
        students = load_students(spark)

        logger.info("=== Processing attendance ===")
        attendance = load_attendance(spark)

        logger.info("=== Processing marks ===")
        marks = load_marks(spark)

        logger.info("=== Building final dataset ===")
        final_df = build_final_dataset(students, attendance, marks)
        final_df.show(10, truncate=False)

        logger.info("=== Saving to HDFS ===")
        save_to_hdfs(final_df)

        logger.info("✅ Pipeline complete.")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
