import re
import sys
import argparse
import csv
import os

def main():
    print('================= Garbage Log Parser ===============')

    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Process Java GC logs.')
    parser.add_argument('-liveset', action='store_true', help='Calculate live set sizes. Stores as csv file ending .live')
    parser.add_argument('-gc', action='store_true', help='Gather GC metrics. Stores as csv file ending .gc')
    parser.add_argument('-runtime', action='store_true', help='Extract runtime metrics from *.time files.')
    parser.add_argument('-parent_dir', required=True, help='Parent directory for logs (e.g., parallel or g1)')
    parser.add_argument('-compact', action='store_true', help='Use compact memory option, affecting output file paths')
    parser.add_argument('-runs', type=int, required=True, help='Number of runs to consider for log file naming')

    args = parser.parse_args()

    benchmarks = ["avrora", "batik", "cassandra", "eclipse", "fop", "graphchi", "h2", "jme", "jython", "kafka", "luindex", "lusearch", "pmd", "spring", "sunflow", "tomcat", "xalan", "zxing"]

    # Invoke metrics based on flags
    if args.runtime:
        extract_performance_metrics(benchmarks, args.parent_dir, args.compact, args.runs)
    elif args.liveset:
        do_metrics(liveset_size, benchmarks, args.parent_dir, args.compact, args.runs)
    elif args.gc:
        do_metrics(gc_metrics, benchmarks, args.parent_dir, args.compact, args.runs)
    else:
        parser.print_help()

def main():
    print('================= Garbage Log Parser ===============')

    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Process Java GC logs.')
    parser.add_argument('-liveset', action='store_true', help='Calculate live set sizes. Stores as csv file ending .live')
    parser.add_argument('-gc', action='store_true', help='Gather GC metrics. Stores as csv file ending .gc')
    parser.add_argument('-runtime', action='store_true', help='Extract runtime metrics from *.time files.')
    parser.add_argument('-parent_dir', required=True, help='Parent directory for logs (e.g., parallel or g1)')
    parser.add_argument('-compact', action='store_true', help='Use compact memory option, affecting output file paths')
    parser.add_argument('-runs', type=int, required=True, help='Number of runs to consider for log file naming')

    args = parser.parse_args()

    benchmarks = ["avrora", "batik", "cassandra", "eclipse", "fop", "graphchi", "h2", "jme", "jython", "kafka", "luindex", "lusearch", "pmd", "spring", "sunflow", "tomcat", "xalan", "zxing"]

    # Invoke metrics based on flags
    if args.runtime:
        extract_performance_metrics(benchmarks, args.parent_dir, args.compact, args.runs)
    elif args.liveset:
        do_metrics(liveset_size, benchmarks, args.parent_dir, args.compact, args.runs)
    elif args.gc:
        do_metrics(gc_metrics, benchmarks, args.parent_dir, args.compact, args.runs)
    else:
        parser.print_help()

def extract_performance_metrics(benchmarks, parent_dir, compact, runs):
    for bench in benchmarks:
        print(f"Evaluating benchmark {bench} for runtime metrics")
        runtime_metrics = []

        for run in range(1, runs + 1):
            time_file_path = os.path.join(parent_dir, f'logs{"" if not compact else "_compact"}', f"{bench}_run{run}.time")
            if os.path.exists(time_file_path):
                with open(time_file_path, 'r') as time_file:
                    for line in time_file:
                        # Check for the specific performance line
                        match = re.search(r'===== DaCapo 23.11-chopin (.+?) PASSED in (\d+) msec =====', line)
                        if match:
                            benchmark_name = match.group(1)
                            runtime = match.group(2)
                            runtime_metrics.append([run, runtime])
                            print(f"{benchmark_name} runtime: {runtime} msec")
                            break
            else:
                print(f"Warning: {time_file_path} not found.")

        # Write metrics to CSV
        if runtime_metrics:
            runtime_output_file = os.path.join(parent_dir, f'logs{"" if not compact else "_compact"}', f"{bench}.runtime")
            write_runtime_to_csv(runtime_metrics, runtime_output_file)

