# !/bin/bash

# cleanup
rm -r -f logs scratch

# TODO update these to the proper Java version I'm measuring.
java="/home/szaldana/jdk/build/linux-x86_64-server-release/images/jdk/bin/java"
dacapo="dacapo-23.11-chopin.jar"
callback="../dacapocallback/target/dacapocallback-1.0-SNAPSHOT.jar"
curr_time="`date +"%H-%M-%S_%Y-%m-%d"`"
java_opts=""
testing_opts="-XX:+UnlockExperimentalVMOptions -XX:-UseCompactObjectHeaders"

# declare the benchmarks we want to run (all of them except h2o as that requires java versions <= 17)
 declare -a benchmarks=("avrora" "batik" "cassandra" "eclipse" "fop" "graphchi" "h2" "jme" "jython" "kafka" "luindex" "lusearch" "pmd" "spring" "sunflow" "tomcat" "tradebeans" "tradesoap" "xalan" "zxing")

# TODO - remove. This is just so I don't have to do them all right now.
#declare -a benchmarks=("batik")

# Build latest callback
echo "Building latest callback version"
cd ../dacapocallback
mvn clean install
cd ../dacapo

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

        # Determine load size. Large for all unless unavailable.
        size="large"
        if [ "$bench" = "zxing" ] || [ "$bench" = "fop" ]
        then
                size="default"
        fi

        # Run the benchmark and put all the results in scratch directory.
        # Also store gc logs.
        scratch_dir=$scratch_parent/$bench
        gc_file=$gc_parent/$bench.log
        time_log=$gc_parent/$bench.time
        mkdir $scratch_dir
        touch $time_log
        # TODO add -n 21 to stabilize the benchmark with 20 runs.
        $java $java_opts $testing_opts -Xlog:gc*,metaspace*:file=$gc_file -cp $callback:$dacapo Harness -c org.sonia.TimeCallback -s $size -n 6 --scratch-directory $scratch_dir $bench 2> $time_log

done


