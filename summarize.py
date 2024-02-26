#!/usr/bin/env python

import json
import sys
from collections import defaultdict


if __name__ == '__main__':
    output = json.load(open(sys.argv[1]))
    exp = output['experiment']
    print(json.dumps(exp, indent=True))
    times = defaultdict(list)
    for run in output['runs']:
        times[run['arm']].append(run['elapsed_time_secs'])

    print('\t'.join([exp['ref_control'], exp['ref_exp']]))
    for run in zip(times['control'], times['exp']):
        print('\t'.join(format(s, '.4f') for s in run))

    stats = output['stats']
    control_mean = stats['control']['mean']
    control_stdev = stats['control']['stdev']
    exp_mean = stats['exp']['mean']
    exp_stdev = stats['exp']['stdev']
    pct = 100.0 * (exp_mean - control_mean) / control_mean
    print(f'Control: {control_mean:.2f} +/- {control_stdev:.2f} s')
    print(f'    Exp: {exp_mean:.2f} +/- {exp_stdev:.2f} s = {pct:+.2f}%')
