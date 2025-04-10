# utilities to support spec.py
#
__prog__ = 'spec_utilities.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import split, join, isfile, isdir
from os import rename, chdir, getcwd, walk, system, remove
from subprocess import check_output
from locale import format_string

import json
from time import time
import sys
import csv

from input_output_funcs import check_summary_out_row

ERROR_STR = '*** Error *** '
SUMMARY_VARNAMES = {
                 'soc': 'total_soc',
                 'ch4': 'ch4_c',
                 'co2': 'co2_c',
                 'no3': 'no3_n',
                 'npp': 'npp_adj',
                 'n2o': 'n2o_n'
                }
SUMMARY_VARNAMES = {
                 'soc': 'Total_SOC',
                 'ch4': 'CH4_C',
                 'co2': 'CO2_C',
                 'no3': 'NO3_N',
                 'n2o': 'N2O_N'
                }
HEAD_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\head.exe'
TAIL_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\tail.exe'
WC_EXE = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\wc.exe'

SMRY_OUT = 'SUMMARY.OUT'
SMRY_ORIG = 'SUMMARY_orig.OUT'

def update_progress_check(last_time, start_time,  nident, num_sims, not_ident):

    """Update progress bar"""
    this_time = time()
    if (this_time - last_time) > 5.0:
        remain_str = format_string("%d", num_sims - nident - not_ident, grouping=True)
        ident_str = format_string("%d", nident, grouping=True)
        not_ident_str = format_string("%d", not_ident, grouping=True)
        sys.stdout.flush()
        sys.stdout.write('\r                                                                                          ')
        sys.stdout.write('\rIdentical: {} Not Identical: {} Remaining: {}'
                                                        .format(ident_str, not_ident_str, remain_str))
        return this_time

    return last_time

def trim_summaries(form):
    """
    remake SUMMARY.OUT with later years of simulation e.g. 1980-2018
    """

    # TODO: cleanup
    # =============
    nsim_years = form.study_defn['futEndYr'] - form.study_defn['futStrtYr'] + 1
    nyears = int(form.w_nyears.text())
    timestep = 'Daily'
    # timestep = 'Monthly'
    if timestep == 'Daily':
        nsteps = nyears*365

    cmd_hdr = HEAD_EXE + ' -2 ' + SMRY_ORIG + ' > ' + SMRY_OUT
    cmd_tl = TAIL_EXE + ' -{} '.format(nsteps) + SMRY_ORIG + ' >> ' + SMRY_OUT

    curr_dir = getcwd()
    sims_dir = form.w_lbl_sims.text()

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
    ntrimmed = 0
    not_found = 0
    too_few_lines = 0
    nerrors = 0
    start_time = time()
    last_time = start_time

    for subdir in subdirs:

        this_dir = join(sims_dir, subdir)
        if isdir(this_dir):
            chdir(this_dir)
            last_time = update_progress_post(last_time, start_time, ntrimmed, num_sims, not_found, nerrors,
                                                                                                    too_few_lines)
            '''
            # might be useful to be able to restore SUMMARY.OUT
            if isfile(SMRY_ORIG) and not isfile(SMRY_OUT):
                rename(SMRY_ORIG, SMRY_OUT)
            '''
            remove_flag = True
            if remove_flag and isfile(SMRY_ORIG):
                remove(SMRY_ORIG)

            if isfile(SMRY_OUT) and not isfile(SMRY_ORIG):

                # check number of lines in file
                # =============================
                sbytes = check_output([WC_EXE, "-l", SMRY_OUT])
                nlines = int(sbytes.split()[0].decode())
                if nlines < nsteps:
                    too_few_lines += 1
                    continue

                rename(SMRY_OUT, SMRY_ORIG)

            if not isfile(SMRY_ORIG):
                not_found += 1
                continue

            ret_code = system(cmd_hdr)
            if ret_code != 0:
                nerrors += 1
                continue

            ret_code = system(cmd_tl)
            if ret_code == 0:
                ntrimmed += 1
            else:
                nerrors += 1

    chdir(curr_dir)
    print('\nNumber of summary files trimmed: {}\tnot found: {}\terrors: {}'.format(ntrimmed, not_found, nerrors))
    return True

class EcosseDialect(csv.excel):
    """Dialect class for reading in ECOSSE output files with the csv module."""
    delimiter = ' '
    skipinitialspace = True

def make_id_mod(id_, latitude, longitude, area_grid_cell, gran_lon):
    """
    latitude and longitude are taken from

    id_mod = list([id_[0], str(round(latitude,6))])
    longitude = (gran_lon/120) - 180.0
    id_mod.append(str(round(longitude,6)))
    """
    id_mod = list([id_[0], str(round(latitude, 6)), str(round(longitude,6))])
    id_mod = id_mod + id_[3:]
    id_mod.append(area_grid_cell)

    return id_mod

