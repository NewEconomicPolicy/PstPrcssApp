"""
#-------------------------------------------------------------------------------
# Name:         spec_post_process_csc.py
# Purpose:      post process spatial simulation results from SUMMARY.OUT files generated by the
#               Spatial Parallel ECosse Simulator
# Author:      Mike Martin
# Created:     25/01/2017
# Licence:     <your licence>
# Description: data is aggregated into CSV files
#-------------------------------------------------------------------------------
"""

__prog__ = 'aggregate_rslts_to_csv.py'
__version__ = '1.0.1'

# Version history
# ---------------
# 1.0.1

from glob import glob
from csv import field_size_limit, writer
from os.path import normpath, isfile, join, split, isdir
from os import walk, remove
from copy import copy
from time import time
from locale import format_string

from spec_utilities import load_manifest, display_headers, update_progress_post, deconstruct_sim_dir, \
                                    retrieve_soil_results, retrieve_soil_results_ss, retrieve_results, make_id_mod

ERROR_STR = '*** Error *** '

EXTRA_METRICS = ['no3', 'npp']
SUMMARY_VARNAMES = {'soc': 'total_soc', 'co2': 'co2_c', 'ch4': 'ch4_c', 'no3': 'no3_n', 'npp': 'npp_adj',
                                                                                                        'n2o': 'n2o_n'}
VAR_FORMAT_STRS = {'soc': '{0:.1f}', 'co2': '{0:.3f}', 'ch4': '{0:.5f}', 'no3': '{0:.6f}', 'npp': '{0:.1f}',
                                                                                                    'n2o': '{0:.6f}'}

MAX_NUM_DOM_SOILS = 9  # HWSD has up to 9 dominant soils
COMMON_HEADERS = ['province', 'latitude', 'longitude', 'mu_global', 'climate_scenario', 'num_dom_soils', 'land_use',
                                                                                                            'area_km2']
MAX_FAILURES = 1000

def aggreg_metrics_to_csv(form, sims_dir = None, expand_results = False):
    '''
    called from GUI
    '''
    if sims_dir is None:
        sims_dir = form.w_lbl_sims.text()

    # Create and initialise SpecCsv object
    # ====================================
    spec_csv = SpecCsv(form)
    if not spec_csv.smmry_out_flag:
        print(ERROR_STR + 'No SUMMARY.OUT files in: ' + sims_dir)
        return False

    if not spec_csv.create_results_files():
        return False

    display_headers(form)
    num_grid_cells = 0  # No. of grid cells have completed successfully
    failed = 0   # sims that failed to complete due to error
    skipped = 0  # sims that were skipped due to error
    warning_count = 0   # No. of warnings
    start_time = time()

    # get the climate scenario from the sims directory
    scenario = form.study_defn['climScnr']

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
    del(subdirs_raw)

    print('Counting all manifest files...')
    num_manifests = len(glob(normpath(sims_dir + '/manifest_lat*_lon*_mu*.txt')))

    print('\nGathered {} simulation directories and counted {} manifest files...'.format(num_sims,num_manifests))

    # main loop
    # =========
    total_area = 0.0
    last_time = time()
    sim_num = 0         # No. of sims that have been processed

    # collect results, as a list, for a given cell for all of the dominant soils
    # ==========================================================================
    results = [{} for x in range(MAX_NUM_DOM_SOILS + 1)]
    results[0] = 0  # counts number of valid results
    sim_dir_prev = ''
    for sub_directory in subdirs:
        sim_dir = join(sims_dir, sub_directory)
        sdom_soil = sim_dir[-2:]
        try:
            ndom_soil = int(sdom_soil)
        except ValueError as err:
            print('\nCould not extract dominant soil number from simulation path ' + sim_dir)
            continue

        # when we hit first dominant soil then write accumulated results
        # ==============================================================
        if sim_dir[-4:] == '_s01':
            if results[0] > 0:
                # write accumulated results to output file - reads the manifest file
                # ==================================================================
                area = spec_csv.process_results(scenario, sim_dir_prev, results, expand_results)
                total_area += area
                num_grid_cells += 1

            # initialise results list with ten disctionary elements, the first as a counter then one for each dominant soil
            # =============================================================================================================
            results = [{} for x in range(MAX_NUM_DOM_SOILS + 1)]
            results[0] = 0  # counts number of valid results

        # retrieve the data from summary.out
        # ==================================
        result_for_sim = retrieve_results(form.lgr, sim_dir)
        if result_for_sim is None:
            failed += 1
            if failed > MAX_FAILURES:
                print('\n*** Abandoned processesing *** Exceeded maximum number of failures {}'.format(MAX_FAILURES))
                break
            else:
                continue

        # filter unwanted metrics
        # =======================
        for metric in EXTRA_METRICS:
            if not form.w_metrics[metric].isChecked():
                if metric in result_for_sim:
                    del(result_for_sim[metric])

        # =========================
        if ndom_soil < MAX_NUM_DOM_SOILS:
            results[ndom_soil] = result_for_sim
            results[0] += 1
        else:
            print('\nCannot process dominant soil number {} for {}'.format(ndom_soil, sim_dir))

        sim_dir_prev = sim_dir

        last_time = update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, failed, warning_count)
        sim_num += 1

    # make sure last cell is written
    if results[0] > 0:
        # process and write accumulated results to output file
        area = spec_csv.process_results(scenario, sim_dir_prev, results, expand_results)
        total_area += area
        num_grid_cells += 1

    # close CSV file
    # ==============
    for key in spec_csv.output_fhs:
        spec_csv.output_fhs[key].close()

    form.lgr.info('\nSimulations completed.')

    last_time = update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, failed, warning_count)

    mess = '\nAggregation of metrics from simulation results completed.'
    area_str = format_string("%12.2f", total_area, grouping=True)
    mess += '\t# failures: {}\tTotal area covered: {} km2'.format(failed, area_str)
    print(mess)
    form.lgr.info(mess)

    return True

