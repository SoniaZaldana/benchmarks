import re
import sys
import argparse
import csv
import os

BENCHMARKS = [
    "avrora", "eclipse", "fop", "jython", "kafka", "luindex", "lusearch", "pmd", "spring", "sunflow"
]

def main():
    print('================= Garbage Log Parser ===============')
    args = parse_arguments()
    process_metrics(gc_metrics, args.parent_dir, args.compact, args.runs)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Removes warmup logs from GC logs')
    parser.add_argument('-parent_dir', required=True, help='Parent directory for logs (e.g., parallel or g1)')
    parser.add_argument('-compact', action='store_true', help='Use compact memory option, affecting output file paths')
    parser.add_argument('-runs', type=int, required=True, help='Number of runs to consider for log file naming')
    return parser.parse_args()

def extract_performance_metrics(parent_dir, compact, runs):
    for bench in BENCHMARKS:
        print(f"Evaluating benchmark {bench} for runtime metrics")
        runtime_metrics = []

        for run in range(1, runs + 1):
            time_file_path = get_log_file_path(parent_dir, bench, run, 'time', compact)
            if os.path.exists(time_file_path):
                runtime = extract_runtime_from_file(time_file_path)
                if runtime is not None:
                    runtime_metrics.append([run, runtime])
                    print(f"{bench} runtime: {runtime} ms")
            else:
                print(f"Warning: {time_file_path} not found.")

        if runtime_metrics:
            output_file_path = get_output_file_path(parent_dir, bench, 'runtime', compact, run)
            write_to_csv(output_file_path, [['Run', 'Runtime (ms)']] + runtime_metrics)

def extract_runtime_from_file(file_path):
    pattern = re.compile(r'===== DaCapo 23.11-chopin (.+?) PASSED in (\d+) msec =====')
    with open(file_path, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                return match.group(2)
    return None

def process_metrics(metric_func, parent_dir, compact, runs):
    for bench in BENCHMARKS:
        print(f"Evaluating benchmark {bench}")
        for run in range(1, runs + 1):
            print(f"------ Run {run}")
            time_file_path = get_log_file_path(parent_dir, bench, run, 'time', compact)
            last_warmup_time = extract_measurable_times(time_file_path)

            if last_warmup_time is None:
                print(f"Error: Could not determine warmup logs for {bench} run {run}")
                continue

            gc_file_path = get_log_file_path(parent_dir, bench, run, 'log', compact)
            filtered_gc_logs = filter_gc_logs(gc_file_path, last_warmup_time)
            metric_func(filtered_gc_logs, bench, run, parent_dir, compact)

def get_log_file_path(parent_dir, bench, run, file_type, compact):
    suffix = "_compact" if compact else ""
    return os.path.join(parent_dir, f'logs{suffix}', f"{bench}_run{run}.{file_type}")

def get_output_file_path(parent_dir, bench, metric_type, compact, run=None):
    suffix = "_compact" if compact else ""
    filename = f"{bench}_run{run}.{metric_type}" if run else f"{bench}.{metric_type}"
    return os.path.join(parent_dir, f'logs{suffix}', filename)

# Find the time the last warmup iteration finished
def extract_measurable_times(file):
    pattern = re.compile(r'Warmup: Benchmark ended (\d+\.\d+)s')
    with open(file, 'r') as warmup_file:
        for line in warmup_file:
            match = pattern.search(line)
            if match:
                return float(match.group(1))
    return None

# Discard any gc logs from warmup iterations
def filter_gc_logs(gc_file_path, start_time):
    filtered_logs = []
    pattern = re.compile(r'\[(\d+\.\d+)s\]')
    with open(gc_file_path, 'r') as gc_file:
        for line in gc_file:
            match = pattern.search(line)
            if match and float(match.group(1)) >= start_time:
                filtered_logs.append(line.strip())
    return filtered_logs

def gc_metrics(lines, bench, run, parent_dir, compact):
    gc_output_file = get_output_file_path(parent_dir, bench, 'gc', compact, run)
    with open(gc_output_file, 'w') as file:
        for string in lines:
            file.write(string + '\n')  # Write each string followed by a newline



if __name__ == "__main__":
    main()
