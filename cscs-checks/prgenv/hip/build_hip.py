# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import reframe as rfm
import reframe.utility.sanity as sn


@rfm.simple_test
class BuildHip(rfm.RegressionTest):
    '''Download and install HIP around the nvcc compiler.'''

    # HIP build variables
    hip_path = variable(str, value='hip')
    hip_full_path = variable(str)
    hip_platform = variable(str, value='nvcc')

    valid_systems = ['daint:gpu', 'dom:gpu']
    valid_prog_environs = ['PrgEnv-gnu']
    sourcesdir = 'https://github.com/ROCm-Developer-Tools/HIP.git'
    build_system = 'CMake'
    postbuild_cmds = ['make install']
    executable = f'{hip_path}/bin/hipcc'
    executable_opts = ['--version']
    maintainers = ['JO']
    tags = {'production'}

    @rfm.run_before('compile')
    def set_compile_options(self):
        self.hip_full_path = os.path.abspath(
            os.path.join(self.stagedir, self.hip_path)
        )
        self.build_system.builddir = 'build'
        self.build_system.config_opts = [
            f'-DCMAKE_INSTALL_PREFIX={self.hip_full_path}',
            f'-DHIP_PLATFORM={self.hip_platform}',
        ]

    @rfm.run_before('sanity')
    def set_sanity_patterns(self):
        self.sanity_patterns = sn.assert_found(r'nvcc:\s+NVIDIA', self.stdout)


@rfm.simple_test
class HelloHip(rfm.RegressionTest):
    '''A Hello World test for HIP.'''

    sample = variable(str, value='HelloWorld')
    sample_dir = variable(str, value='HIP-Examples-Applications')

    valid_systems = ['daint:gpu', 'dom:gpu']
    valid_prog_environs = ['PrgEnv-gnu']
    modules = ['cdt-cuda']
    sourcesdir = 'https://github.com/ROCm-Developer-Tools/HIP-Examples.git'
    build_system = 'Make'
    maintainers = ['JO']
    tags = {'production'}

    def __init__(self):
        self.depends_on('BuildHip')

    @rfm.require_deps
    def get_hip_path(self, BuildHip):
        self.hip_path = BuildHip().hip_full_path

    @rfm.run_before('compile')
    def set_env(self):
        self.variables = {'HIP_PATH': f'{self.hip_path}'}
        self.build_system.cxx = os.path.join(self.hip_path, 'bin', 'hipcc')
        self.prebuild_cmds = [f'cd {self.sample_dir}/{self.sample}']

    @rfm.run_before('run')
    def set_executable(self):
        self.executable = f'{self.sample_dir}/{self.sample}/{self.sample}'

    @rfm.run_before('sanity')
    def set_sanity(self):
        self.sanity_patterns = sn.assert_found(r'HelloWorld', self.stdout)