def map_sims_weather(form):
    '''
    create tab sepaaretedCSV file of weather folders for a simulation
    '''
    sims_dir = form.sims_dir
    sim_dir, study = split(sims_dir)
    fname = join(sim_dir, study + '_weather_map.txt')
    if isfile(fname):
        remove(fname)
        print('deleted ' + fname)

    try:
        fobj = open(fname, 'w', newline='')
    except (OSError, IOError) as err:
        err = 'Unable to open output file. {0}'.format(err)
        return None

    # construct a list of all weather directories
    # ===========================================
    weather_dirs = glob(sims_dir + '\\[0-9]*_*')
    wthr_dirs = []
    for d in weather_dirs:
        dummy, dirname = split(d)
        wthr_dirs.append(dirname)

    # construct sorted lists of all lats and longs
    #  ===========================================
    lat_list = []
    lon_list = []
    for d in wthr_dirs:
        lat, lon = d.split('_')
        if lat not in lat_list:
            lat_list.append(lat)
        if lon not in lon_list:
            lon_list.append(lon)

    lon_list = sorted(lon_list)
    lat_list = sorted(lat_list)

    nwthr = len(wthr_dirs)
    nlats = len(lat_list)
    nlons = len(lon_list)
    print('Number of weather dirs {}\t latitudes {}\t longitudes {}'.format(nwthr,nlats,nlons))

    # build and populate output grid
    # ==============================
    grid_cells = {}
    for lat in lat_list:
        grid_cells[lat] = {}
        for lon in lon_list:
            grid_cells[lat][lon] = '0'

    for d in wthr_dirs:
        lat, lon = d.split('_')
        grid_cells[lat][lon] = '1'

    # output CSV file
    # ===============
    line = ''
    for lon in lon_list:
        line += lon + '\t'
    line += '\n'
    fobj.write(line)

    for lat in lat_list:
        line = lat + '\t'
        for lon in lon_list:
            line += grid_cells[lat][lon] + '\t'
        line += '\n'
        fobj.write(line)

    fobj.close()
    print('Wrote {} lines to {}'.format(nlats + 1,fname))

    return fname

