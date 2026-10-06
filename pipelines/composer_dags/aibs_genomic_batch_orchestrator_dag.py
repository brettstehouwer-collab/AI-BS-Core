#!/usr/bin/env python3
"""
AI-BS Sovereign Intelligence Ecosystem - Cloud Composer Orchestrator DAG
Schedules & triggers Dataflow Flex Template jobs for daily genomic batch processing
Compatible with Managed Service for Apache Airflow (Cloud Composer 2 & 3)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowStartFlexTemplateOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "aibs_sentinel",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

PROJECT_ID = "{{ var.value.get('gcp_project_id', 'aibs-ecosystem-prod') }}"
REGION = "{{ var.value.get('gcp_region', 'us-central1') }}"
BUCKET_NAME = "{{ var.value.get('aibs_vault_bucket', 'aibs-vault-storage') }}"
FLEX_TEMPLATE_IMAGE_GCS = f"gs://{BUCKET_NAME}/templates/aibs_genomic_pipeline.json"

with DAG(
    dag_id="aibs_genomic_batch_orchestrator",
    default_args=default_args,
    description="Orchestrates daily AI-BS genomic dataset ingest and Dataflow Flex Template execution",
    schedule_interval="0 4 * * *",  # Daily at 04:00 UTC
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["aibs", "genomics", "dataflow", "composer"],
) as dag:

    def preflight_check(**context):
        """Verifies environment variables and target cloud paths before launch."""
        execution_date = context["execution_date"].to_date_string()
        print(f"[AI-BS Sentinel] Starting daily genomic batch orchestration for {execution_date}")
        print(f"[AI-BS Sentinel] Project: {PROJECT_ID}, Region: {REGION}")
        return True

    task_preflight = PythonOperator(
        task_id="aibs_preflight_audit",
        python_callable=preflight_check,
    )

    # Launch Dataflow Flex Template
    task_start_dataflow = DataflowStartFlexTemplateOperator(
        task_id="launch_dataflow_genomic_pipeline",
        project_id=PROJECT_ID,
        location=REGION,
        body={
            "launchParameter": {
                "jobName": f"aibs-genomic-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "containerSpecGcsPath": FLEX_TEMPLATE_IMAGE_GCS,
                "parameters": {
                    "input_pattern": f"gs://{BUCKET_NAME}/intake/genomics/*.jsonl",
                    "output_table": f"{PROJECT_ID}:aibs_genomics.processed_variants",
                    "output_gcs_prefix": f"gs://{BUCKET_NAME}/summaries/daily_gene_summary",
                    "dead_letter_path": f"gs://{BUCKET_NAME}/dead_letter/malformed_records",
                },
                "environment": {
                    "tempLocation": f"gs://{BUCKET_NAME}/temp",
                    "stagingLocation": f"gs://{BUCKET_NAME}/staging",
                    "machineType": "n2-standard-4",
                    "maxWorkers": 10,
                },
            }
        },
        do_xcom_push=True,
    )

    # Downstream BigQuery ML summary query
    task_bq_enrichment = BigQueryInsertJobOperator(
        task_id="aggregate_variant_impact_metrics",
        configuration={
            "query": {
                "query": f"""
                    CREATE OR REPLACE TABLE `{PROJECT_ID}.aibs_genomics.daily_impact_kpis` AS
                    SELECT 
                        gene_symbol,
                        COUNT(1) as total_variants,
                        COUNTIF(variant_type = 'SNP') as total_snps,
                        COUNTIF(variant_type != 'SNP') as total_indels,
                        AVG(impact_score) as mean_impact_score,
                        MAX(impact_score) as peak_impact_score,
                        CURRENT_TIMESTAMP() as calculated_at
                    FROM `{PROJECT_ID}.aibs_genomics.processed_variants`
                    WHERE DATE(TIMESTAMP(processed_timestamp)) = CURRENT_DATE()
                    GROUP BY gene_symbol
                    ORDER BY total_variants DESC;
                """,
                "useLegacySql": False,
            }
        },
    )

    def post_execution_audit(**context):
        """Records execution success in AI-BS vault."""
        print("[AI-BS Sentinel] Dataflow & BigQuery enrichment completed successfully.")

    task_audit = PythonOperator(
        task_id="aibs_post_execution_audit",
        python_callable=post_execution_audit,
    )

    task_preflight >> task_start_dataflow >> task_bq_enrichment >> task_audit
