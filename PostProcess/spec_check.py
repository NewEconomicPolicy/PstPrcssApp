# check results
#
__prog__ = 'spec_utilities.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import split, join, isfile, isdir
from os import rename, chdir, getcwd, walk, system, remove
from time import time
from glob import glob
import filecmp

from spec_utilities import update_progress_check

ERROR_STR = '*** Error *** '

HEAD_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\head.exe'
TAIL_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\tail.exe'
WC_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\wc.exe'

SMRY_OUT = 'SUMMARY.OUT'

SV_DIR = 'G:\\GlblEcssOutputs\\EcosseOutputs'

ASIA_WHT = 'Asia_Wheat_Asia_Wheat'

def verify_subdir(subdir, version=None):
    """
    validate subdirectory as Global Ecosse
    """
    verify_flag = False
    subdir_segs = subdir.split('_')
    nsegs = len(subdir_segs)
    if nsegs == 4:      # lats/lons typically  lat0002374_lon0024154_mu10090_s01
        if subdir[0:5] == 'lat00':
            verify_flag = True
    '''
    elif nsegs == 2 and version == 'NetZeroPlus':    # OSGB typically  73500_870500
        for sval in subdir_segs:
            try:
                ival = int(sval)
            except ValueError as err:
                verify_flag = False
                break
            else:
                verify_flag = True
    '''
    return verify_flag

def check_asia_results(form):
    """
    check CSV outputs  across multiple simulations
    """
    sim_dirs = {}
    base_lines = {}
    for scenario in ['A1B', 'A2']:
        sim_dirs[scenario] = glob(SV_DIR + '\\' + ASIA_WHT + '0*' + scenario)
        base_lines[scenario] = join(sim_dirs[scenario][0], 'cut_outdir', ASIA_WHT + '00' + scenario + '_soc.txt')

        print('\nBaseline: ' + split(base_lines[scenario])[1])
        for ic, sim_dir in enumerate(sim_dirs[scenario][1:]):
            targ_file = join(sim_dir, 'cut_outdir', ASIA_WHT + '0' + str(ic + 1) + scenario + '_soc.txt')
            res = filecmp.cmp(base_lines[scenario], targ_file)
            print('\t{} {}'.format(res, split(targ_file)[1]))

    return True

def check_spec_results(form):
    """
    check SUMMARY.OUTs across two simulations
    """

    # compare
    # =======
    sims_dir = form.w_lbl_sims.text()
    sims_targ_dir = join(split(sims_dir)[0], 'EU28_45_10_grz_mnr')

    print('Gathering all simulation directories from ' + sims_dir + '...')
    for directory, subdirs_raw, files in walk(sims_dir):
        break
    del directory
    del files

    # filter weather directories to leave only simulation directories
    # ===============================================================
    subdirs = []
    for subdir in subdirs_raw:
        if subdir[0:5] == 'lat00':
            subdirs.append(subdir)
    num_sims = len(subdirs)
    del (subdirs_raw)

    # counters: Number of summary files trimmed or not found
    # ======================================================
    nfound = 0
    nident = 0
    not_ident = 0
    not_found = 0
    start_time = time()
    last_time = start_time

    for subdir in subdirs:

        ref_dir = join(sims_dir, subdir)
        targ_dir = join(sims_targ_dir, subdir)
        if isdir(ref_dir and targ_dir):

            ref_file = join(ref_dir, SMRY_OUT)
            targ_file = join(targ_dir, SMRY_OUT)
            if isfile(ref_file) and isfile(targ_file):
                nfound += 1
                if filecmp.cmp(ref_file, targ_file):
                    nident += 1
                else:
                    not_ident += 1
            else:
                not_found += 1

        last_time = update_progress_check(last_time, start_time, nident, num_sims, not_ident)

    print('\nNumber of summary files found: {}\tnot found: {}'.format(nfound, not_found))
    return True
