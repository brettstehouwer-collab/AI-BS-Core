#!/usr/bin/env python3
"""
AI-BS Sovereign Intelligence Ecosystem - Cloud Dataflow Apache Beam Pipeline
High-Throughput Genomic Variant & Inference Telemetry Processing Engine
Compatible with Google Cloud Dataflow Flex Templates & Local DirectRunner
"""

import argparse
import json
import logging
import re
from typing import Dict, Any, Tuple
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions, StandardOptions

logger = logging.getLogger("AIBSGenomicPipeline")

# Tag for dead-letter side outputs
TAG_DEAD_LETTER = "dead_letter"
TAG_VALID = "valid_records"


class ParseAndValidateVariantFn(beam.DoFn):
    """
    Parses incoming raw JSON lines into structured genomic variant events.
    Applies strict validation: chromosome format, positive coordinate position,
    nucleotide base validity (A, C, G, T, N), and calculates variant complexity.
    Routes invalid records to the dead-letter tag.
    """
    CHROM_PATTERN = re.compile(r"^(chr)?([1-9]|1[0-9]|2[0-2]|X|Y|M|MT)$", re.IGNORECASE)
    BASES_PATTERN = re.compile(r"^[ACGTN]+$", re.IGNORECASE)

    def process(self, line: str):
        if not line or not line.strip():
            return

        try:
            record = json.loads(line)
        except Exception as e:
            yield beam.pvalue.TaggedOutput(TAG_DEAD_LETTER, {"raw": line, "error": f"JSON parse error: {str(e)}"})
            return

        # Check required fields: chrom, pos, ref, alt
        chrom = str(record.get("chrom", "")).strip()
        pos = record.get("pos")
        ref = str(record.get("ref", "")).strip().upper()
        alt = str(record.get("alt", "")).strip().upper()

        if not self.CHROM_PATTERN.match(chrom):
            yield beam.pvalue.TaggedOutput(TAG_DEAD_LETTER, {"record": record, "error": f"Invalid chromosome: {chrom}"})
            return

        try:
            pos_int = int(pos)
            if pos_int <= 0:
                raise ValueError("Position must be positive")
        except Exception:
            yield beam.pvalue.TaggedOutput(TAG_DEAD_LETTER, {"record": record, "error": f"Invalid position: {pos}"})
            return

        if not self.BASES_PATTERN.match(ref) or not self.BASES_PATTERN.match(alt):
            yield beam.pvalue.TaggedOutput(TAG_DEAD_LETTER, {"record": record, "error": f"Invalid alleles: ref={ref}, alt={alt}"})
            return

        # Enrich variant
        is_snp = len(ref) == 1 and len(alt) == 1
        var_type = "SNP" if is_snp else ("INS" if len(alt) > len(ref) else "DEL")
        
        enriched = {
            "chrom": chrom if chrom.startswith("chr") else f"chr{chrom}",
            "pos": pos_int,
            "ref": ref,
            "alt": alt,
            "rsid": record.get("rsid", "unknown"),
            "variant_type": var_type,
            "gene_symbol": record.get("gene_symbol", "intergenic"),
            "impact_score": float(record.get("impact_score", 0.0)),
            "source_dataset": record.get("source_dataset", "aibs_sovereign_intake"),
            "processed_timestamp": record.get("timestamp", "")
        }
        yield beam.pvalue.TaggedOutput(TAG_VALID, enriched)


class AggregateGeneImpactStats(beam.PTransform):
    """
    PTransform that groups valid variants by gene symbol and computes
    variant counts and maximum impact scores.
    """
    def expand(self, pcoll):
        return (
            pcoll
            | "MapToGeneKey" >> beam.Map(lambda v: (v["gene_symbol"], v["impact_score"]))
            | "CombineByGene" >> beam.CombinePerKey(
                lambda scores: {
                    "count": len(list(scores)),
                    "max_impact": max(scores) if scores else 0.0,
                    "avg_impact": sum(scores) / max(len(scores), 1)
                }
            )
            | "FormatGeneSummary" >> beam.Map(
                lambda item: {
                    "gene_symbol": item[0],
                    "total_variants": item[1]["count"],
                    "max_impact_score": round(item[1]["max_impact"], 4),
                    "avg_impact_score": round(item[1]["avg_impact"], 4)
                }
            )
        )


def run_pipeline(argv=None):
    """Main pipeline execution function."""
    parser = argparse.ArgumentParser(description="AI-BS Genomic & Telemetry Dataflow Pipeline")
    parser.add_argument("--input_pattern", required=True, help="Input GCS or local file path pattern (JSON lines)")
    parser.add_argument("--output_table", default="", help="BigQuery output table (PROJECT:DATASET.TABLE)")
    parser.add_argument("--output_gcs_prefix", default="", help="GCS output prefix for summary reports")
    parser.add_argument("--dead_letter_path", default="", help="GCS or local path for dead letter output")

    known_args, pipeline_args = parser.parse_known_args(argv)
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True

    with beam.Pipeline(options=pipeline_options) as p:
        # 1. Ingest raw lines
        raw_lines = p | "ReadRawInput" >> beam.io.ReadFromText(known_args.input_pattern)

        # 2. Parse and validate with dead-letter tagging
        results = raw_lines | "ParseAndValidate" >> beam.ParDo(ParseAndValidateVariantFn()).with_outputs(
            TAG_DEAD_LETTER,
            TAG_VALID
        )

        valid_records = results[TAG_VALID]
        dead_letter_records = results[TAG_DEAD_LETTER]

        # 3. Handle dead letter output if path provided
        if known_args.dead_letter_path:
            (
                dead_letter_records
                | "FormatDeadLetter" >> beam.Map(json.dumps)
                | "WriteDeadLetter" >> beam.io.WriteToText(known_args.dead_letter_path, file_name_suffix=".jsonl")
            )

        # 4. Write valid variants to BigQuery if table provided
        if known_args.output_table:
            (
                valid_records
                | "WriteToBigQuery" >> beam.io.WriteToBigQuery(
                    table=known_args.output_table,
                    schema={
                        "fields": [
                            {"name": "chrom", "type": "STRING", "mode": "REQUIRED"},
                            {"name": "pos", "type": "INTEGER", "mode": "REQUIRED"},
                            {"name": "ref", "type": "STRING", "mode": "REQUIRED"},
                            {"name": "alt", "type": "STRING", "mode": "REQUIRED"},
                            {"name": "rsid", "type": "STRING", "mode": "NULLABLE"},
                            {"name": "variant_type", "type": "STRING", "mode": "REQUIRED"},
                            {"name": "gene_symbol", "type": "STRING", "mode": "NULLABLE"},
                            {"name": "impact_score", "type": "FLOAT", "mode": "NULLABLE"},
                            {"name": "source_dataset", "type": "STRING", "mode": "NULLABLE"},
                            {"name": "processed_timestamp", "type": "STRING", "mode": "NULLABLE"}
                        ]
                    },
                    write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                    create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
                )
            )

        # 5. Summarize gene impact stats and write to GCS if prefix provided
        if known_args.output_gcs_prefix:
            gene_summaries = valid_records | "AggregateGeneStats" >> AggregateGeneImpactStats()
            (
                gene_summaries
                | "FormatSummary" >> beam.Map(json.dumps)
                | "WriteSummary" >> beam.io.WriteToText(known_args.output_gcs_prefix, file_name_suffix=".jsonl")
            )


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run_pipeline()
