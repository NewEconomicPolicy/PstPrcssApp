#-------------------------------------------------------------------------------
# Name:
# Purpose:     perform SuperG operations
# Author:      Mike Martin
# Created:     4 Oct 2022
# Description:
#-------------------------------------------------------------------------------
#
__author__ = 's03mm5'
__prog__ = 'cdo_superg_ops.py'
__version__ = '0.0'

from argparse import ArgumentParser
from os import getcwd, chdir, system, mkdir, remove, name as os_name
from os.path import abspath, expanduser, expandvars, isfile, isdir, join, normpath, split
from sys import exit, stdout
from time import sleep, time
from glob import glob

sleepTime = 5
PROGRAM_ID = 'cdo_superg_ops'
ERROR_STR = '*** Error *** '

EU28 = 'EU28'
CO2E = 'co2e.nc'
DIFF = 'diff'

RCPS_FLAG = True
RCPS = ['45', '85']

RUNS_FLAG = True
RUNS = ['', 'grz_mnr', 'nsyn_grz', 'nsyn_mnr']

UNIX_UTILS_DIR = {'posix':'/usr/bin', 'nt':'E:\\Freeware\\UnxUtils\\usr\\local\\wbin'}

CLEAN_FLAG = True

class Form(object):
    """
    CDO operations in batch mode
    """
    def __init__(self):
        """

        """
        if os_name == 'posix':
            cdo_exe = join(UNIX_UTILS_DIR[os_name], 'cdo')
            if not isfile(cdo_exe):
                print(ERROR_STR + cdo_exe + ' does not exist, cannot continue')
                sleep(sleepTime)
                exit(1)

            superg_dir = '/mnt/e/SuperG_MA/co2e_results_2022_10_03'
        else:
            cdo_exe = 'cdo_exe'
            superg_dir = 'E:\\SuperG_MA\\co2e_results_2022_10_03'

        results_dir = join(superg_dir, 'results')
        if not isdir(results_dir):
            mkdir(results_dir)

        self.superg_dir = superg_dir
        self.results_dir = results_dir
        self.touch_exe = join(UNIX_UTILS_DIR[os_name], 'touch.exe')
        self.cdo_exe = cdo_exe

    def prepare_ops(self):
        """

        """
        superg_dir = self.superg_dir
        chdir(superg_dir)
        rslts_rel_dir = './' + split(self.results_dir)[1]
        if CLEAN_FLAG:
            fn_list = glob(rslts_rel_dir + '/*')
            for fn in fn_list:
                remove(fn)
            print('Removed {} files from {}'.format(len(fn_list), rslts_rel_dir))

        self.rslts_rel_dir = rslts_rel_dir

    def subtract_runs(self):
        """
         
        """
        rslts_rel_dir = self.rslts_rel_dir

        for rcp in RCPS:
            prefix = '_'.join([EU28, rcp, '10'])
            rcp_nc = '_'.join([prefix, CO2E])
            for run in RUNS[1:]:
                run_nc = '_'.join([prefix, run, CO2E])
                out_nc = normpath(join(rslts_rel_dir, '_'.join([prefix, run, DIFF, CO2E])))

                print('\nrcp_nc: {}\trun_nc: {}'.format(isfile(rcp_nc), isfile(run_nc)))

                cmd_str = self.cdo_exe + ' sub ' + rcp_nc + ' ' + run_nc + ' ' + out_nc
                if os_name == 'posix':
                    system(cmd_str)
                else:
                    print('cmd_str runs: ' + cmd_str)
                    cmd_str = self.touch_exe  + ' ' + out_nc
                    system(cmd_str)

        print('\n************')
        return True

    def subtract_rcps(self):
        """

        """
        rslts_rel_dir = self.rslts_rel_dir

        prefix_45 = '_'.join([EU28, RCPS[0], '10'])
        prefix_85 = '_'.join([EU28, RCPS[1], '10'])
        prefix_out = '_'.join([EU28, RCPS[0], RCPS[1], '10'])

        for run in RUNS:

            if run == '':
                nc_45 = '_'.join([prefix_45, CO2E])
                nc_85 = '_'.join([prefix_85, CO2E])
                nc_out = '_'.join([prefix_out, DIFF, CO2E])
            else:
                nc_45 = '_'.join([prefix_45, run, CO2E])
                nc_85 = '_'.join([prefix_85, run, CO2E])
                nc_out = '_'.join([prefix_out, run, DIFF, CO2E])

            out_nc = normpath(join(rslts_rel_dir, nc_out))

            print('\nnc_45: {}\tnc_85: {}'.format(isfile(nc_45), isfile(nc_85)))

            cmd_str = self.cdo_exe + ' sub ' + nc_45 + ' ' + nc_85 + ' ' + out_nc
            if os_name == 'posix':
                system(cmd_str)
            else:
                print('cmd_str rcps: ' + cmd_str)
                cmd_str = self.touch_exe + ' ' + out_nc
                system(cmd_str)

        return True

def main():
    """
    Entry point
    """
    argparser = ArgumentParser( prog = __prog__, description = 'perform SuperG CDO operations')

    argparser.add_argument('--version', action = 'version', version = '{} {}'.format(__prog__, __version__),
                                                                        help = 'Display the version number.')
    args = argparser.parse_args()

    prfrm_ops = Form()
    curr_dir = getcwd()

    prfrm_ops.prepare_ops()

    if RUNS_FLAG:
        prfrm_ops.subtract_runs()

    if RCPS_FLAG:
        prfrm_ops.subtract_rcps()

    chdir(curr_dir)
    exit(0)

if __name__ == '__main__':
    main()
