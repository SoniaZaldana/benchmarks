import re
import sys
import argparse
import csv
import os

BENCHMARKS = [
    "avrora", "eclipse", "fop", "jme", "jython",
    "kafka", "luindex", "lusearch", "pmd", "spring", "sunflow",
]

def main():
    print('================= Garbage Log Parser ===============')
    args = parse_arguments()
    process_metrics(liveset_size if args.liveset else gc_metrics, args.parent_dir, args.compact, args.n)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process Java GC logs.')
    parser.add_argument('-liveset', action='store_true', help='Calculate live set sizes. Stores as csv file ending .live')
    parser.add_argument('parent_dir', help='Parent directory for logs (e.g., parallel or g1)')
    parser.add_argument('-compact', action='store_true', help='Use compact memory option, affecting output file paths')
    parser.add_argument('-n', type=int, required=True, help='Number of runs to consider for log file naming')
    return parser.parse_args()

def process_metrics(metric_func, parent_dir, compact, runs):
    all_pause_times = []
    cpu_metrics = []

    for bench in BENCHMARKS:
        print(f"Evaluating benchmark {bench}")
        runtime_metrics = extract_runtime_metrics(parent_dir, bench, compact, runs)

        cpu_metrics.clear()
        all_pause_times.clear()

        for run in range(1, runs + 1):
            print(f"------ Run {run}")
            last_warmup_time = extract_measurable_times(get_log_file_path(parent_dir, bench, run, 'time', compact))
            if last_warmup_time is None:
                print(f"Error: Could not determine warmup logs for {bench} run {run}")
                continue

            filtered_gc_logs = filter_gc_logs_for_runs(parent_dir, bench, run, compact, last_warmup_time)
            metric_func(filtered_gc_logs, bench, run, parent_dir, compact, all_pause_times, cpu_metrics)

        write_aggregated_gc_data(all_pause_times, bench, parent_dir, compact, runs)
        write_cpu_metrics_to_csv(parent_dir, bench, cpu_metrics, compact) 

def extract_runtime_metrics(parent_dir, bench, compact, runs):
    metrics = []
    for run in range(1, runs + 1):
        time_file_path = get_log_file_path(parent_dir, bench, run, 'time', compact)
        if os.path.exists(time_file_path):
            runtime = extract_runtime_from_file(time_file_path)
            if runtime is not None:
                metrics.append([run, runtime])
                print(f"{bench} runtime: {runtime} ms")
        else:
            print(f"Warning: {time_file_path} not found.")
    if metrics:
        write_to_csv(get_output_file_path(parent_dir, bench, 'runtime', compact), [['Run', 'Runtime (ms)']] + metrics)

def filter_gc_logs_for_runs(parent_dir, bench, run, compact, last_warmup_time):
    gc_file_paths = [
        get_log_file_path(parent_dir, bench, run, 'log', compact),
        get_log_file_path(parent_dir, bench, f"{run}.0", 'log', compact)
    ]
    return [line.strip() for gc_file_path in gc_file_paths if os.path.exists(gc_file_path)
            for line in filter_gc_logs(gc_file_path, last_warmup_time)]

def get_log_file_path(parent_dir, bench, run, file_type, compact):
    suffix = "_compact" if compact else ""
    return os.path.join(parent_dir, f'logs{suffix}', f"{bench}_run{run}.{file_type}")

def get_output_file_path(parent_dir, bench, metric_type, compact):
    suffix = "_compact" if compact else ""
    return os.path.join(parent_dir, f'logs{suffix}', f"{bench}_{metric_type}.csv")  # Updated here

def extract_runtime_from_file(file_path):
    pattern = re.compile(r'===== DaCapo 23.11-chopin (.+?) PASSED in (\d+) msec =====')
    with open(file_path) as file:
        return next((match.group(2) for line in file if (match := pattern.search(line))), None)

def extract_measurable_times(file):
    pattern = re.compile(r'Warmup: Benchmark ended (\d+\.\d+)s')
    with open(file) as warmup_file:
        return next((float(match.group(1)) for line in warmup_file if (match := pattern.search(line))), None)

