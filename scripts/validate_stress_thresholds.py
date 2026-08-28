#!/usr/bin/env python3
import argparse, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json_file')
    ap.add_argument('--p95-ms', type=float, default=5000)
    ap.add_argument('--p99-ms', type=float, default=10000)
    ap.add_argument('--min-throughput', type=float, default=2)
    ap.add_argument('--max-lock-waiters', type=int, default=250)
    ap.add_argument('--max-errors', type=int, default=0)
    ap.add_argument('--max-deadlocks', type=int, default=0)
    ap.add_argument('--required-concurrency', type=int, default=None)
    ap.add_argument('--required-workloads', default='')
    args = ap.parse_args()

    with open(args.json_file, encoding='utf-8') as fh:
        data = json.load(fh)
    samples = data.get('samples', [])
    failures = []

    required_workloads = {x.strip() for x in args.required_workloads.split(',') if x.strip()}
    actual_workloads = {x.get('operation') for x in samples}
    if args.required_concurrency is not None:
        actual_concurrency = {int(x.get('concurrency', -1)) for x in samples}
        if args.required_concurrency not in actual_concurrency:
            failures.append(f"required concurrency {args.required_concurrency} is missing")
    missing_workloads = required_workloads - actual_workloads
    if missing_workloads:
        failures.append(f"required workloads missing: {', '.join(sorted(missing_workloads))}")

    for x in samples:
        label = f"{x['operation']}@{x['concurrency']}"
        if x['errors'] > args.max_errors:
            failures.append(f"{label}: errors {x['errors']} > {args.max_errors}")
        if x['deadlocks_delta'] > args.max_deadlocks:
            failures.append(f"{label}: deadlocks {x['deadlocks_delta']} > {args.max_deadlocks}")
        if x['p95_ms'] > args.p95_ms:
            failures.append(f"{label}: p95 {x['p95_ms']:.2f}ms > {args.p95_ms}ms")
        if x['p99_ms'] > args.p99_ms:
            failures.append(f"{label}: p99 {x['p99_ms']:.2f}ms > {args.p99_ms}ms")
        if x['throughput_ops_s'] < args.min_throughput:
            failures.append(f"{label}: throughput {x['throughput_ops_s']:.2f} < {args.min_throughput}")
        if x['lock_wait_max'] > args.max_lock_waiters:
            failures.append(f"{label}: lock waiters {x['lock_wait_max']} > {args.max_lock_waiters}")

    print(f"Thresholds checked: {len(samples)} samples")
    if failures:
        print("PERFORMANCE GATE: FAIL")
        print("\n".join(f"- {x}" for x in failures))
        return 1
    print("PERFORMANCE GATE: PASS")
    return 0


if __name__ == '__main__':
    sys.exit(main())
