# !/bin/bash

# cleanup
rm -r -f logs scratch

# TODO update these to the proper Java version I'm measuring.
java="/home/szaldana/jdk/build/linux-x86_64-server-release/images/jdk/bin/java"
dacapo="dacapo-23.11-chopin.jar"
curr_time="`date +"%H-%M-%S_%Y-%m-%d"`"
java_opts=""
testing_opts="-XX:+UnlockExperimentalVMOptions -XX:-UseCompactObjectHeaders"

# declare the benchmarks we want to run (all of them except h2o as that requires java versions <= 17)
 declare -a benchmarks=("avrora" "batik" "cassandra" "eclipse" "fop" "graphchi" "h2" "jme" "jython" "kafka" "luindex" "lusearch" "pmd" "spring" "sunflow" "tomcat" "tradebeans" "tradesoap" "xalan" "zxing")

# TODO - remove. This is just so I don't have to do them all right now.
#declare -a benchmarks=("batik")

# create a directory to store gc logs and scratch data
scratch_parent="scratch"
gc_parent="logs"
mkdir $scratch_parent
mkdir $gc_parent

# Run the above benchmarks and collect gc log files
for bench in "${benchmarks[@]}"
do
        echo "******************* Running benchmark $bench *******************"
        if [ "$bench" = "h2" ] || [ "$bench" = "cassandra" ]
        then
                java_opts=" -Djava.security.manager=allow"
        else
                java_opts=""
        fi

        # Run the benchmark and put all the results in scratch directory.
        # Also store gc logs.
        scratch_dir=$scratch_parent/$bench
        gc_file=$gc_parent/$bench.log
        mkdir $scratch_dir
        # TODO add -n 21 to stabilize the benchmark with 20 runs.
        $java $java_opts $testing_opts -Xlog:gc*,metaspace*:file=$gc_file -jar $dacapo --scratch-directory $scratch_dir $bench

done


