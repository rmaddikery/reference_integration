# Transition rule that forces a target to be built with -c opt

def _opt_transition_impl(settings, attr):
    return {"//command_line_option:compilation_mode": "opt"}

_opt_transition = transition(
    implementation = _opt_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:compilation_mode"],
)

def _opt_binary_impl(ctx):
    # Note: ctx.attr.binary is a list when using transitions
    binary_target = ctx.attr.binary[0]
    src_executable = ctx.executable.binary

    # Create a symlink to the actual executable (executable must be created by this rule)
    out = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.symlink(output = out, target_file = src_executable, is_executable = True)

    runfiles = ctx.runfiles(files = ctx.files.data)
    runfiles = runfiles.merge(binary_target[DefaultInfo].default_runfiles)

    return [DefaultInfo(
        executable = out,
        files = depset([out]),
        runfiles = runfiles,
    )]

opt_binary = rule(
    implementation = _opt_binary_impl,
    attrs = {
        "binary": attr.label(
            cfg = _opt_transition,
            executable = True,
            mandatory = True,
        ),
        "data": attr.label_list(
            allow_files = True,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
    executable = True,
)
