package org.sonia;

import org.dacapo.harness.Callback;
import org.dacapo.harness.CommandLineArgs;

public class TimeCallback extends Callback {

    /**
     * Notes the time we started running the first iteration of a given benchmark.
     */
    private long startTime = System.currentTimeMillis();
    public TimeCallback(CommandLineArgs args) {
        super(args);
    }

    @Override
    public void start(String benchmark) {
        super.start(benchmark);
    }

    /**
     * Prints how many seconds after we initially started this benchmark each
     * iteration ends. This is useful as gc logs are measured in seconds
     * relative to start time.
     * @param duration
     */
    @Override
    public void stop(long duration) {
        float endTime = (System.currentTimeMillis() - startTime) / (float) 1000;
        String end = String.format("%sBenchmark ended %fs", isWarmup() ? "Warmup: " : "Measurable: ", endTime);
        System.err.println(end);
        System.err.flush();
    }
}