def filter_gc_logs(gc_file_path, start_time):
    pattern = re.compile(r'\[(\d+\.\d+)s\]')
    with open(gc_file_path) as gc_file:
        return [line for line in gc_file if (match := pattern.search(line)) and float(match.group(1)) >= start_time]

def gc_metrics(lines, bench, run, parent_dir, compact, all_pause_times, cpu_metrics):
    gc_total_time, pause_metrics = 0, []

    total_user, total_sys, total_real = 0, 0, 0
    for line in lines:
        if 'Pause' in line:
            match = re.search(r'Pause [A-Za-z]+\s+\(.*?\)\s+(\d+)M->\d+M\(\d+M\)\s+(\d+\.\d+)ms', line)
            if match:
                pause_metrics.append(float(match.group(2)))
                gc_total_time += float(match.group(2))
        else:
            match = re.search(r'User=(\d+\.\d+)s\s+Sys=(\d+\.\d+)s\s+Real=(\d+\.\d+)s', line)
            if match:
                total_user += float(match.group(1))
                total_sys += float(match.group(2))
                total_real += float(match.group(3))

    print_gc_metrics(pause_metrics, gc_total_time, total_user, total_sys, total_real)
    all_pause_times.append(pause_metrics)
    cpu_metrics.append([run, total_user, total_sys, total_real])

def print_gc_metrics(pause_metrics, gc_total_time, total_user, total_sys, total_real):
    print(f"GC count: {len(pause_metrics)}")
    print(f"GC pause total time: {gc_total_time}ms")
    print(f"CPU usage: User={total_user}s Sys={total_sys}s Real={total_real}s")

def liveset_size(lines, bench, run, parent_dir, compact):
    live_set_sizes = []
    total_live = 0
    live_pattern = re.compile(r'GC\(\d+\).*?Pause Full.*?(\d+)M->(\d+)M')

    for line in lines:
        if (match := live_pattern.search(line)):
            before_gc, after_gc = int(match.group(1)), int(match.group(2))
            total_live += after_gc
            live_set_sizes.append([len(live_set_sizes) + 1, before_gc, after_gc])

    print(f"GC count: {len(live_set_sizes)}")
    if live_set_sizes:
        print(f"Average live set size: {total_live / len(live_set_sizes)} MB")

    write_to_csv(get_output_file_path(parent_dir, bench, 'live', compact), [['GC Event', 'Before GC (MB)', 'After GC (MB)']] + live_set_sizes)

def write_aggregated_gc_data(all_pause_times, bench, parent_dir, compact, runs):
    aggregated_data = [['GC Event'] + [f'Pause time (ms) Run {i+1}' for i in range(runs)]]
    max_gc_events = max(len(run) for run in all_pause_times)

    for i in range(max_gc_events):
        row = [i + 1] + [run_pause_times[i] if len(run_pause_times) > i else 0 for run_pause_times in all_pause_times]
        aggregated_data.append(row)

    total_row = ['Total pause time'] + [sum(row[run_index + 1] for row in aggregated_data[1:]) for run_index in range(runs)]
    count_row = ['Total event count'] + [sum(1 for row in aggregated_data[1:] if row[run_index + 1] > 0) for run_index in range(runs)]

    aggregated_data += [count_row, total_row]
    write_to_csv(get_output_file_path(parent_dir, bench, 'gc', compact), aggregated_data)

def write_cpu_metrics_to_csv(parent_dir, bench, cpu_metrics, compact):
    cpu_file_path = get_output_file_path(parent_dir, bench, 'cpu', compact)
    headers = ["Run", "Total User (s)", "Total Sys (s)", "Total Real (s)"]

    with open(cpu_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(cpu_metrics)

def write_to_csv(output_file, data):
    with open(output_file, 'w', newline='') as csvfile:
        csv.writer(csvfile).writerows(data)

if __name__ == "__main__":
    main()
