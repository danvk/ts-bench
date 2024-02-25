#!/usr/bin/env python
#
# ./run.py experiment.json

import asyncio
import statistics
import subprocess
import os
import shutil
import sys
import json
import time
from typing import Optional, TypedDict


class Experiment(TypedDict):
    description: Optional[str]
    ref_control: str
    ref_exp: str
    command: str
    ts_dir: str
    num_runs: int


def build_tsc(ts_dir: str, ref: str) -> str:
    init_cwd = os.getcwd()
    os.chdir(ts_dir)
    sha = subprocess.check_output(['git', 'rev-parse', ref]).decode('utf8').strip()
    print(f'{ref=} -> {sha=}')
    tmpdir = f'/tmp/{sha}'
    if os.path.exists(tmpdir):
        return sha, tmpdir
        # shutil.rmtree(tmpdir)
    subprocess.check_call(['git', 'checkout', sha])
    subprocess.check_call(['npx', 'hereby', 'local'])
    shutil.copytree('built', tmpdir)
    subprocess.check_call(['git', 'checkout', '-'])
    os.chdir(init_cwd)
    return sha, tmpdir


def run(cmd, **kwargs):
    stdout = []
    stderr = []
    return_code = None
    with subprocess.Popen(cmd, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        for line in process.stdout:
            line_str = line.decode("utf8")
            print(line_str, end="")
            stdout.append(line_str)
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code)
        stderr = process.stderr.read() if process.stderr else None
        return ('\n'.join(stdout), stderr)


def run_experiment(ts_dir: str, command: str) -> tuple[str, str]:
    command = command.replace('$tsc', f'{ts_dir}/local/tsc.js')
    print(f'Running {command}')

    stdout, stderr = run(command, shell=True)
    if stderr:
        print('stderr:')
        print(stderr)
        print('\n')
    return stdout, stderr


def main():
    exp_file = sys.argv[1]
    exp: Experiment = json.load(open(exp_file))
    print(json.dumps(exp, indent=True))
    (name, _) = os.path.splitext(os.path.basename(exp_file))
    timestamp = time.strftime('%Y-%m-%dT%H%M%S')
    output_file = os.path.abspath(f'results/tmp-{name}-{timestamp}.json')
    final_output_file = os.path.abspath(f'results/{name}-{timestamp}.json')
    control_sha, control_dir = build_tsc(exp['ts_dir'], exp['ref_control'])
    print(f'{control_dir=}')
    exp_sha, exp_dir = build_tsc(exp['ts_dir'], exp['ref_exp'])
    print(f'{exp_dir=}')

    output = {
        'experiment': exp,
        'resolved_shas': {
            'control': control_sha,
            'exp': exp_sha,
        },
        'start_time_secs': time.time(),
        'runs': [],
        'times': {
            'control': [],
            'exp': [],
        },
        'stats': {
            'control': None,
            'exp': None,
        }
    }
    def checkpoint():
        with open(output_file, 'w') as out:
            json.dump(output, out, indent=True)

    checkpoint()
    print(f'Logging results to {output_file}')

    for exp_num in range(exp['num_runs']):
        for arm in ('control', 'exp'):
            print(f'Running {exp_num=} {arm=}')
            start_secs = time.time()
            stdout, stderr = run_experiment(control_dir if arm == 'control' else exp_dir, exp['command'])
            end_secs = time.time()
            elapsed_secs = end_secs - start_secs
            output['runs'].append(
                {
                    'arm': arm,
                    'num': exp_num,
                    'stdout': stdout,
                    'stderr': stderr,
                    'elapsed_time_secs': elapsed_secs,
                }
            )
            output['times'][arm].append(elapsed_secs)
            times = output['times'][arm]
            output['stats'][arm] = {
                'mean': statistics.mean(times),
                'stdev': statistics.stdev(times),
            }
            checkpoint()
            print('\n----\n')

    output['end_time_secs'] = time.time()
    checkpoint()
    shutil.move(output_file, final_output_file)

    stats = output['stats']
    control_mean = stats['control']['mean']
    control_stdev = stats['control']['stdev']
    exp_mean = stats['exp']['mean']
    exp_stdev = stats['exp']['stdev']
    print(f'Control: {control_mean:.2f} +/- {control_stdev:.2f} s')
    print(f'    Exp: {exp_mean:.2f} +/- {exp_stdev:.2f} s')

if __name__ == '__main__':
    main()
