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
        shutil.rmtree(tmpdir)
    subprocess.check_call(['git', 'checkout', sha])
    subprocess.check_call(['npx', 'hereby', 'local'])
    shutil.copytree('built', tmpdir)
    subprocess.check_call(['git', 'checkout', '-'])
    os.chdir(init_cwd)
    return sha, tmpdir


def run_experiment(ts_dir: str, command: str) -> tuple[str, str]:
    command = command.replace('$tsc', f'{ts_dir}/local/tsc.js')
    print(f'Running {command}')

    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()

    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode)

    stdout = stdout.decode('utf8')
    stderr = stderr.decode('utf8')
    print('stdout:')
    print(stdout)
    print('\nstderr:')
    print(stderr)
    print('\n')


def main():
    exp_file = sys.argv[1]
    exp: Experiment = json.load(open(exp_file))
    print(json.dumps(exp, indent=True))
    control_sha, control_dir = build_tsc(exp['ts_dir'], exp['ref_control'])
    print(f'{control_dir=}')
    exp_sha, exp_dir = build_tsc(exp['ts_dir'], exp['ref_exp'])
    print(f'{exp_dir=}')

    (name, _) = os.path.splitext(os.path.basename(exp_file))
    timestamp = time.strftime('%Y-%m-%dT%H%M%S')
    output_file = f'results/{name}-{timestamp}.json'
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
            json.dump(output, out)

    checkpoint()
    print(f'Logging results to {output_file}')

    for exp_num in range(exp['num_runs']):
        print(f'Running {exp_num=}')
        for arm in ('control', 'exp'):
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
            output['stats']['arm'] = {
                'mean': statistics.mean(times),
                'stdev': statistics.pstdev(times),
            }
            checkpoint()

    output['end_time_secs'] = time.time()
    checkpoint()

    stats = output['stats']
    control_mean = stats['control']['mean']
    control_stdev = stats['control']['stdev']
    exp_mean = stats['exp']['mean']
    exp_stdev = stats['exp']['stdev']
    print(f'Control: {control_mean:.2f} +/- {control_stdev:.2f} s')
    print(f'    Exp: {exp_mean:.2f} +/- {exp_stdev:.2f} s')

if __name__ == '__main__':
    main()
