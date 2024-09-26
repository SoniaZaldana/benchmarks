# !/bin/bash

# specify location for java and dacapo
java="/root/jdk/build/linux-x86_64-server-release/images/jdk/bin/java"
dacapo="/root/bench/dacapo/dacapo-23.11-chopin.jar"
curr_run=$1
curr_time="`date +"%H-%M-%S_%Y-%m-%d"`"
java_opts="-Xlog:gc*,metaspace*:file=" 

# declare the benchmarks we want to run (all of them except h2o as that requires java versions <= 17) 
 declare -a benchmarks=("avrora" "batik" "cassandra" "eclipse" "fop" "graphchi" "h2" "jme" "jython" "kafka" "luindex" "lusearch" "pmd" "spring" "sunflow" "tomcat" "tradebeans" "tradesoap" "xalan" "zxing")

# TODO - remove. This is just so I don't have to do them all right now. 
#declare -a benchmarks=("batik")

# create a directory to store gc logs and scratch data
scratch_parent="scratch"
gc_parent="logs"
mkdir $scratch_parent 
mkdir $gc_parent 

# Run the above benchmarks 
for bench in "${benchmarks[@]}"
do 
	if [ "$bench" = "h2" ]
       	then 
		java_opts+=" -Djava.security.manager=allow"
	fi

	# Run the benchmark and put all the results in scratch directory. 
	# Also store stdout and stderr accordingly.
	scratch_dir=$scratch_parent/$bench
	gc_file=$gc_parent/$bench.log
	mkdir $scratch_dir
	$java $java_opts$gc_file -jar $dacapo --scratch-directory $scratch_dir $bench
done

