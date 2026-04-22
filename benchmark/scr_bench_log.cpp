#include <iostream>
#include <sstream>
#include <iomanip>
#include <benchmark/benchmark.h>
#include <string>
#include <string_view>
#include <memory>
#include <thread>
#include <atomic>
#include "score/mw/log/logger.h"

std::atomic<int> g_side_effects{0};
std::string get_heavy_metadata() {
    g_side_effects.fetch_add(1, std::memory_order_relaxed);

    std::stringstream ss;

    // Simulate formatting 64 bytes of data
    for(int i = 0; i < 64; ++i) {
        ss << std::hex << std::setw(2) << std::setfill('0') << (i % 255);
    }

    return ss.str();
}

// --- THE FIXTURE ---
class LoggerFixture : public benchmark::Fixture {
public:
    // 1. One-time Initialization per benchmark run
    void SetUp(const ::benchmark::State& state) override {
        //msg = "Score Logging framework benchmark test with metrics";
        msg = get_heavy_metadata();
        g_side_effects = 0; // reset counter
        elogger = std::make_unique<score::mw::log::Logger>("ESBL");
        dlogger = std::make_unique<score::mw::log::Logger>("DSBL");
    }

    // 2. Cleanup after the benchmark finishes
    void TearDown(const ::benchmark::State& state) override {
        // framework_shutdown();
    }

    std::unique_ptr<score::mw::log::Logger> elogger;
    std::unique_ptr<score::mw::log::Logger> dlogger;
    std::string msg;
};

// --- THE BENCHMARK (Using the Fixture) ---
BENCHMARK_F(LoggerFixture, BM_ScoreSteadyStateLogging)(benchmark::State& state) {
    size_t total_bytes = 0;
//    int simulated_allocs = 0;
    size_t alloc_counter = 0;

    for (auto _ : state) {
        // 3. THE HOT PATH (What we are actually measuring)
        // framework_log(msg);
        // msg = get_heavy_metadata();
        alloc_counter++;
        elogger->LogInfo() << msg;
        benchmark::DoNotOptimize(msg.data());

        // Tracking data for metrics
        total_bytes += msg.size();
 //       if (state.iterations() % 500 == 0) simulated_allocs++;
    }

    // --- ADDITIONAL METRICS ---

    // Throughput: Bytes per second (will show as MB/s)
    state.SetBytesProcessed(int64_t(total_bytes));

    // Throughput: Logs per second
    state.SetItemsProcessed(int64_t(state.iterations()));

    // Custom Counter: Allocations (Zero-Copy Check)
    // kIsRate shows average allocs per second
    //state.counters["AllocRate"] = benchmark::Counter(
    //    simulated_allocs, benchmark::Counter::kIsRate);

    state.counters["AllocPerLog"] = benchmark::Counter(
        static_cast<double>(alloc_counter) / state.iterations(),
        benchmark::Counter::kAvgThreads
    );

    // kAvgThreads shows average allocs per log call
    //state.counters["AllocPerLog"] = benchmark::Counter(
    //    simulated_allocs, benchmark::Counter::kAvgThreads);

    state.counters["SideEffects"] = benchmark::Counter(g_side_effects.load());
}

// --- TEST SCORE (DEBUG log while level is FATAL) ---
BENCHMARK_F(LoggerFixture, BM_Score_DisabledLog)(benchmark::State& state) {
    for (auto _ : state) {
        dlogger->LogDebug() << msg;
        benchmark::DoNotOptimize(msg.data());
    }
    state.counters["SideEffects"] = benchmark::Counter(g_side_effects.load());
}

// Register and run
BENCHMARK_MAIN();
