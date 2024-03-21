#-------------------------------------------------------------------------------
# Name:
# Purpose:     read and write functions for processing ECOSSE results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
#
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'input_output_funcs.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from glob import glob
import json
from os import stat, mkdir, makedirs, remove, chdir, getcwd
from os.path import join, isdir, isfile, split, splitext
from zipfile import ZIP_STORED, ZipFile, ZIP_DEFLATED

from PyQt5.QtWidgets import QApplication

from locale import setlocale, LC_ALL, format_string
from subprocess import Popen, STDOUT

sleepTime = 2
ERROR_STR = '*** Error *** '

# make sure you have the variable names in the same order as the conversion factors
# result names (same in both folders), must match order of other lists (assume they have .txt suffix)

ALL_METRICS = ['soc', 'co2', 'ch4', 'no3', 'npp', 'n2o']
nfiles = len(ALL_METRICS)

CUT_EXE_PATH = 'E:\\Freeware\\UnxUtils\\usr\\local\\wbin\\cut.exe'
data_rec_prefix_len = 8
maxFieldsMonthly = 3600     # TODO: if number of fields exceeeds this then assume timestep is daily
setlocale(LC_ALL, '')

SMRY_ROW_LEN = 29

def clean_and_zip(form, dir_list, stage_dir, mgmt_flag):
    """

    """
    for dirn in dir_list:
        if mgmt_flag:
            flist = glob(dirn + '\\Reg*')
        else:
            flist = glob(dirn + '\\*.txt')

        # skip unwanted files
        # ===================
        flist_zipping = []
        for fn in flist:
            long_fn, exten = splitext(fn)
            if exten == '.nc' or exten == '.txt' :
                metric = long_fn.split('_')[-1]
                if metric == 'npp':
                    continue
                elif mgmt_flag:
                    if metric == 'ch4':
                        continue
                else:
                    flist_zipping.append(fn)

        print('Will zip {} files from {}'.format(len(flist_zipping), dirn))

        # construct zipfile name for this simulation
        # ==========================================
        if mgmt_flag:
            out_zip_fn = join(stage_dir, split(dirn)[1] + '.zip')
        else:
            out_zip_fn = join(stage_dir, split(split(dirn)[0])[1] + '.zip')

        if isfile(out_zip_fn):
            try:
                remove(out_zip_fn)
            except PermissionError as err:
                print(err)
                continue

        zip_obj = ZipFile(out_zip_fn, mode="w")

        for fn in flist_zipping:
            short_name = split(fn)[1]
            zip_obj.write(fn, short_name, compress_type=ZIP_DEFLATED)

        zip_obj.close()
        print('Zipped {} files to {}'.format(len(flist_zipping), out_zip_fn))

    print('Zipping completed')
    return

def chng_study_create_co2e(form, eu28_dir):
    """
    change study and create co2e NC file
    """
    form.w_lbl_sims.setText(eu28_dir)
    QApplication.processEvents()    # allow event loop to update unprocessed events
    change_create_rslts_dir(form)
    QApplication.processEvents()

    return

def aggregate_csv_create_coards(form, mgmt_dir):
    """
    aggregate to CSV files, then optionally clip resultant CSVs and write Coards compliant NetCDF files
    """
    form.w_lbl_sims.setText(mgmt_dir)
    QApplication.processEvents()    # allow event loop to update unprocessed events
    change_create_rslts_dir(form)

    form.aggregToCsvClicked()
    cut_csv_files(form)
    form.writeCoardsNcClicked()

    return

def check_summary_out_row(row, smry_row_len = 29):
    """
    switch w_cut_csv push button off or on
    """

    row_out = []
    if len(row) == smry_row_len:
        return row
    else:
        for icol, val_str in enumerate(row):
            try:
                val = float(val_str)
            except ValueError as err:
                result = val_str.split('-')
                if len(result) == 2:
                    val_str1, val_str2 = result
                    row_out.append(val_str1)
                    row_out.append('-' + val_str2)
                else:
                    row_out.append(val_str)
            else:
                row_out.append(val_str)

        return row_out

def check_cut_csv_files(form):
    """
    switch w_cut_csv push button off or on
    """
    if len(form.trans_defn['file_list']) > 0 and form.trans_defn['nfields'] == 3600:
        form.w_cut_csv.setEnabled(True)
    else:
        form.w_cut_csv.setEnabled(False)

