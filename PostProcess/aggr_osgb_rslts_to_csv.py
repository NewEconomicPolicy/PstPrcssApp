# -------------------------------------------------------------------------------
# Name:         spec_post_process_csc.py
# Purpose:      post process spatial simulation results from SUMMARY.OUT files generated by the
#               Spatial Parallel ECosse Simulator
# Author:      Mike Martin
# Created:     25/01/2017
# Licence:     <your licence>
# Description: data is aggregated into CSV files
# -------------------------------------------------------------------------------
#
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

from aggregate_rslts_to_csv import fetch_fut_end_year
from spec_utilities import (load_manifest, display_headers, update_progress_post, deconstruct_sim_dir,
                                                                                retrieve_results, make_id_mod)
from spec_check import verify_subdir

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

def aggreg_osgb_metrics_to_csv(form, sims_dir=None):
    """
     called from GUI
     """
    if sims_dir is None:
        sims_dir = form.w_lbl_sims.text()

    # Create and initialise SpecCsv object
    # ====================================
    spec_csv = SpecCsvOsgb(form)
    if not spec_csv.smmry_out_flag:
        print(ERROR_STR + 'No SUMMARY.OUT files in: ' + sims_dir)
        return False

    if not spec_csv.create_results_files():
        return False

    display_headers(form)

    # get the climate scenario from the sims directory
    scenario = form.study_defn['climScnr']
    version = form.study_defn['version']

    print('Gathering all simulation directories from ' + sims_dir + '...')
    for directory, subdirs_raw, files in walk(sims_dir):
        break
    del directory
    del files

    # filter weather directories to leave only simulation directories
    # ===============================================================
    subdirs = []
    for subdir in subdirs_raw:      # typical OSGB subdir = '246500_642500'
        if verify_subdir(subdir):
            subdirs.append(subdir)
    num_sims = len(subdirs)
    del (subdirs_raw)

    print('Counting all manifest files...')
    num_manifests = len(glob(normpath(sims_dir + '/manifest_*.txt')))

    print('\nGathered {} simulation directories and {} manifest files...'.format(num_sims, num_manifests))

    # main loop
    # =========
    skipped = 0  # sims that were skipped due to error
    warning_count = 0  # No. of warnings
    start_time = time()
    nfailed = 0
    num_grid_cells = 0
    total_area = 0.0
    last_time = time()
    sim_num = 0         # No. of sims that have been processed

    # collect results, as a list, for a given cell for all of the dominant soils
    # ==========================================================================
    for sub_directory in subdirs:
        sim_dir = join(sims_dir, sub_directory)

        # write accumulated results to output file - reads the manifest file
        # ==================================================================
        # area = spec_csv.process_osgb_rslts(scenario, sim_dir_prev, results, expand_results=None)
        area = 1
        total_area += area
        num_grid_cells += 1

        # retrieve the data from summary.out
        # ==================================
        result_for_sim = retrieve_results(form.lgr, sim_dir)
        if result_for_sim is None:
            nfailed += 1
            if nfailed > MAX_FAILURES:
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

        # write accumulated results to output file - reads the manifest file
        # ==================================================================
        area = spec_csv.process_osgb_rslts(scenario, sim_dir, result_for_sim)
        total_area += area
        num_grid_cells += 1

        # =========================
        last_time = update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, nfailed, warning_count)
        sim_num += 1

     # close CSV files
    # ================
    for key in spec_csv.output_fhs:
        spec_csv.output_fhs[key].close()

    form.lgr.info('\nSimulations completed.')

    last_time = update_progress_post(last_time, start_time, num_grid_cells, num_manifests, skipped, nfailed, warning_count)

    mess = '\nAggregation of metrics from simulation results completed.'
    area_str = format_string("%12.2f", total_area, grouping=True)
    mess += '\t# failures: {}\tTotal area covered: {} km2'.format(nfailed, area_str)
    print(mess)
    form.lgr.info(mess)

    return True

class SpecCsvOsgb(object):
    """
    Class to write CSV results of a Spatial ECOSSE run
    """
    def __init__(self, form):

        self.lgr = form.lgr

        self.fut_start_year, self.fut_end_year, self.sims_dir, self.smmry_out_flag = fetch_fut_end_year(form)
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
        """
        Create empty results files
        The CSV format is the most common import and export format for spreadsheets and databases
        On Windows, if csvfile is a file object, it should be opened with newline=''.
        CSV is really a binary format, with "\r\n" separating records. If that separator is written in text mode, the
        Python runtime replaces the "\n" with "\r\n" hence, without the newline='' there will be blank lines.
        """
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

            self.writers[varname] = writer(self.output_fhs[varname], delimiter=',')
            self.writers[varname].writerow(hdr_rec)

        return True

    def process_osgb_rslts(self, scenario, sim_dir, results):
        """
        Process results accumulated for this grid cell
        Write to NC file
        Optionally delete simulation folder
        NB this function will only be called if there is useful data for this grid cell
        """
        mu_global = -999
        soil_id = 1
        id_ = deconstruct_sim_dir(sim_dir, scenario, self.land_use, mu_global, soil_id)
        lat_id, lon_id, mu_global, scenario, soil_id, lut = id_
        mu_global = -999

        # retrieve grid cell manifest file content
        # ========================================
        manifest = load_manifest(self.lgr, sim_dir)
        if manifest == None:    # trap error
            return 0.0

        province = manifest['location']['province']
        id_ = [province] + id_
        area_grid_cells = manifest['location']['area']

        # write final result to CSV file
        # =================================
        lat = manifest['location']['latitude']
        lon = manifest['location']['longitude']

        for varname in results.keys():
            nvals = len(results[varname])
            res = list(results[varname])

            format_str = self.var_format_strs[varname]
            res = [format_str.format(val) for val in res]
            if varname in self.writers:
                id_mod_ = make_id_mod(id_, lat, lon, area_grid_cells, int(lon_id))
                self.writers[varname].writerow(id_mod_ + res)

        return area_grid_cells
