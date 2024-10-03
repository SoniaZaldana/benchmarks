#!/bin/bash

# Function to display usage information
usage() {
    echo "Usage: $0 -n <number_of_runs> [-parallel] [-compact]"
    exit 1
}

# Default values
num_runs=1
parallel=false
compact=false

# Parse command line arguments
while getopts ":n:p:c:" opt; do
    case $opt in
        n)
            num_runs="$OPTARG"
            ;;
        p)
            parallel=true
            ;;
        c)
            compact=true
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            ;;
    esac
done

# Cleanup old directories
rm -rf parallel g1

# Java and DaCapo paths
java="/home/szaldana/jdk/build/linux-x86_64-server-release/images/jdk/bin/java" # local
# java="/root/tests/jdk/build/linux-x86_64-server-release/images/jdk/bin/java"  # beaker
dacapo="dacapo-23.11-chopin.jar"
callback="../dacapocallback/target/dacapocallback-1.0-SNAPSHOT.jar"
java_opts="-XX:+UnlockExperimentalVMOptions"

# Add options based on flags
if $parallel; then
    java_opts="$java_opts -XX:+UseParallelGC"
fi

if $compact; then
    java_opts="$java_opts -XX:+UseCompactObjectHeaders"
fi

# Print JAVA_OPTS and number of iterations
echo "JAVA_OPTS: $java_opts"
echo "Number of runs: $num_runs"

# Set parent directory based on compact flag
if $parallel; then
    parent_dir="parallel"
else
    parent_dir="g1"
fi

# Create parent directory
mkdir -p "$parent_dir"

# Set subdirectory names based on compact flag
if $compact; then
    scratch_parent="$parent_dir/scratch_compact"
    gc_parent="$parent_dir/logs_compact"
else
    scratch_parent="$parent_dir/scratch"
    gc_parent="$parent_dir/logs"
fi

# Create scratch and logs directories
mkdir -p "$scratch_parent"
mkdir -p "$gc_parent"

# Declare benchmarks
declare -a benchmarks=("avrora" "batik" "cassandra" "eclipse" "fop" "graphchi" "h2" "jme" "jython" "kafka" "luindex" "lusearch" "pmd" "spring" "sunflow" "tomcat" "tradebeans" "tradesoap" "xalan" "zxing")

# Build latest callback
echo "Building latest callback version"
(cd ../dacapocallback && mvn clean install)

# Run benchmarks and collect GC log files
for bench in "${benchmarks[@]}"; do
    for ((run=1; run<=num_runs; run++)); do
        echo "******************* Running benchmark $bench - Run $run *******************"

        # Set additional Java options based on benchmark type
        if [[ "$bench" == "h2" || "$bench" == "cassandra" ]]; then
            java_opts="$java_opts -Djava.security.manager=allow"
        fi

        # Determine load size
        size="large"
        if [[ "$bench" == "zxing" || "$bench" == "fop" ]]; then
            size="default"
        fi

        # Prepare directories and log files with run number
        scratch_dir="$scratch_parent/${bench}_run${run}"
        gc_file="$gc_parent/${bench}_run${run}.log"
        time_log="$gc_parent/${bench}_run${run}.time"

        # Create the specific scratch directory for this run
        mkdir -p "$scratch_dir"
        touch "$time_log"

        # Run the benchmark
        $java $java_opts -Xlog:gc*,metaspace*:file="$gc_file" -cp "$callback:$dacapo" Harness -c org.sonia.TimeCallback -s "default" -n 1 --scratch-directory "$scratch_dir" "$bench" 2> "$time_log"
    done
done