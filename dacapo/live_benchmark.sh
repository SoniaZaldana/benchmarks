#!/bin/bash

# Function to display usage information
usage() {
    echo "Usage: $0 -n <number_of_runs> [-p] [-c]"
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
jcmd="/home/szaldana/jdk/build/linux-x86_64-server-release/images/jdk/bin/jcmd" # local

# java="/root/tests/jdk/build/linux-x86_64-server-release/images/jdk/bin/java"  # beaker
# jcmd="/root/tests/jdk/build/linux-x86_64-server-release/images/jdk/bin/jcmd"  # beaker


dacapo="dacapo-23.11-chopin.jar"
callback="../dacapocallback/target/dacapocallback-1.0-SNAPSHOT.jar"
java_opts="-XX:+UnlockExperimentalVMOptions -Xms256m"

# Add options based on flags
if $parallel; then
    java_opts="$java_opts -XX:+UseParallelGC"
fi

if $compact; then
    java_opts="$java_opts -XX:+UseCompactObjectHeaders"
fi

# Additional Java options
java_opts="$java_opts \
  --add-exports java.base/jdk.internal.ref=ALL-UNNAMED \
  --add-exports java.base/jdk.internal.misc=ALL-UNNAMED \
  --add-exports java.base/sun.nio.ch=ALL-UNNAMED \
  --add-exports java.management.rmi/com.sun.jmx.remote.internal.rmi=ALL-UNNAMED \
  --add-exports java.rmi/sun.rmi.registry=ALL-UNNAMED \
  --add-exports java.rmi/sun.rmi.server=ALL-UNNAMED \
  --add-exports java.sql/java.sql=ALL-UNNAMED \
  --add-exports java.base/jdk.internal.math=ALL-UNNAMED \
  --add-exports java.base/jdk.internal.module=ALL-UNNAMED \
  --add-exports java.base/jdk.internal.util.jar=ALL-UNNAMED \
  --add-exports jdk.management/com.sun.management.internal=ALL-UNNAMED \
  --add-opens java.base/java.lang=ALL-UNNAMED \
  --add-opens java.base/java.lang.module=ALL-UNNAMED \
  --add-opens java.base/java.net=ALL-UNNAMED \
  --add-opens java.base/jdk.internal.loader=ALL-UNNAMED \
  --add-opens java.base/jdk.internal.ref=ALL-UNNAMED \
  --add-opens java.base/jdk.internal.reflect=ALL-UNNAMED \
  --add-opens java.base/java.io=ALL-UNNAMED \
  --add-opens java.base/sun.nio.ch=ALL-UNNAMED \
  --add-opens java.base/java.util=ALL-UNNAMED \
  --add-opens java.base/java.util.concurrent=ALL-UNNAMED \
  --add-opens java.base/java.util.concurrent.atomic=ALL-UNNAMED \
  --add-opens java.base/java.nio=ALL-UNNAMED"

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
# declare -a benchmarks=("avrora")
# declare -a benchmarks=("avrora" "batik" "cassandra" "eclipse" "fop" "graphchi" "h2" "jme" "jython" "kafka" "luindex" "lusearch" "pmd" "spring" "sunflow" "tomcat" "xalan" "zxing")


# Build latest callback
echo "Building latest callback version"
(cd ../dacapocallback && mvn clean install)

# Function to run GC command
run_gc() {
    OUTPUT=$(jps -l | grep Harness | awk '{print $1}')
    $jcmd $OUTPUT GC.run
}

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

        # Start GC script in the background
        (
            while true; do
                run_gc
                sleep 180 # Run every 3 minutes
            done
        ) & gc_pid=$!

        # Run the benchmark
        $java $java_opts -Xlog:gc*,metaspace*:file="$gc_file" -cp "$callback:$dacapo" Harness -c org.sonia.LiveCallback -s "$size" --no-pre-iteration-gc -n 30 --scratch-directory "$scratch_dir" "$bench" 2> "$time_log"

        # Stop the GC process after benchmark completes
        kill "$gc_pid"
        wait "$gc_pid" 2>/dev/null # Wait for the GC process to finish
    done
done
