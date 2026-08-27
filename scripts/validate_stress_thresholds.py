#!/usr/bin/env python3
import argparse, json, sys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('json_file')
    ap.add_argument('--p95-ms',type=float,default=5000)
    ap.add_argument('--p99-ms',type=float,default=10000)
    ap.add_argument('--min-throughput',type=float,default=2)
    ap.add_argument('--max-lock-waiters',type=int,default=250)
    ap.add_argument('--max-errors',type=int,default=0)
    ap.add_argument('--max-deadlocks',type=int,default=0)
    ap.add_argument('--required-concurrency', type=int, action='append', default=[])
    ap.add_argument('--required-workloads', type=str, default='')
    args=ap.parse_args()
    data=json.load(open(args.json_file,encoding='utf-8')); samples=data.get('samples',[])
    failures=[]
    required_n=set(args.required_concurrency)
    required_ops={x.strip() for x in args.required_workloads.split(',') if x.strip()}
    seen_n={x.get('concurrency') for x in samples}
    seen_ops={x.get('operation') for x in samples}
    missing_n=required_n-seen_n
    missing_ops=required_ops-seen_ops
    if missing_n: failures.append(f'missing required concurrency levels: {sorted(missing_n)}')
    if missing_ops: failures.append(f'missing required workloads: {sorted(missing_ops)}')
    for x in samples:
        if x['errors']>args.max_errors: failures.append(f"{x['operation']}@{x['concurrency']}: errors {x['errors']} > {args.max_errors}")
        if x['deadlocks_delta']>args.max_deadlocks: failures.append(f"{x['operation']}@{x['concurrency']}: deadlocks {x['deadlocks_delta']} > {args.max_deadlocks}")
        if x['p95_ms']>args.p95_ms: failures.append(f"{x['operation']}@{x['concurrency']}: p95 {x['p95_ms']:.2f}ms > {args.p95_ms}ms")
        if x['p99_ms']>args.p99_ms: failures.append(f"{x['operation']}@{x['concurrency']}: p99 {x['p99_ms']:.2f}ms > {args.p99_ms}ms")
        if x['throughput_ops_s']<args.min_throughput: failures.append(f"{x['operation']}@{x['concurrency']}: throughput {x['throughput_ops_s']:.2f} < {args.min_throughput}")
        if x['lock_wait_max']>args.max_lock_waiters: failures.append(f"{x['operation']}@{x['concurrency']}: lock waiters {x['lock_wait_max']} > {args.max_lock_waiters}")
    print(f"Thresholds checked: {len(samples)} samples")
    if failures:
        print("PERFORMANCE GATE: FAIL")
        print("\n".join(f"- {x}" for x in failures))
        return 1
    print("PERFORMANCE GATE: PASS")
    return 0
if __name__=='__main__': sys.exit(main())