def write_runtime_to_csv(runtime_metrics, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Run Number', 'Runtime (msecs)'])
        writer.writerows(runtime_metrics)


def extract_measurable_times(file):
    last_warmup_time = None

    warmup_pattern = re.compile(r'Warmup: Benchmark ended (\d+\.\d+)s')
    with open(file, 'r') as warmup_file:
        for line in warmup_file:
            warmup_match = warmup_pattern.search(line)
            if warmup_match:
                last_warmup_time = float(warmup_match.group(1))

    return last_warmup_time

def filter_gc_logs(gc_file_path, start_time):
    filtered_logs = []
    gc_time_pattern = re.compile(r'\[(\d+\.\d+)s\]')

    with open(gc_file_path, 'r') as gc_file:
        for line in gc_file:
            gc_time_match = gc_time_pattern.search(line)
            if gc_time_match:
                gc_time = float(gc_time_match.group(1))
                if start_time <= gc_time:
                    filtered_logs.append(line.strip())

    return filtered_logs

def do_metrics(func, benchmarks, parent_dir, compact, runs):
    for bench in benchmarks:
        print(f"Evaluating benchmark {bench}")

        for run in range(1, runs + 1):
            print(f"------ Run {run}")
            # Discard warmup metrics
            time_file_path = os.path.join(parent_dir, f'logs{"" if not compact else "_compact"}', f"{bench}_run{run}.time")
            last_warmup_time = extract_measurable_times(time_file_path)
            if last_warmup_time is None:
                print(f"Error: Could not determine warmup logs to discard for {bench} run {run}")
                continue  # Skip this run

            gc_file_path = os.path.join(parent_dir, f'logs{"" if not compact else "_compact"}', f"{bench}_run{run}.log")
            filtered_gc_logs = filter_gc_logs(gc_file_path, last_warmup_time)

            # Invoke metric collection
            if func == liveset_size:
                func(filtered_gc_logs, bench, run, parent_dir, compact)
            else:
                func(filtered_gc_logs, bench, run, parent_dir, compact)
        print("***************************************************")

def gc_metrics(lines, bench, run, parent_dir, compact):
    gc_total_time = 0
    total_user = 0
    total_sys = 0
    total_real = 0

    pause_metrics = []
    cpu_metrics = []

    pause_pattern = re.compile(r'Pause [A-Za-z]+\s+\(.*?\)\s+(\d+)M->\d+M\(\d+M\)\s+(\d+\.\d+)ms')
    cpu_pattern = re.compile(r'User=(\d+\.\d+)s\s+Sys=(\d+\.\d+)s\s+Real=(\d+\.\d+)s')
    for line in lines:
        if 'Pause' in line:
            match = pause_pattern.search(line)
            if match:
                time = match.group(2)
                gc_total_time += float(time)
                pause_metrics.append([len(pause_metrics) + 1, time])
        else:
            match = cpu_pattern.search(line)
            if match:
                user_time = float(match.group(1))
                sys_time = float(match.group(2))
                real_time = float(match.group(3))
                total_user += user_time
                total_sys += sys_time
                total_real += real_time
                cpu_metrics.append([len(cpu_metrics) + 1, user_time, sys_time, real_time])

    print(f"GC count: {len(pause_metrics)}")
    print(f"GC pause total time: {gc_total_time}ms")
    print(f"CPU usage: User={total_user}s Sys={total_sys}s Real={total_real}s")

    # Create output file path for this run
    log_suffix = "_compact" if compact else ""
    gc_output_file = os.path.join(parent_dir, f'logs{log_suffix}', f"{bench}_run{run}.gc")
    cpu_output_file = os.path.join(parent_dir, f'logs{log_suffix}', f"{bench}_run{run}.cpu")

    # Write metrics to the respective files
    write_gc_to_csv(pause_metrics, gc_output_file)
    write_cpu_to_csv(cpu_metrics, cpu_output_file)

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
    if len(live_set_sizes) > 0:
        print(f"Average live set size: {total_live / len(live_set_sizes)} MB")

    # Create output file path for this run
    log_suffix = "_compact" if compact else ""
    live_output_file = os.path.join(parent_dir, f'logs{log_suffix}', f"{bench}_run{run}.live")

    # Write metrics to the respective file
    write_live_set_to_csv(live_set_sizes, live_output_file)

def write_gc_to_csv(gc_metrics, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['GC Event', 'Pause Full Time (ms)'])
        writer.writerows(gc_metrics)

def write_cpu_to_csv(cpu_metrics, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['GC Event', 'User CPU Time (s)', 'Sys CPU Time (s)', 'Real Time (s)'])
        writer.writerows(cpu_metrics)

def write_live_set_to_csv(live_set_metrics, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['GC Event', 'Before GC (MB)', 'After GC (MB)'])
        writer.writerows(live_set_metrics)

if __name__ == "__main__":
    main()
