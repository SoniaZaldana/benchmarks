import re
import sys


def main():
    print('================= Garbage Log Parser ===============')

    benchmarks = ["avrora", "batik", "cassandra", "eclipse", "fop", "graphchi", "h2", "jme", "jython", "kafka", "luindex", "lusearch", "pmd", "spring", "sunflow", "tomcat", "tradebeans", "tradesoap", "xalan", "zxing"]

    # benchmarks = ["jython"]

    for bench in benchmarks:
        print("Evaluating benchmark: " + bench)

        # Read file
        filename = "logs/" + bench + ".log"
        file = open(filename, "r")
        lines = file.readlines()

        # Calculate garbage collection count
        garbage_stats(lines)

        # Calculate liveset size
        liveset_size(lines)

        print("***************************************************")


def garbage_stats(lines):
    gc_count = 0
    gc_total_time = 0
    total_user = 0
    total_sys = 0
    total_real = 0
    for line in lines:
        # Calculate full gc count and time
        full = re.search("Pause Full", line)
        if full != None:
            time_full = re.findall("\\d*.\\d\\d\\dms", full.string)
            if time_full != None and len(time_full) == 1:
                gc_count += 1
                time = time_full[0]
                # print("     Full pause: " + time) # for debugging
                # Remove ms from time measurement
                gc_total_time += float(time[:len(time) - 2])

        # Calculate CPU stats
        cpu = re.search("User=\\d+.\\d+s Sys=\\d+.\\d+s Real=\\d+.\\d+s", line)
        if cpu != None:
            cpu_times = re.findall("=\\d+.\\d+s", cpu.string)
            total_user += float(cpu_times[0][1:-1])
            total_sys += float(cpu_times[1][1:-1])
            total_real += float(cpu_times[2][1:-1])

    print("GC count: " + str(gc_count))
    print("GC Full total time: " + str(gc_total_time) + "ms")
    print("CPU Usage: User=" + str(total_user) + " Sys=" + str(total_sys) + " Real=" + str(total_real))

def liveset_size(lines):
    gc_count = 0
    liveset = 0
    for line in lines:
        # Calculate full gc count and time
        full = re.search("Pause Full", line)
        if full != None:
            size = re.findall("->\\d+M", full.string)
            if size != None and len(size) == 1:
                gc_count += 1

                # print("     Full pause: " + time) # for debugging
                # Remove -> and M from measurement
                liveset += float(size[0][2:-1])

    print("GC count: " + str(gc_count))
    if (gc_count > 0):
        print("Average liveset size " + str(int(liveset / gc_count)) + "M")


if __name__ == "__main__":
    main()