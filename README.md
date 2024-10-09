# An investigation on [Project Lilliput's]([url](https://openjdk.org/projects/lilliput/)) effects on Garbage Collection. 

## Rough Methodology (in progress)

### Choice of benchmark 
I use the [latest version]( https://github.com/dacapobench/dacapobench/releases/tag/v23.11-chopin) of the DaCapo benchmark suite.

### Load size 
Since there are different sizes available for the workloads’ inputs in DaCapo, I set the input size using the switch `-s`. 
I use a `large` load if available to increase the number of live objects in the heap and make GCs work frequently. 
Otherwise, I set the input size to default (benchmarks `zxing` and `fop`). 

### DaCapo's System.gc() calls 
DaCapo automatically triggers a System.gc() call before the start of each iteration. I explicitly disable GC calls in the workload’s call using the `-no-pre-iteration-gc` switch so as to not skew GC metrics. 

### Benchmark incompatibilities:
Some benchmarks are incompatible with my experiment:
- `h2o` requires a JDK version <= 17, so I am omitting it.
- `tradebeans` and `tradesoap` are incompatible with JDK 21+, as WildFly 26 is [incompatible](https://github.com/dacapobench/dacapobench/issues/252) with versions higher than 21.
- `h2` and `cassandra` required enabling the Java Security Manager. I have enabled it for those benchmarks. 

### Choice of Heap Size
GCs are sensitive to heap size. A large heap means there is lots of memory to assign new objects. Conversely, small heaps cause frequent garbage collections to free more memory; leading to obvious impacts on GC's pause times. Ideally, I should conduct this experiment in heap size evaluations of `256`, `512`, `1024`, `2048`, `4096` and `8192` MB per [similar GC studies]([url](https://www.dpss.inesc-id.pt/~rbruno/papers/stavakolisomeh-access23.pdf)). 

Controlling the heap size, I ensure we are working on the same workloads with the same heap availability. 

### Choice of garbage collector
I am conducting this experiment using G1 and the parallel collector.

### Warmup
I warmup each benchmark by executing it `20` times before measuring results.  I chose 20 because DaCapo suite’s built-in mechanism automatically detects a steady state after at most 20 warmups. [Source](https://research.spec.org/icpe_proceedings/2017/proceedings/p3.pdf). 

I specify the number of iterations using the `-n` switch. 

### Calculating GC pause time: 
To extract GC pause times, I use the JVM log files corresponding to executing each workload. I then aggregate the number of gc events and their length, along with CPU times. 

Since JVM gc logs contain logs from all iterations, including warmup ones, and DaCapo doesn’t have built-in functionality to specify the time iterations started/ended, discardings logs corresponding to warmup iterations is not a trivial task. 
To accomplish the above, I need to determine the range of time that corresponds to warm up iterations in the gc log file. DaCapo supports specifying custom callbacks which are triggered before/after each iteration, so I worked on a custom one to report time and whether the iteration is a warm up or measurable one. I can then refer to those timestamps to filter my gc logs accordingly. 

### Calculating liveset size
To extract liveset sizes, I force full garbage collections using a jcmd’s `GC.run` periodically (every 3 minutes). I then scan for the "Full GC" messages in the GC log and extract the post-GC heap usage.

I also do this after warming up for 20 iterations. Then, I run each benchmark 10 times and pepper in full garbage collections periodically during that period. 
To discard gc logs for warmup iterations, I implemented a custom callback to print to stderr when an interaction is a warmup one or a measurable one along with their respective timestamps. 

## Scripts 

This repository consists of three main scripts: 

### benchmark.sh 
```
Usage: benchmark.sh -n <number_of_runs> [-parallel] [-compact]
``` 
Runs the DaCapo benchmarks following the methodology described above. You can specify `-parallel` to use the Parallel Garbage Collector but it uses G1 by default. Specifying `-compact` enables Lilliput's compact object headers (`-XX:+UseCompactObjectHeaders`)

The script then collects gc logs, perf information, important timestamps and stdout/stderr in text files ready to be analyzed. 

### live_benchmark.sh
```
Usage: live_benchmark.sh -n <number_of_runs> [-parallel] [-compact]
```

Similar to the script above, except it peppers in periodic full gargabe collection cycles. 

### garbage.py 
```
================= Garbage Log Parser ===============
usage: garbage.py [-h] [-liveset] [-gc] [-runtime] -parent_dir PARENT_DIR [-compact] -runs RUNS

Process Java GC logs.

options:
  -h, --help            show this help message and exit
  -liveset              Calculate live set sizes. Stores as csv file ending .live
  -gc                   Gather GC metrics. Stores as csv file ending .gc
  -runtime              Extract runtime metrics from *.time files.
  -parent_dir PARENT_DIR
                        Parent directory for logs (e.g., parallel or g1)
  -compact              Use compact memory option, affecting output file paths
  -runs RUNS            Number of runs to consider for log file naming
```
Python script to analyze all the files we generated above and extract the following metrics: 

1) Average Liveset Size

2) GC metrics (number of GCs, full pause time, CPU times (real/sys/user). 

Stores the metrics in .csv files. 
