"""Separate worker process; survives its owned API restart without a daemon fleet."""
import argparse
import time

from .project_maintenance import run_dispatched_job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job-id', required=True)
    args = parser.parse_args()
    # Let the authenticated request return its durable identifier before any
    # operation that can close its existing HTTP connection.
    time.sleep(.75)
    result = run_dispatched_job(args.job_id)
    return 0 if result['state'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
