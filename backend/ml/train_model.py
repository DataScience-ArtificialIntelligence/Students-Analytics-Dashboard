"""
ML Model: Logistic Regression (at-risk classification)
Reads processed data from HDFS, trains the model, saves results.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudentML")

HDFS_BASE       = "hdfs://localhost:9000/students_data"
PROCESSED_PATH  = f"{HDFS_BASE}/processed_data/final_dataset.csv"
MODEL_OUT_PATH  = f"{HDFS_BASE}/processed_data/predictions.csv"
LR_MODEL_PATH   = f"{HDFS_BASE}/processed_data/lr_model"
FEATURES        = ["avg_marks", "attendance_pct"]


def create_spark_session():
    return (
        SparkSession.builder
        .appName("StudentML")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


# ─────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────
def load_data(spark):
    df = spark.read.csv(PROCESSED_PATH, header=True, inferSchema=True)
    logger.info(f"Loaded {df.count()} rows for ML")
    df.printSchema()
    return df


# ─────────────────────────────────────────────
# 2. FEATURE ASSEMBLY
# ─────────────────────────────────────────────
def assemble_features(df):
    assembler = VectorAssembler(inputCols=FEATURES, outputCol="raw_features")
    scaler    = StandardScaler(inputCol="raw_features", outputCol="features",
                               withMean=True, withStd=True)
    pipeline  = Pipeline(stages=[assembler, scaler])
    model     = pipeline.fit(df)
    df_feat   = model.transform(df)
    return df_feat, model


# ─────────────────────────────────────────────
# 3. LOGISTIC REGRESSION
# ─────────────────────────────────────────────
def train_logistic_regression(df_feat):
    train_df, test_df = df_feat.randomSplit([0.8, 0.2], seed=42)
    logger.info(f"Train: {train_df.count()} | Test: {test_df.count()}")

    lr = LogisticRegression(
        featuresCol="features",
        labelCol="label",
        maxIter=100,
        regParam=0.01,
        elasticNetParam=0.0
    )
    lr_model = lr.fit(train_df)

    # Evaluate on test set
    predictions = lr_model.transform(test_df)

    auc_eval = BinaryClassificationEvaluator(
        labelCol="label",
        rawPredictionCol="rawPrediction",
        metricName="areaUnderROC"
    )
    auc = auc_eval.evaluate(predictions)

    acc_eval = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="accuracy"
    )
    accuracy = acc_eval.evaluate(predictions)

    logger.info(f"Logistic Regression AUC:      {auc:.4f}")
    logger.info(f"Logistic Regression Accuracy: {accuracy:.4f}")

    # Coefficients
    logger.info(f"Coefficients: {lr_model.coefficients}")
    logger.info(f"Intercept:    {lr_model.intercept}")

    return lr_model, auc, accuracy


# ─────────────────────────────────────────────
# 4. FINAL PREDICTIONS & SAVE
# ─────────────────────────────────────────────
def save_predictions(df_feat, lr_model):
    df_pred = lr_model.transform(df_feat)

    # Extract probability of being at-risk (class 1)
    get_prob = F.udf(lambda v: float(v[1]))

    result = df_pred.withColumn("risk_score", F.round(get_prob(F.col("probability")), 4)) \
                    .select(
                        "student_id", "name", "branch", "year",
                        "attendance_pct", "avg_marks", "label",
                        "prediction", "risk_score"
                    )

    result.coalesce(1) \
          .write \
          .mode("overwrite") \
          .option("header", "true") \
          .csv(MODEL_OUT_PATH)

    logger.info(f"Saved predictions to: {MODEL_OUT_PATH}")
    result.show(10, truncate=False)
    return result


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        df = load_data(spark)

        logger.info("=== Feature Engineering ===")
        df_feat, feat_pipeline = assemble_features(df)

        logger.info("=== Logistic Regression ===")
        lr_model, auc, accuracy = train_logistic_regression(df_feat)

        logger.info("=== Saving predictions ===")
        save_predictions(df_feat, lr_model)

        logger.info("✅ ML pipeline complete.")
        logger.info(f"   AUC: {auc:.4f} | Accuracy: {accuracy:.4f}")

    except Exception as e:
        logger.error(f"ML pipeline failed: {e}")
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