def deconstruct_sim_dir(sim_dir, scenario, land_use, mu_global=None, soil_id=None):
    """

    """
    directory = split(sim_dir)[1]
    parts = directory.split('_')

    # check for OSGB
    # ==============
    if directory.find('lat') == -1:
        lat_id = parts[0]
        lon_id = parts[1]

    else:
        lat_id = parts[0].strip('lat')
        lon_id = parts[1].strip('lon')
        mu_global = parts[2].strip('mu')
        mu_global = mu_global.lstrip('0')

        soil_id = parts[3].lstrip('s')
        soil_id = soil_id.lstrip('0')

    # Get rid of leading zeros
    # =========================
    lat_id = str(int(lat_id))
    lon_id = str(int(lon_id))
    lut = land_use   # from study definition file

    return [lat_id, lon_id, mu_global, scenario, soil_id, lut]

def retrieve_soil_results_ss(sim_dir):
    """
    TODO: rewrite
    """

    # split directory name to retrieve the mu global
    # =============================================
    mu = int(sim_dir.split('_mu')[1].split('_s')[0])

    input_txt = join(sim_dir, sim_dir, str(mu) + '.txt')
    if not isfile(input_txt):
        return -1

    result_for_soil = {'s_C_content': [], 's_bulk_dens': [],  's_pH': [], 's_clay': [], 's_silt': [],'s_sand': []}
    metric_lookup = {'C_content':'s_C_content', 'Bulk_dens':'s_bulk_dens', '%_clay':'s_clay', 'pH':'s_pH',
                                                                    '%_sand':'s_sand', '%_silt':'s_silt'}

    with open(input_txt, 'r') as fobj:
        mu_detail = json.load(fobj)

    for key in mu_detail:
        if key.find('soil_lyr') == 0:
            for metric in mu_detail[key]:
                map_metric = metric_lookup[metric]
                val = mu_detail[key][metric]
                result_for_soil[map_metric].append(val)

    return result_for_soil

def retrieve_soil_results(sim_dir, failed):

    func_name =  __prog__ + ' retrieve_soil_results'

    """
    for limited data mode only
    read soil parameters and plant input from the mu global file for example: 6093.txt
    """
    #
    soil_properties = list(['s_C_content','s_bulk_dens','s_pH','s_clay','s_silt','s_sand'])

    input_txt = join(sim_dir,'input.txt')
    if not isfile(input_txt):
        return -1

    with open(input_txt, 'r') as fobj:
        lines = fobj.readlines()

    nlayers = int(lines[1].split()[0])
    if nlayers < 1 or nlayers > 2:
        print('Check ' + sim_dir + ' - number of layers must be 1 or 2' )
        return -1

    nline = 2 + nlayers
    soil_parms = {}
    for property in soil_properties:
        soil_parms[property] = list([])

    for ilayer in range(nlayers):
        for property in soil_properties:
            line = lines[nline]
            soil_parms[property].append(float(line.split()[0]))
            nline += 1

    # look for plant input
    # ====================
    for nline, line in enumerate(lines):
        str_ngrow, descrip = line.split('#')
        if descrip.find('Number of growing seasons') >= 0:
            ngrow = int(str_ngrow)
            break

    # step through each land use and plant input (PI) pair until we find a non-zero PI
    # ================================================================================
    nline += 1
    for iyear, line in enumerate(lines[nline:nline + ngrow]):
        lu_yield, dummy = line.split('#')
        lu, pi = lu_yield.split(',')
        plant_input = float(pi)
        if plant_input > 0.0:
            break

    return soil_parms, iyear, plant_input

def _make_mapping_dict(columns):
    """
    return dictionary to map required SUMMARY.OUT metrics
    this func overcomes failure when processing legacy ECOSSE SUMMARY.OUT files, namely version 6_2c or earlier
    sv_name = short variable name; lv_name = long
    """
    nrequired = len(SUMMARY_VARNAMES)
    smmry_vars_dict = {}
    smmry_vars_lgcy_dict = {}
    for sv_name, lv_name in SUMMARY_VARNAMES.items():
        if lv_name in columns:
            smmry_vars_dict[sv_name] = lv_name
        elif lv_name.lower() in columns:
            smmry_vars_lgcy_dict[sv_name] = lv_name.lower()

    if len(smmry_vars_dict) == nrequired:
        return smmry_vars_dict
    elif len(smmry_vars_lgcy_dict) == nrequired:
        return smmry_vars_lgcy_dict
    else:
        return None

    return

