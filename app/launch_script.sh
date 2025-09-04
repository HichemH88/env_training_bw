#!/bin/bash
# run_python_pipeline.sh - Manages Python job dependencies with robust logging

# Configuration
LOG_DIR="/var/log/python_jobs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/pipeline_${TIMESTAMP}.log"
JOB_A="/app/pyspark_stg.py"
JOB_B="/app/data_clean_pyspark.py"
PYTHON_EXEC="/usr/local/bin/python"  # or "python3" if in PATH

# Create log directory if missing
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Run Python job with error handling
run_python_job() {
    local job_name=$1
    local script_path=$2
    
    log "Starting $job_name..."
    
    $PYTHON_EXEC "$script_path" >> "$LOG_FILE" 2>&1
    
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        log "ERROR: $job_name failed with exit code $exit_code"
        return 1
    else
        log "$job_name completed successfully"
        return 0
    fi
}

# Main execution flow
log "=== Starting Python Job Pipeline ==="

# Run Job A
if run_python_job "Data Loader" "$JOB_A"; then
    # Only run Job B if Job A succeeds
    if run_python_job "Data check" "$JOB_B"; then
        log "=== Pipeline Completed Successfully ==="
        exit 0
    fi
fi

log "=== Pipeline Failed ==="
exit 1