# TypeScript Benchmark Test Harness

This script runs two versions of TypeScript against the same codebase to test for performance
differences. This was motivated by a desire to reproduce the "Compiler-Unions" benchmark for [TypeScript#57465].

Experiments are specified in JSON files, check out the [experiments](/experiments/) directory for for more examples.

```json
{
    "description": "Compare PR branch to main",
    "ref_control": "main",
    "ref_exp": "pr-branch",
    "command": "cd /Users/danvk/code/TypeScript-Compiler-Unions; npx hereby clean-src && node $tsc -b --emitDeclarationOnly false src/compiler --extendedDiagnostics",
    "ts_dir": "/Users/danvk/github/TypeScript",
    "num_runs": 8
}
```

Run via:

```sh
$ ./run.py experiments/branch-vs-main.json
...
Control: 31.82 +/- 1.92 s
    Exp: 31.81 +/- 1.49 s = -0.05%
```

Runs are interleaved to try and reduce bias from whatever else your computer happens to be doing.

[TypeScript#57465]: https://github.com/microsoft/TypeScript/pull/57465
