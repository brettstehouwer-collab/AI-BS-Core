FROM gcr.io/dataflow-templates-base/python311-template-launcher-base

ARG WORKDIR=/dataflow/template
RUN mkdir -p ${WORKDIR}
WORKDIR ${WORKDIR}

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -U "apache-beam[gcp]>=2.54.0" && \
    pip install --no-cache-dir -r requirements.txt

# Copy pipeline code
COPY aibs_genomic_telemetry_pipeline.py .

ENV FLEX_TEMPLATE_PYTHON_PY_FILE="${WORKDIR}/aibs_genomic_telemetry_pipeline.py"

ENTRYPOINT ["/opt/google/dataflow/python_template_launcher"]
