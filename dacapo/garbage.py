import re
import sys
import argparse
import csv
import os

BENCHMARKS = [
    "avrora", "batik", "cassandra", "eclipse", "fop",
    "graphchi", "h2", "jme", "jython", "kafka",
    "luindex", "lusearch", "pmd", "spring", "sunflow",
    "tomcat", "xalan", "zxing"
]

def main():
    print('================= Garbage Log Parser ===============')
    args = parse_arguments()

    if args.runtime:
        # Extracts each run's runtime as presented by DaCapo
        extract_performance_metrics(args.parent_dir, args.compact, args.runs)
    elif args.liveset:
        # Extracts average live set
        process_metrics(liveset_size, args.parent_dir, args.compact, args.runs)
    elif args.gc:
        # Extracts garbage collection pause time, gc count and cpu time
        process_metrics(gc_metrics, args.parent_dir, args.compact, args.runs)
    else:
        sys.exit("No valid option provided. Use -h for help.")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process Java GC logs.')
    parser.add_argument('-liveset', action='store_true', help='Calculate live set sizes. Stores as csv file ending .live')
    parser.add_argument('-gc', action='store_true', help='Gather GC metrics. Stores as csv file ending .gc')
    parser.add_argument('-runtime', action='store_true', help='Extract runtime metrics from *.time files.')
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
    gc_total_time, total_user, total_sys, total_real = 0, 0, 0, 0
    pause_metrics, cpu_metrics = [], []

    for line in lines:
        if 'Pause' in line:
            match = re.search(r'Pause [A-Za-z]+\s+\(.*?\)\s+(\d+)M->\d+M\(\d+M\)\s+(\d+\.\d+)ms', line)
            if match:
                time = float(match.group(2))
                gc_total_time += time
                pause_metrics.append([len(pause_metrics) + 1, time])
        else:
            match = re.search(r'User=(\d+\.\d+)s\s+Sys=(\d+\.\d+)s\s+Real=(\d+\.\d+)s', line)
            if match:
                user_time = float(match.group(1))
                sys_time = float(match.group(2))
                real_time = float(match.group(3))
                total_user += user_time
                total_sys += sys_time
                total_real += real_time
                cpu_metrics.append([len(cpu_metrics) + 1, user_time, sys_time, real_time])

    print_gc_metrics(pause_metrics, gc_total_time, total_user, total_sys, total_real)

    # Create output file paths for this run
    gc_output_file = get_output_file_path(parent_dir, bench, 'gc', compact, run)
    cpu_output_file = get_output_file_path(parent_dir, bench, 'cpu', compact, run)

    # Write metrics to the respective files
    write_to_csv(gc_output_file, [['GC Event', 'Pause Full Time (ms)']] + pause_metrics)
    write_to_csv(cpu_output_file, [['GC Event', 'User CPU Time (s)', 'Sys CPU Time (s)', 'Real Time (s)']] + cpu_metrics)

def print_gc_metrics(pause_metrics, gc_total_time, total_user, total_sys, total_real):
    print(f"GC count: {len(pause_metrics)}")
    print(f"GC pause total time: {gc_total_time}ms")
    print(f"CPU usage: User={total_user}s Sys={total_sys}s Real={total_real}s")

def liveset_size(lines, bench, run, parent_dir, compact):
    live_set_sizes = []
    total_live = 0
    live_pattern = re.compile(r'GC\(\d+\).*?Pause Full.*?(\d+)M->(\d+)M')

    for line in lines:
        match = live_pattern.search(line)
        if match:
            before_gc = int(match.group(1))
            after_gc = int(match.group(2))
            total_live += after_gc
            live_set_sizes.append([len(live_set_sizes) + 1, before_gc, after_gc])

    print(f"GC count: {len(live_set_sizes)}")
    if live_set_sizes:
        print(f"Average live set size: {total_live / len(live_set_sizes)} MB")

    live_output_file = get_output_file_path(parent_dir, bench, 'live', compact, run)
    write_to_csv(live_output_file, [['GC Event', 'Before GC (MB)', 'After GC (MB)']] + live_set_sizes)

def write_to_csv(output_file, data):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

if __name__ == "__main__":
    main()