def retrieve_results(lggr, sim_dir):
    """
    extract necessary results from the completed simulation's output file
    """
    path = join(sim_dir, 'SUMMARY.OUT')
    if not isfile(path):
        print(ERROR_STR + 'No SUMMARY.OUT file in: ' + split(path)[0])
        return None

    summary = {}
    with open(path, 'r') as fobj:
        reader = csv.reader(fobj, dialect = EcosseDialect)
        try:
            next(reader)  # Skip the units description line
        except StopIteration as err:
            print('\nCheck: ' + path + ' is empty')
            return None
        try:
            columns = next(reader)
        except StopIteration as err:
            print('\nCheck: ' + path + ' is empty')
            return None

        # identify Ecosse version
        # =======================
        smmry_vars_dict = _make_mapping_dict(columns)
        if smmry_vars_dict is None:
            print('SUMMARY.OUT file: ' + path + ' not recognised')
            return None
        
        for column in columns:
            summary[column] = []
        for irow, row in enumerate(reader):
            row = check_summary_out_row (row)
            for icol, val_str in enumerate(row):
                try:
                    val = float(val_str)
                except ValueError as err:
                    icol_nxt = icol + 1
                    if icol_nxt < len(columns):
                        metric_str = '\tmetrics: ' + columns[icol] + ' ' + columns[icol_nxt]
                    else:
                        metric_str = '\tmetric: ' + columns[icol]

                    lggr.info(ERROR_STR + 'on row ' + str(irow + 3) + ' ' + str(err) + metric_str + '\n\tin: ' + path)
                    return None

                summary[columns[icol]].append(val)

    # build result
    # ============
    full_result = {}
    for sv_name, lv_name in smmry_vars_dict.items():
        full_result[sv_name] = list(summary[lv_name])    # sv_name = short variable name; lv_name = long

    if len(full_result) == 0:
        full_result = None

    return full_result

def load_manifest(lgr, sim_dir):
    """
    construct the name of the manifest file and read it
    last 4 characters of lat/lon simulations directory indicates soil, so ignore
    """
    root_dir, cell_id = split(sim_dir)

    # identify if lat/lon or OSGB
    # ===========================
    if cell_id.find('lat') >= 0:
        cell_id = cell_id[0:-4]

    manifest_fn = join(root_dir,'manifest_' + cell_id + '.txt')
    if isfile(manifest_fn):
        lgr.info('manifest file ' + manifest_fn + ' exists')
        try:
            with open(manifest_fn, 'r') as fmani:
                manifest = json.load(fmani)
        except (OSError, IOError) as err:
            print(str(err))
            manifest = None
    else:
        print('manifest file ' + manifest_fn + ' does not exist')
        manifest = None

    return manifest

def update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, failed, warning_count):

    """Update progress bar."""
    '''
    if time() - last_time > 1.0:
        sec_elapsed = time() - start_time
        h, m, s = mut.s2hms(sec_elapsed)
        pc_complete = max(completed / est_num_sims, 0.0000001)
        t_left = sec_elapsed / pc_complete - sec_elapsed
        h2, m2, s2 = mut.s2hms(t_left)
        sys.stdout.flush()
        sys.stdout.write('\rComplete: {0} Skip: {1} Warn: {2} Taken: {3:0>2}'
                         ':{4:0>2}:{5:0>2} Left: {6:0>3}:{7:0>2}:{8:0>2}'
                         .format(completed, skipped, warning_count,
                         h, m, int(round(s)), h2, m2, int(round(s2))))
    '''
    this_time = time()
    if (this_time - last_time) > 5.0:
        remain_str = format_string("%d", num_manifests - num_grid_cells, grouping=True)
        cmplt_str = format_string("%d", num_grid_cells, grouping=True)
        sys.stdout.flush()
        sys.stdout.write('\r                                                                                          ')
        sys.stdout.write('\rComplete: {} Skip: {} Warnings: {} Remaining: {}'
                                                        .format(cmplt_str, skipped, warning_count, remain_str))
        return this_time

    return last_time

def _within_times(dt, starthour, startminute, endhour, endminute):
    """Deterines if the time is within the specified boundaries.
    dt    - [datetime object] the time to be checked
    """
    within = False
    if dt.hour > starthour and dt.hour < endhour:
        within = True
    elif dt.hour == starthour:
        if dt.minute >= startminute:
            within = True
    elif dt.hour == endhour and dt.minute <= endminute:
        within = True
    return within

def _seconds2hms(seconds):
    """
    Converts a time period in seconds to hours, minutes and seconds.
    """
    hours = int(seconds / 3600)
    seconds -= hours * 3600
    mins = int(seconds / 60)
    secs = seconds % 60
    return hours, mins, secs

def display_headers(form):
    """Writes a header to the screen and logfile."""
    print('')
    print('spec {}'.format(__version__))
    print('')
    print('   ####   ###      #   #  ###  #####      ### #      ###   #### #####   # #')
    print('   #   # #   #     ##  # #   #   #       #    #     #   # #     #       # #')
    print('   #   # #   #     # # # #   #   #      #     #     #   #  ###  #####   # #')
    print('   #   # #   #     #  ## #   #   #       #    #     #   #     # #')
    print('   ####   ###      #   #  ###    #        ### #####  ###  ####  #####   # #')
    print('')
    form.lgr.info('Starting simulations')