def cut_csv_files(form, cut_str = '-f1-8,2397-3608'):
    """
    retrieve CSV results files to be converted from 300 to 101 years i.e. to run from Jan 2001 to 2100
                                                or 300 to 141 years i.e. to run from Jan 1961 to 2100
    """
    rslts_dir = form.w_lbl_rslts.text()

    out_dir = join(rslts_dir, 'cut_outdir')
    if not isdir(out_dir):
        mkdir(out_dir)

    """
    form.trans_defn is a list of files created in function ecosse_results_files which is 
    called whenever the results directory changes
    """
    for fname in form.trans_defn['file_list']:

        dum, fn_short = split(fname)
        fn_out = join(out_dir, fn_short)
        print('Creating new file: ' + fn_out)
        cmd_str = CUT_EXE_PATH + ' ' + cut_str + ' ' + fname

        with open(fn_out, 'wb') as out_fobj, open('stderr.txt', 'wb') as err_fobj:
            Popen(cmd_str, stdout = out_fobj, stderr = err_fobj)

    return out_dir

def change_create_rslts_dir(form):
    """
    change and, if reqested, create a results directory for this study
    """
    sims_dir = form.w_lbl_sims.text()

    dummy, study = split(sims_dir)
    rslts_dir = sims_dir.replace('EcosseSims', 'EcosseOutputs')
    if not isdir(rslts_dir):
        if form.w_create_outdir.isChecked():
            try:
                makedirs(rslts_dir)
                print('Created results directory: ' + rslts_dir)
            except PermissionError as err:
                print('Could not create ' + rslts_dir)
                return
        else:
            return

    form.w_lbl_rslts.setText(rslts_dir)
    descriptor, form.trans_defn = ecosse_results_files(rslts_dir, 'Contents: ')
    form.w_lbl06.setText(descriptor)

    return

def ecosse_simulations_files(sims_dir):

    wthr_list = glob(sims_dir + '\\[0-9]*')
    sims_list = glob(sims_dir + '\\lat*')
    if len(wthr_list) == 0:
        clim_fnames = []
    else:
        clim_fnames = glob(wthr_list[0] + '\\met*')

    nsims_str = format_string("%d", len(sims_list), grouping=True)
    nwthr_str = format_string("%d", len(wthr_list), grouping=True)
    nclim_str = format_string("%d", len(clim_fnames), grouping=True)

    description = 'Found {} simulations\t{} weather sets\t{} met files per weather set'\
                                            .format(nsims_str, nwthr_str, nclim_str)
    """
    for wthr_dir in wthr_list:
        clim_fnames = glob(wthr_dir + '\\met*')
    sims_list = glob(sims_dir + '\\lat*')
    for sim_dir in sims_list:
        manage_fn = join(sim_dir, 'management.txt')
        if isfile(manage_fn):
            with open(manage_fn, 'r') as fobj:
                lines = fobj.readlines()
                nyears = lines[9]
    """
    return description

def _check_study_defn(study_defn_fn, study_defn, land_use):
    """
    validate study definition file contents
    """

    crop_name =  'cropName'
    required_keys = list(['bbox', 'climScnr', crop_name, 'resolution', 'futEndYr', 'futStrtYr', 'land_use', 'study'])

    for key in required_keys:
        if key in study_defn:
            val = study_defn[key]
            if key == 'futEndYr' or key == 'futStrtYr':
                study_defn[key] = int(val)
            elif key == 'land_use':
                # TODO: make more robust
                # ======================
                if val == 'unk2unk':
                    study_defn[key] = 'ara'
                    if crop_name in study_defn:
                        if study_defn[crop_name] == 'Grassland':
                            study_defn[key] = 'gra'

            elif key == 'resolution':
                if val == '' or val is None:
                    study_defn[key] = 0.0
                    print(ERROR_STR + ' invalid resolution: {} in study definition: {}'.format(str(val), study_defn_fn))
                    return None
                else:
                    try:
                        study_defn[key] = float(val)
                    except TypeError as err:
                        print(str(err) + ' invalid resolution: {} in study definition: {}'.format(str(val), study_defn_fn))
                        return None
        else:
            if key == crop_name:
                print(crop_name + ' not in study definition - will use ' + land_use)
                study_defn[crop_name] = land_use
            else:
                print(key + ' not in study definition - please check ' + study_defn_fn)
                return None

    return study_defn

def read_study_definition(form, study_defn_fn = None):
    """

    """
    func_name = __prog__ + ' read_study_definition'

    # identify the study definition file
    # ==================================
    if study_defn_fn is None:
        rslts_dir = form.w_lbl_rslts.text()
        outputs_dir, study = split(rslts_dir)
        base_dir, dummy = split(outputs_dir)
        sims_dir = join(base_dir, 'EcosseSims')
        study_defn_fn = join(sims_dir, study + '_study_definition.txt')

    if not isfile(study_defn_fn):
        study_defn_flag = False

        # try reforming study
        # ===================
        study_list = study.split('_')
        if len(study_list) >= 4:
            study = '_'.join(study_list[-2:])
            study_defn_fn = join(sims_dir, study + '_study_definition.txt')
            if isfile(study_defn_fn):
                study_defn_flag = True

        if not study_defn_flag:
            print('Study definition file ' + study_defn_fn + ' does not exist')
            return False

    # read
    # ====
    land_use = 'unknown'
    try:
        with open(study_defn_fn, 'r') as fstudy:
            study_defn_raw = json.load(fstudy)

    except (OSError, IOError) as err:
        print(err)
        return False

    grp = 'studyDefn'
    study_defn = _check_study_defn(study_defn_fn, study_defn_raw[grp], land_use)
    if study_defn is None:
        return False

    form.study_defn = study_defn

    return True

