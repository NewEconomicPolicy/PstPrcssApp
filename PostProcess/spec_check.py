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
from locale import format_string
from netCDF4 import Dataset
from sys import stdout

from spec_utilities import update_progress_check
from input_output_funcs import open_file_sets, read_one_line
from nc_low_level_fns import get_nc_coords

ERROR_STR = '*** Error *** '

HEAD_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\head.exe'
TAIL_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\tail.exe'
WC_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\wc.exe'

SMRY_OUT = 'SUMMARY.OUT'

SV_DIR = 'G:\\GlblEcssOutputs\\EcosseOutputs'

ASIA_WHT = 'Asia_Wheat_Asia_Wheat'
WARNING_STR = '*** Warning *** '
sleepTime = 5.0

def csv_to_csv_ireland(form):
    """
    C
    """
    nc_fname = 'G:\\HoliSoils\\GlblEcssVcSpTest\\EcosseOutputs\\EFISCENSE_BAU_0.1_26_ELUM\\'
    nc_fname += 'EFISCENSE_BAU_0.1_26_ELUM_co2e.nc'
    bbox = list([-10.6, 50.8, -5.6, 55.0])

    try:
        nc_dset = Dataset(nc_fname, 'a')
    except TypeError as err:
        print(ERROR_STR + 'Unable to open output file. {}'.format(err))
        return

    # max_lines = int(form.w_nlines.text())
    max_lines = 9999999                                        # stop processing after this number of lines
    max_lat_indx = nc_dset.variables['latitude'].shape[0] - 1
    max_lon_indx = nc_dset.variables['longitude'].shape[0] - 1

    trans_files = form.trans_defn['file_list']     # Files comprising the LU transition result
    if len(trans_files) == 0:
        print('No transition files to process')
        return

    # open all files
    # ==============
    trans_fobjs, soil_header = open_file_sets(trans_files)

    # read and process each line
    # ==========================
    ll_lon, ll_lat, ur_lon, ur_lat = bbox
    max_lines = 99999999
    nline = 0
    num_out_lines = 0
    num_skip_lines = 0
    num_bad_lines = 0
    last_time = time()
    lat_lons = []
    while nline <= max_lines:

        # read in land use transition results
        # ===================================
        num_trans_time_vals, nsoil_metrics, line_prefix, atom_tran = read_one_line(trans_fobjs)
        if atom_tran is None:
            break
        nline += 1

        # check data integrity
        # ====================
        if num_trans_time_vals != form.trans_defn['nfields']:

            # write to file....
            # writers[bad_fobj_key].writerow(line_prefix)

            if num_bad_lines == 0:
                nline_str = format_string("%d", int(nline), grouping=True)
                print('\nBad data at line {}\tfound {} trans fields, expected {} - will skip'
                                                .format(nline_str, num_trans_time_vals, form.trans_defn['nfields']))
            num_bad_lines += 1
        else:
            # write final result to NetCDF file
            # =================================
            total_area = 0.0
            province, slat, slon, smu_global, wthr_set, num_soil, dummy, sarea = line_prefix
            area = float(sarea)
            total_area += area
            mu_global = int(smu_global)
            lat = float(slat)
            lon = float(slon)

            if (lat >= ll_lat and lat <= ur_lat) and (lon >= ll_lon and lon <= ur_lon):
                pass
            else:
                num_skip_lines += 1
                continue

            '''
            lat_indx, lon_indx = get_nc_coords(form, lat, lon, max_lat_indx, max_lon_indx)
            if lat_indx == -1:
                continue
            '''
            for varname in atom_tran.keys():
                if varname != 'soc':
                    continue
                '''
                if atom_tran[varname] is None or varname not in nc_dset.variables:
                    continue
                '''
                lat_lons.append([lat,lon])
                num_out_lines += 1

                nvals = len(atom_tran[varname])
                nyears = nvals // 12
                if nvals % 12 != 0 and nline == 1:
                    print(WARNING_STR + 'Number of months {} should be divisable by 12'.format(nvals))

                    atom_rec = atom_tran[varname]

        # inform user with progress message
        # =================================
        new_time = time()
        if new_time - last_time > sleepTime:
            last_time = new_time
            num_out_str = format_string("%d", int(num_out_lines), grouping=True)
            nremain = format_string("%d", form.trans_defn['nlines'] - num_out_lines, grouping=True)
            stdout.write('\rLines output: {}\trejected: {}\tremaining: {}'
                                    .format(num_out_str, num_bad_lines, nremain))

    # close file objects
    # ==================
    for key in trans_fobjs:
        trans_fobjs[key].close()

    nc_dset.close()

    print('\nDone - having processed ' + format_string("%d", int(nline), grouping=True) + ' lines')

    return

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

    elif nsegs == 2 and version == 'NetZeroPlus':    # OSGB typically  73500_870500 but could be weather
        for sval in subdir_segs:
            try:
                ival = int(sval)
            except ValueError as err:
                verify_flag = False
                break
            else:
                verify_flag = True

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