def _deduce_fut_end_year(form):
    '''

    '''
    sims_dir = form.w_lbl_sims.text()
    fut_end_year = form.study_defn['futEndYr']
    fut_start_year = form.study_defn['futStrtYr']
    '''
    if form.study_defn['futStrtYr'] == 1901:
        fut_start_year = 1801
        print('Adjusted future start year from 1901 to ' + str(fut_start_year) + ' to correct header')
    else:
        fut_start_year = form.study_defn['futStrtYr']
    '''

    print('Gathering simulation directories from ' + sims_dir + '...')
    for directory, subdirs_raw, files in walk(sims_dir):
        break
    del files

    # filter weather directories to leave only simulation directories
    # ===============================================================
    smmry_out_flag = False
    for subdir in subdirs_raw:
        if subdir[0:5] == 'lat00':
            smmry_out_fn = join(sims_dir, subdir, 'SUMMARY.OUT')
            if isfile(smmry_out_fn):
                smmry_out_flag = True
                with open(smmry_out_fn, 'r') as fobj:
                    nlines = len(fobj.readlines())

                    # deduce check timestep
                    # =====================
                    if (nlines -2) % 12 == 0:
                        fut_start_year = int(fut_end_year - (nlines - 2) / 12 + 1)
                        timestep = 'monthly'
                    elif (nlines -2) % 365 == 0:
                        fut_start_year = int(fut_end_year - (nlines - 2) / 365 + 1)
                        timestep = 'daily'
                    else:
                        fut_start_year = form.study_defn['futStrtYr']
                        timestep = 'undetermined'

                    print('Simulation timestep is deduced to be: {}\twith start and end years: {} {}'
                                                                .format(timestep, fut_start_year, fut_end_year))
                    break

    return fut_start_year, fut_end_year, sims_dir, smmry_out_flag