def open_file_sets(trans_files, crop_name = 'dummy', remove_flag = True):
    """
    for each file read first line for header and return open file handles
    """
    key_list = []
    trans_fobjs = {}
    soil_header = None
    for file_name in trans_files:
        rootname, extens = splitext(file_name)
        indx_strt = rootname.rfind('_') + 1
        # TODO
        if crop_name == 'dummy':
            key = rootname[indx_strt:]
        else:
            key = crop_name
        key_list.append(key)
        trans_fobjs[key] = open(file_name, 'r')
        rec = trans_fobjs[key].readline()
        if key == 'soil' or key == 'soc':
            soil_header = rec.split()

    return trans_fobjs, soil_header

def ecosse_results_files(dir_name, descriptor_prefix):
    """
    TODO: use spaces rather than tabs
    """
    timestep = 'Not set'
    ret_dict = {'file_list': [], 'nfields': 0, 'nlines': 0}
    
    # identify files for processing
    # =============================
    file_list = []; nfields = 0; nyears = 0; missing_metrics = []
    descriptor = ''
    for metric in ALL_METRICS:
        files = glob(dir_name + '/*' + metric + '.txt')
        if len(files) > 0:
            file_list.append(files[0])
            descriptor = descriptor + metric + ', '

            # open file and ascertain period
            # ==============================
            if metric == 'soil':
                continue
            fobj = open(files[0], 'r')
            dummy = fobj.readline()
            first_rec = fobj.readline()
            fobj.close()
            nfields = len(first_rec.split()) - data_rec_prefix_len
            if nfields > maxFieldsMonthly:
                nyears = int((nfields)/365)
                timestep = 'Daily'
            else:
                nyears = int((nfields)/12)
                timestep = 'Monthly'
        else:
            missing_metrics.append(metric)

    descriptor = '   ' + descriptor_prefix + descriptor.rstrip(', ')

    # convert to file size to kilobytes
    # =================================
    if len(file_list) == 0:
         mess = 'No ' + str(ALL_METRICS).strip('[]').replace("'","") + ' CSV files for processing'
         print(mess + ' in ' + dir_name)
         return mess, ret_dict

    fname = file_list[0]
    fname_info = stat(fname)
    fsize_kb = format_string("%d", fname_info.st_size/1024, grouping=True)
    descriptor += '   file size: {} Kb   years: {}'.format(str(fsize_kb),str(nyears))

    # TODO: find faster method
    with open(fname, 'r') as fobj:
        nlines = len(fobj.readlines())

    for fname in file_list:
            nlines_str = format_string("%d", nlines, grouping=True)
            descriptor += '   # lines: {}   years: {}'.format(nlines_str, nyears)
            break

    descriptor += '   timestep: ' + timestep
    ret_dict['file_list'] = file_list
    ret_dict['nfields']   = nfields
    ret_dict['nlines']    = nlines

    return descriptor, ret_dict

def read_one_line(file_objs):
    """
    read in one line of data from via each file object and return three data elements:
      - number of data points
      - line prefix list:  province, latitude, longitude, mu_global, climate_scenario, num_dom_soils, land_use, area_km2
      - a dictionary of values whose keys are typically the metrics: ch4, co2, n2o, soc
                                and whose objects comprise a list of monthly values for the corresponding metric
    """

    # defaults for end of file
    num_time_vals = -1
    nsoil_metrics = -1
    line_prefix  = []

    # read one line of data from each file
    # ====================================
    vals = {}
    for key in file_objs.keys():
        rec = file_objs[key].readline()

        # check for end of file
        # =====================
        if rec == '':
            vals = None
            break

        data_rec = rec.split()
        line_prefix = data_rec[0:data_rec_prefix_len]
        num_vals = len(data_rec) - data_rec_prefix_len
        vals[key] = []
        for k in range(num_vals):
            vals[key].append(float(data_rec[k + data_rec_prefix_len]))  # first 8 cols are province, east, north, etc

        if key == 'soil':
            nsoil_metrics = num_vals
        else:
            num_time_vals = num_vals    # number of time values e.g. monthly

    return num_time_vals, nsoil_metrics, line_prefix, vals
