import re
import sys
import argparse
import csv

def main():
    print('================= Garbage Log Parser ===============')

    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Process Java GC logs.')
    parser.add_argument('-liveset', action='store_true', help='Calculate live set sizes. Stores as csv file ending .live')
    parser.add_argument('-gc', action='store_true', help='Gather GC metrics. Stores as csv file ending .gc')

    args = parser.parse_args()

    # benchmarks = ["avrora", "batik", "cassandra", "eclipse", "fop", "graphchi", "h2", "jme", "jython", "kafka", "luindex", "lusearch", "pmd", "spring", "sunflow", "tomcat", "tradebeans", "tradesoap", "xalan", "zxing"]

    benchmarks = ["avrora"]

    # Invoke metrics based on flags
    if args.liveset:
        do_metrics(liveset_size, benchmarks)
    elif args.gc:
        do_metrics(gc_metrics, benchmarks)
    else:
        parser.print_help()


def do_metrics(func, benchmarks):
    for bench in benchmarks:
        print(f"Evaluating benchmark {bench}")

        # Read file
        filename = "logs/" + bench + ".log"
        file = open(filename, "r")
        lines = file.readlines()

        # Invoke metric collection
        func(lines, bench)
        print("***************************************************")


def gc_metrics(lines, bench):
    gc_total_time = 0
    total_user = 0
    total_sys = 0
    total_real = 0

    pause_metrics = []
    cpu_metrics = []

    pause_pattern = re.compile(r'Pause\s+Full.*?(\d+\.\d+)ms')
    cpu_pattern = re.compile(r'User=(\d+\.\d+)s\s+Sys=(\d+\.\d+)s\s+Real=(\d+\.\d+)s')
    for line in lines:
        if 'Pause Full' in line:
            # Calculate full gc count and time
            match = pause_pattern.search(line)
            if match:
                time = match.group(1)
                gc_total_time += float(time)
                pause_metrics.append([len(pause_metrics) + 1, time])
        else:
            # Calculate cpu stats
            match = cpu_pattern.search(line)
            if match:
                user_time = float(match.group(1))
                sys_time = float(match.group(2))
                real_time = float(match.group(3))
                total_user += user_time
                total_sys += sys_time
                total_sys += real_time
                cpu_metrics.append([len(cpu_metrics) + 1, user_time, sys_time, real_time])

    print(f"GC count: {len(pause_metrics)}")
    print(f"GC full total time: {gc_total_time}ms")
    print(f"CPU usage: User={total_user}s Sys={total_sys}s Real={total_real}s")

    write_gc_to_csv(pause_metrics, "logs/" + bench + ".gc")
    write_cpu_to_csv(cpu_metrics, "logs/" + bench + ".cpu")

def liveset_size(lines, bench):
    live_set_sizes = []
    total_live = 0
    live_pattern = re.compile(r'GC\(\d+\).*?Pause Full.*?(\d+)M->(\d+)M')
    for line in lines:
        # Calculate full gc count and time
        match = live_pattern.search(line)
        if match:
            # Memory before and after GC
            before_gc = int(match.group(1))  # before
            after_gc = int(match.group(2))   # after
            total_live += after_gc
            live_set_sizes.append([len(live_set_sizes) + 1, before_gc, after_gc])

    print(f"GC count: {len(live_set_sizes)}")
    if (len(live_set_sizes) > 0):
        print(f"Average liveset size: {total_live / len(live_set_sizes)}")
    write_live_set_to_csv(live_set_sizes, "logs/" + bench + ".live")

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