class SpecCsv(object):
    '''
    Class to write CSV results of a Spatial ECOSSE run
    '''
    def __init__(self, form):

        self.lgr = form.lgr

        self.fut_start_year, self.fut_end_year, self.sims_dir, self.smmry_out_flag = _deduce_fut_end_year(form)


        self.output_dir = form.w_lbl_rslts.text()

        self.land_use = form.study_defn['land_use']

        from copy import copy
        smry_varnames = copy(SUMMARY_VARNAMES)
        var_format_strs = copy(VAR_FORMAT_STRS)

        varnames = []
        for metric in EXTRA_METRICS:
            if not form.w_metrics[metric].isChecked():
                del(smry_varnames[metric])
                del(var_format_strs[metric])

        self.varnames = list(var_format_strs.keys())
        self.summary_varnames = smry_varnames
        self.var_format_strs = var_format_strs

    def create_results_files(self):
        '''
        Create empty results files
        The CSV format is the most common import and export format for spreadsheets and databases
        On Windows, if csvfile is a file object, it should be opened with newline=''.
        CSV is really a binary format, with "\r\n" separating records. If that separator is written in text mode, the
        Python runtime replaces the "\n" with "\r\n" hence, without the newline='' there will be blank lines.
        '''
        size_current = field_size_limit(131072*4)

        self.output_fhs = {}
        self.writers = {}
        hdr_rec = copy(COMMON_HEADERS)
        for year in range(self.fut_start_year, self.fut_end_year + 1):
            for month in range(1, 13):
                hdr_rec.append('{0}-{1:0>2}'.format(str(year), str(month)))

        for varname in self.varnames:
            sim_dir, study = split(self.sims_dir)
            fname = study + '_{0}.txt'.format(varname)
            try:
                self.output_fhs[varname] = open(join(self.output_dir,fname), 'w', newline='')
            except (PermissionError, OSError, IOError) as err:
                err_mess = 'Unable to open output file. {}'.format(err)
                self.lgr.critical(err_mess)
                print(err_mess)
                return False

            self.writers[varname] = writer(self.output_fhs[varname], delimiter='\t')
            self.writers[varname].writerow(hdr_rec)

        return True

    def create_soil_results_file(self, run_mode):

        # Create empty soil results files
        # ===============================
        self.output_fhs = {}
        self.writers = {}
        hdr_rec = COMMON_HEADERS + list(['s_C_content', 's_bulk_dens', 's_pH', 's_clay', 's_silt', 's_sand'])

        if run_mode == 'ltd_data':
            hdr_rec += list(['iyear','yield'])

        sim_dir, study = split(self.sims_dir)
        varname = 'soil'
        fname = study + '_' + varname + '.txt'
        try:
            self.output_fhs[varname] = open(join(self.output_dir, fname), 'w', newline='')
        except (OSError, IOError) as err:
            mess = 'Unable to open output file. {0}'.format(err)
            self.lgr.critical(mess)

        self.writers[varname] = writer(self.output_fhs[varname], delimiter='\t')
        self.writers[varname].writerow(hdr_rec)

    def process_soil_result(self, scenario, sim_dir, result, iyear, plant_input, run_mode):
        """
        write first layer of soil TODO: what about second layer?
        """
        id_ = deconstruct_sim_dir(sim_dir, scenario, self.land_use)
        lat_id, lon_id, mu_global, scenario, soil_id, lut = id_
        # retrieve manifest
        manifest = load_manifest(self.lgr, sim_dir)
        if manifest is None:    # trap error
            return 0.0

        # retrieve percentages and convert to ordered factors
        province = manifest['location']['province']
        id_ = [province] + id_
        percentages = manifest[mu_global.lstrip('0')]
        area_grid_cells = manifest['location']['area']
        latitude = manifest['location']['latitude']

        id_mod_ = make_id_mod(id_, latitude, area_grid_cells, int(lon_id))
        record = id_mod_
        for key in result.keys():
            record.append(result[key][0])

        if run_mode == 'ltd_data':
            record.append(iyear)
            record.append(plant_input)

        self.writers['soil'].writerow(record)

        return area_grid_cells

    def process_results(self, scenario, sim_dir, results, expand_results):
        """
        Process results accumulated for this grid cell
        Write to NC file
        Optionally delete simulation folder
        NB this function will only be called if there is useful data for this grid cell
        """
        id_ = deconstruct_sim_dir(sim_dir, scenario, self.land_use)
        lat_id, lon_id, mu_global, scenario, soil_id, lut = id_

        # retrieve grid cell manifest file content
        # ========================================
        manifest = load_manifest(self.lgr, sim_dir)
        if manifest == None:    # trap error
            return 0.0

        # retrieve percentages and convert to ordered factors
        province = manifest['location']['province']
        id_ = [province] + id_
        percentages = manifest[mu_global.lstrip('0')]
        area_grid_cells = manifest['location']['area']

        # reconstruct set of cells for this simulation
        granular_longs = manifest['granular_longs']
        nlen = len(granular_longs)
        area_grid_cell = str(round(area_grid_cells/(1 +nlen),6))
        granular_longs[str(nlen+1)] = int(lon_id)

        factors = {}
        multiplier = 1.0
        # valuable_data_flag = False
        for el in percentages.items():
            factors[el[0]] = el[1]/100.0
            # check corresponding entry in results list
            indx = int(el[0])
            if results[indx] == None:
                multiplier += el[1]/100.0

        ndom_soils = results[0]
        npercs = len(percentages)
        if npercs != ndom_soils:
            self.lgr.info('Number of percentages {} from the manifest file does not equal number of dominant soils {}'.
                  format(npercs,ndom_soils))

        # apply factors and sum - NB order of dominant soils is important
        # ===============================================================
        final_result = {}
        ndsp1 = ndom_soils+1
        for result, el in zip(results[1:ndsp1], sorted(factors.items())):
            if result == None:
                continue

            factor =  el[1]
            for varname in result.keys():
                if final_result.get(varname) == None:
                    final_result[varname] = [el*factor for el in result[varname]]
                else:
                    first = final_result[varname]
                    second = [el*factor for el in result[varname]]
                    final_result[varname] = [x + y for x, y in zip(first, second)]

        # write final result to CSV file
        # =================================
        latitude = manifest['location']['latitude']
        longitude = manifest['location']['longitude']
        for varname in final_result.keys():
            nvals = len(final_result[varname])

            # adjust for missing soils
            if multiplier > 1.0:
                final_result[varname] = [el*multiplier for el in final_result[varname]]

            res = list(final_result[varname])
            format_str = self.var_format_strs[varname]
            res = [format_str.format(val) for val in res]
            if varname in self.writers:
                if expand_results:
                    for gran_lon in granular_longs.values():
                        id_mod_ = make_id_mod(id_, latitude, longitude, area_grid_cell, gran_lon)
                        self.writers[varname].writerow(id_mod_ + res)
                else:
                    id_mod_ = make_id_mod(id_, latitude, longitude, area_grid_cells, int(lon_id))
                    self.writers[varname].writerow(id_mod_ + res)

        return area_grid_cells

