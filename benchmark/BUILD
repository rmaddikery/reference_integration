load(":opt_transition.bzl", "opt_binary")

cc_binary(
  name = "scr_bench_log",
  srcs = [
    "scr_bench_log.cpp"
  ],
  data = ["etc/logging.json"],
  visibility = ["//visibility:public"],
  deps = [
    "@google_benchmark//:benchmark",
    "@google_benchmark//:benchmark_main",
    "@score_logging//score/mw/log",
  ],
)

# Forces the benchmark to be built with -c opt even when the rest is debug
opt_binary(
  name = "scr_bench_log_opt",
  binary = ":scr_bench_log",
  data = ["etc/logging.json"],
  visibility = ["//visibility:public"],
)

exports_files([
    "etc/logging.json",
])

filegroup(
    name = "etc_configs",
    srcs = ["etc/logging.json"],
    visibility = ["//visibility:public"],
)

