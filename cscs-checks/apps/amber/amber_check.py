# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import reframe as rfm
import reframe.utility.sanity as sn
from hpctestlib.apps.amber.nve import Amber_NVE


# FIXME: Use tuples as dictionary keys as soon as
# https://github.com/eth-cscs/reframe/issues/2022 is in

REFERENCE_GPU_PERFORMANCE = {
    'normal':{
        ('daint:gpu', 'dom:gpu'): {
            'Cellulose_production_NVE': (30.0, -0.05, None, 'ns/day'),
            'FactorIX_production_NVE': (134.0, -0.05, None, 'ns/day'),
            'JAC_production_NVE': (388.0, -0.05, None, 'ns/day'),
            'JAC_production_NVE_4fs': (742, -0.05, None, 'ns/day'),
        },
    },
}

REFERENCE_CPU_PERFORMANCE_SMALL = {
    ('daint:mc', 'dom:mc'): {
        'Cellulose_production_NVE': (8.0, -0.30, None, 'ns/day'),
        'FactorIX_production_NVE': (34.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE': (90.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE_4fs': (150.0, -0.30, None, 'ns/day'),
    },
    ('eiger:mc', 'pilatus:mc'): {
        'Cellulose_production_NVE': (3.2, -0.30, None, 'ns/day'),
        'FactorIX_production_NVE': (7.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE': (30.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE_4fs': (45.0, -0.30, None, 'ns/day'),
    },
}

REFERENCE_CPU_PERFORMANCE_LARGE = {
    ('daint:mc'): {
        'Cellulose_production_NVE': (10.0, -0.30, None, 'ns/day'),
        'FactorIX_production_NVE': (36.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE': (78.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE_4fs': (135.0, -0.30, None, 'ns/day'),
    },
    ('eiger:mc'): {
        'Cellulose_production_NVE': (1.3, -0.30, None, 'ns/day'),
        'FactorIX_production_NVE': (3.5, -0.30, None, 'ns/day'),
        'JAC_production_NVE': (17.0, -0.30, None, 'ns/day'),
        'JAC_production_NVE_4fs': (30.5, -0.30, None, 'ns/day'),
    },
}

REFERENCE_CPU_PERFORMANCE = {
    'small': REFERENCE_CPU_PERFORMANCE_SMALL,
    'large': REFERENCE_CPU_PERFORMANCE_LARGE,
}

REFERENCE_PERFORMANCE = {
    'gpu': REFERENCE_GPU_PERFORMANCE,
    'cpu': REFERENCE_CPU_PERFORMANCE,
}

def inherit_cpu_only(params):
    return tuple(filter(lambda p: 'cpu' in p[0], params))


def inherit_gpu_only(params):
    return tuple(filter(lambda p: 'gpu' in p[0], params))


class AmberCheckCSCS(Amber_NVE):
    modules = ['Amber']
    valid_prog_environs = ['builtin']
    strict_check = True
    extra_resources = {
        'switches': {
            'num_switches': 1
        }
    }
    maintainers = ['VH', 'SO']

    @run_before('performance')
    def set_perf_reference(self):
        for key, val in REFERENCE_PERFORMANCE[self.platform][self.scale].items():
            if self.current_partition.fullname in key:
                self.reference = {'*': val}
                break
        else:
            raise ValueError(
                f'could not find a reference for the current '
                f'partition {self.current_partition.fullname!r}'
            )

@rfm.simple_test
class amber_gpu_check(AmberCheckCSCS):
    valid_systems = ['daint:gpu', 'dom:gpu']
    scale = 'normal'
    num_tasks = 1
    num_gpus_per_node = 1
    num_tasks_per_node = 1
    descr = f'Amber GPU check'
    tags.update({'maintenance', 'production', 'health'})
    platform_info = parameter(
        inherit_params=True,
        filter_params=inherit_gpu_only)


@rfm.simple_test
class amber_cpu_check(AmberCheckCSCS):
    tags.update({'maintenance', 'production'})
    scale = parameter(['small', 'large'])
    valid_systems = ['daint:mc', 'eiger:mc']
    platform_info = parameter(
        inherit_params=True,
        filter_params=inherit_cpu_only)

    @run_after('init')
    def set_description(self):
        self.mydescr = f'Amber parallel {self.scale} CPU check'

    @run_after('init')
    def set_additional_systems(self):
        if self.scale == 'small':
            self.valid_systems += ['dom:mc', 'pilatus:mc']

    @run_after('init')
    def set_hierarchical_prgenvs(self):
        if self.current_system.name in ['eiger', 'pilatus']:
            self.valid_prog_environs = ['cpeIntel']

    @run_after('init')
    def set_num_tasks_cray_xc(self):
        if self.current_system.name in ['daint', 'dom']:
            self.num_tasks_per_node = 36
            if self.scale == 'small':
                self.num_nodes = 6
            else:
                self.num_nodes = 16
            self.num_tasks = self.num_nodes * self.num_tasks_per_node

    @run_after('init')
    def set_num_tasks_cray_shasta(self):
        if self.current_system.name in ['eiger', 'pilatus']:
            self.num_tasks_per_node = 128
            if self.scale == 'small':
                self.num_nodes = 4
            else:
                # there are too many processors, the large jobs cannot start
                # need to decrease to just 8 nodes
                self.num_nodes = 8
            self.num_tasks = self.num_nodes * self.num_tasks_per_node