def aggregate_soil_data_to_csv(form):

    '''
    assumes single soil for grid cell
    '''
    func_name = __prog__ + ' aggregate_soil_data_to_csv'
    display_headers(form)
    completed_max = 99999999999

    # get the climate scenario from the sims directory
    # ================================================
    scenario = form.study_defn['climScnr']
    if 'cropName' in form.study_defn:
        if form.study_defn['cropName'] == 'unknown':
            run_mode = 'ltd_data'
        else:
            run_mode = 'site_spec'
    else:
        run_mode = 'ltd_data'

    # Create and initialise SpecCsv object
    # ====================================
    spec_csv = SpecCsv(form)
    spec_csv.create_soil_results_file(run_mode)
    sims_dir = form.w_lbl_sims.text()

    num_grid_cells = 0  # No. of grid cells have completed successfully
    failed = 0   # sims that failed to complete due to error
    skipped = 0  # sims that were skipped due to error
    warning_count = 0   # No. of warnings
    start_time = time()

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
    del(subdirs_raw)

    print('Counting all manifest files...')
    num_manifests = len(glob(normpath(sims_dir + '/manifest_lat*_lon*_mu*.txt')))

    print('\nGathered {} simulation directories and counted {} manifest files...'.format(num_sims,num_manifests))

    # main loop
    # =========
    iyear = None
    plant_input = None
    total_area = 0.0
    last_time = time()
    sim_num = 0         # No. of sims that have been processed

    # collect results - ignore all but the dominant soils
    # ===================================================
    for sub_directory in subdirs:
        sim_dir = join(sims_dir, sub_directory)

        if sim_dir[-4:] != '_s01':
            continue

        # write accumulated results to output file - reads the manifest file
        # ==================================================================
        if run_mode == 'ltd_data':
            result_for_soil, iyear, plant_input = retrieve_soil_results(sim_dir, failed)
        else:
            result_for_soil = retrieve_soil_results_ss(sim_dir)

        area = spec_csv.process_soil_result(scenario, sim_dir, result_for_soil, iyear, plant_input, run_mode)

        total_area += area
        num_grid_cells += 1

        last_time = update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, failed, warning_count)
        sim_num += 1
        if sim_num > completed_max:
            print('\nCompleted maximum number of simulations {} - will terminate processing'.format(sim_num))
            break

    # close CSV file
    # ==============
    for key in spec_csv.output_fhs:
        spec_csv.output_fhs[key].close()

    form.lgr.info('\nSimulations completed.')

    last_time = update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, failed, warning_count)
    mess = '\nAggregation of soil data completed.\tTotal area covered: {} km2'.format(round(total_area,2))
    print(mess)
    form.lgr.info(mess)