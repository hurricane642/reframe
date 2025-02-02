# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import reframe as rfm
import reframe.utility.sanity as sn
from hpctestlib.apps.quantumespresso.base_check import QuantumESPRESSO


REFERENCE_CPU_PERFORMANCE_SMALL = {
    'dom:mc': {
        'maint': (115.0, None, 0.05, 's'),
        'prod': (115.0, None, 0.05, 's')
    },
    'daint:mc': {
        'maint': (115.0, None, 0.10, 's'),
        'prod': (115.0, None, 0.10, 's')
    },
    'eiger:mc': {
        'maint': (66.0, None, 0.10, 's'),
        'prod': (66.0, None, 0.10, 's')
    },
    'pilatus:mc': {
        'maint': (66.0, None, 0.10, 's'),
        'prod': (66.0, None, 0.10, 's')
    },
}

REFERENCE_CPU_PERFORMANCE_LARGE = {
    'daint:mc': {
        'maint': (115.0, None, 0.10, 's'),
        'prod': (115.0, None, 0.10, 's')
    },
    'eiger:mc': {
        'maint': (53.0, None, 0.10, 's'),
        'prod': (53.0, None, 0.10, 's')
    },
    'pilatus:mc': {
        'maint': (53.0, None, 0.10, 's'),
        'prod': (53.0, None, 0.10, 's')
    },
}

REFERENCE_GPU_PERFORMANCE_SMALL = {
    'dom:mc': {
        'maint': (61.0, None, 0.05, 's'),
        'prod': (61.0, None, 0.05, 's')
    },
    'daint:mc': {
        'maint': (61.0, None, 0.05, 's'),
        'prod': (61.0, None, 0.05, 's')
    }
}

REFERENCE_GPU_PERFORMANCE_LARGE = {
    'daint:mc': {
        'maint': (54.0, None, 0.05, 's'),
        'prod': (54.0, None, 0.05, 's')
    }
}

REFERENCE_PERFORMANCE = {
    'gpu': {
        'small': REFERENCE_GPU_PERFORMANCE_SMALL,
        'large': REFERENCE_GPU_PERFORMANCE_LARGE,
    },
    'cpu': {
        'small': REFERENCE_CPU_PERFORMANCE_SMALL,
        'large': REFERENCE_CPU_PERFORMANCE_LARGE,
    },
}

REFERENCE_ENERGY = {
    'gpu': {
        'small': (-11427.09017168, 1E-07),
        'large': (-11427.09017179, 1E-07),
    },
    'cpu': {
        'small': (-11427.09017168, 1E-06),
        'large': (-11427.09017152, 1E-06),
    },
}


@rfm.simple_test
class quantum_espresso_check_cscs(QuantumESPRESSO):
    scale = parameter(['small', 'large'])
    mode = parameter(['maint', 'prod'])
    platform = parameter(['gpu', 'cpu'])
    modules = ['QuantumESPRESSO']
    maintainers = ['LM']
    tags = {'scs'}
    strict_check = False
    extra_resources = {
        'switches': {
            'num_switches': 1
        }
    }

    @run_after('init')
    def set_valid_systems(self):
        if self.platform == 'cpu':
            self.valid_systems = ['daint:mc', 'eiger:mc', 'pilatus:mc']
        else:
            self.valid_systems = ['daint:gpu']

    @run_after('init')
    def env_define(self):
        if self.current_system.name in ['eiger', 'pilatus']:
            self.valid_prog_environs = ['cpeIntel']
        else:
            self.valid_prog_environs = ['builtin']

    @run_after('init')
    def set_tags(self):
        self.tags |= {
            'maintenance' if self.mode == 'maint' else 'production'
        }

    @run_after('init')
    def set_num_tasks(self):
        if self.platform == 'cpu':
            if self.scale == 'small':
                self.valid_systems += ['dom:mc']
                if self.current_system.name in ['daint', 'dom']:
                    self.num_tasks = 216
                    self.num_tasks_per_node = 36
                elif self.current_system.name in ['eiger', 'pilatus']:
                    self.num_tasks = 96
                    self.num_tasks_per_node = 16
                    self.num_cpus_per_task = 16
                    self.num_tasks_per_core = 1
                    self.variables = {
                        'MPICH_OFI_STARTUP_CONNECT': '1',
                        'OMP_NUM_THREADS': '8',
                        'OMP_PLACES': 'cores',
                        'OMP_PROC_BIND': 'close'
                    }
            else:
                if self.current_system.name in ['daint']:
                    self.num_tasks = 576
                    self.num_tasks_per_node = 36
                elif self.current_system.name in ['eiger', 'pilatus']:
                    self.num_tasks = 256
                    self.num_tasks_per_node = 16
                    self.num_cpus_per_task = 16
                    self.num_tasks_per_core = 1
                    self.variables = {
                        'MPICH_OFI_STARTUP_CONNECT': '1',
                        'OMP_NUM_THREADS': '8',
                        'OMP_PLACES': 'cores',
                        'OMP_PROC_BIND': 'close'
                    }
        else:
            self.num_gpus_per_node = 1
            self.num_tasks_per_node = 1
            self.num_cpus_per_task = 12
            if self.scale == 'small':
                self.valid_systems += ['dom:gpu']
                self.num_tasks = 6
            else:
                self.num_tasks = 16

    @run_after('init')
    def set_description(self):
        self.descr = (f'QuantumESPRESSO {self.platform}'
                      f'check (version: {self.scale}, {self.mode})')

    @run_after('init')
    def set_reference(self):
        self.reference = REFERENCE_PERFORMANCE[self.platform][self.scale]
        self.energy_value = REFERENCE_ENERGY[self.platform][self.scale][0]
        self.energy_tolerance = REFERENCE_ENERGY[self.platform][self.scale][1]

    @run_before('run')
    def set_task_distribution(self):
        if self.platform == 'cpu':
            self.job.options = ['--distribution=block:block']

    @run_before('run')
    def set_cpu_binding(self):
        if self.platform == 'cpu':
            self.job.launcher.options = ['--cpu-bind=cores']
