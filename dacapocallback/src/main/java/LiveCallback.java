package org.sonia;

import org.dacapo.harness.Callback;
import org.dacapo.harness.CommandLineArgs;

public class LiveCallback extends Callback {

    /**
     * Notes how many warmup iterations we have completed.
     */
    private long warmupCount = 0;
    private long startTime = System.currentTimeMillis();

    public LiveCallback(CommandLineArgs args) {
        super(args);
    }

    @Override
    public void start(String benchmark) {
        warmupCount++;
        super.start(benchmark);
    }

    /**
     * Prints whether I quantify the last run as a warmup or measurable run.
     */
    @Override
    public void stop(long duration) {
        float endTime = (System.currentTimeMillis() - startTime) / (float) 1000;
        boolean warmup = warmupCount < 20; // we discard 20 warmup runs. 
        String end = String.format("%sBenchmark ended %fs", warmup ? "Warmup: " : "Measurable: ", endTime);
        System.err.println(end);
        System.err.flush();
    }
}
