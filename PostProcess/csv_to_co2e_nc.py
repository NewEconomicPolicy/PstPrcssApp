#-------------------------------------------------------------------------------
# Name:
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'csv_to_co2e_nc.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import split
from locale import format_string
from time import time
from netCDF4 import Dataset

from input_output_funcs import open_file_sets, read_one_line
from create_coards_nc_class import find_metric_in_flist_names
from create_co2e_nc_class import create_co2e_nc_dset, Co2e_nc_defn
from nc_low_level_fns import get_nc_coords, update_progress_bar

sleepTime = 5

GRANULARITY = 120

MAX_FIELDS_MONTHLY = 3600
MAX_LINES = 10000000000  # stop processing after this number of lines
METRICS = list(['ch4','n2o','co2','soc'])

CO2EQUIV_CH4 = 32      # from MA 24 April 2023, the latest IPCC report?
CO2EQUIV_N2O = 273
CO2_MOL_MASS_FACTOR = 44.01 / 12.01   # CO2-C --> CO2
CH4_MOL_MASS_FACTOR = 16.04 / 12.01   # CH4-C --> CH4
N2O_MOL_MASS_FACTOR = 44.013 / (14.007 * 2.0)  # CO2-C --> CO2
CO2_MOL_MASS_CONVERSION = 1     # MJM TODO:

ERROR_STR = '*** Error *** '

def _convert_to_co2e(num_months, metric_vals, daily_flag):
    """
    metric_vals: list of daily or monthly values
    assume:
        monthly values for now
    """
    monthly_vals = []
    for imnth in range(num_months):
        if imnth > 0:
            # When calculating the change in SOC add the methane-C back in so
            # we don't account for it twice
            #                   (metric_vals['co2'][imnth] * CO2_MOL_MASS_FACTOR)
            soc1 = metric_vals['soc'][imnth] + metric_vals['ch4'][imnth]
            soc2 = metric_vals['soc'][imnth - 1] + metric_vals['ch4'][imnth - 1]
            change_in_soc = soc1 - soc2
            # Apply Global Warming Potential factors and convert from C to molecular mass
            co2e = (CO2EQUIV_CH4 * metric_vals['ch4'][imnth] * CH4_MOL_MASS_FACTOR) \
                   + (CO2EQUIV_N2O * metric_vals['n2o'][imnth] * N2O_MOL_MASS_FACTOR)\
                   - (change_in_soc * CO2_MOL_MASS_FACTOR)
        else:
            co2e = 0.0  # Can't calculate net GHG because can't calculate change in SOC
        monthly_vals.append(co2e)

    #rescaled_vals = rescale_metric_values(num_months, monthly_vals, 'co2e', daily_flag)

    #return rescaled_vals
    return monthly_vals

def _generate_nc(form, metric_obj, daily_flag):
    """

    """
    nc_fname, var_name, num_months = create_co2e_nc_dset(form, metric_obj)
    if isinstance(nc_fname, int):
        return

    # open the newly created NC files
    # ===============================
    try:
        nc_dset = Dataset(nc_fname,'a', format='NETCDF4')
    except TypeError as err:
        err = 'Unable to open output file. {}'.format(err)
        print(err)
        return

    max_lat_indx = nc_dset.variables['latitude'].shape[0]  - 1
    max_lon_indx = nc_dset.variables['longitude'].shape[0] - 1

    # open crop file - TODO: only works for one file
    # ==============
    metric = metric_obj.metric
    trans_fobjs, header_rec = open_file_sets(metric_obj.rqrd_flist)

    # read and process each line
    # ==========================
    ntrans_lines  = form.trans_defn['nlines']
    ntrans_fields = form.trans_defn['nfields']
    nlines = 0
    num_out_lines = 0
    num_bad_lines = 0
    last_time = time()
    while (nlines <= MAX_LINES):

        # read in land use transition results
        # ===================================
        num_trans_time_vals, nsoil_metrics, line_prefix, atom_tran = read_one_line(trans_fobjs)
        if atom_tran == None:
            break
        nlines += 1

        # check data integrity
        # ====================
        if num_trans_time_vals != ntrans_fields:
            if num_bad_lines == 0:
                nline_str = format_string("%d", int(nlines), grouping=True)
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
            latitude  = float(slat)
            longitude = float(slon)

            lat_indx, lon_indx = get_nc_coords(form, latitude, longitude, max_lat_indx, max_lon_indx)
            if lat_indx == -1:
                continue

            if metric == 'soil':
                pass
            else:
                try:
                    nc_dset.variables['area'][lat_indx, lon_indx] = area

                    nc_dset.variables[var_name][:num_months, lat_indx, lon_indx] = _convert_to_co2e(num_months,
                                                                                            atom_tran, daily_flag)
                except (IndexError, ValueError, RuntimeError) as err:
                    mess = '\n' + ERROR_STR + '{}\nwriting {} values for metric {}'.format(err, num_months, metric)
                    mess += ' at lat/lon indices: {} {}'.format(lat_indx, lon_indx)
                    # form.lgr.critical(err)
                    print(mess)
                    return -1

            num_out_lines += 1

        last_time = update_progress_bar(last_time, ntrans_lines, num_out_lines, num_bad_lines)  # inform user of progress

    # close file objects
    # ==================
    for key in trans_fobjs:
        trans_fobjs[key].close()

    nc_dset.close()

    print('\nFinished - having written {} lines to NC file: {}\n'.format(nlines, nc_fname))

    return nlines

def csv_to_co2e_netcdf(form):
    """

    """
    mess = '*** Yearly data will be generated from '

    ntrans_fields = form.trans_defn['nfields']
    if ntrans_fields > MAX_FIELDS_MONTHLY:
        daily_flag = True
        time_step = 365
        mess += 'daily'
    else:
        daily_flag = False
        time_step = 12
        mess += 'monthly'

    print(mess + ' input ***')

    # gather required vars from UI
    # ============================
    aggreg_daily = form.w_aggreg.isChecked()
    out_dir = form.w_lbl_rslts.text()
    delete_flag = form.w_del_nc.isChecked()
    study = split(out_dir)[1]
    # study = form.study_defn['study']
    land_use = form.study_defn['land_use']
    file_list = form.trans_defn['file_list']

    # create list of required CSV files
    # =================================
    success_flag = True
    rqrd_flist = []
    for metric in METRICS:
        fname = find_metric_in_flist_names(file_list, metric)
        if fname is None:
            success_flag = False
            break
        else:
            rqrd_flist.append(fname)

    # create basic co2e object
    # ========================
    if success_flag:
        metric_obj = Co2e_nc_defn('co2e', rqrd_flist, land_use, out_dir, study, delete_flag)
        if metric_obj.fout_name is None:
            success_flag = False

    # construct NC file
    #==================
    if success_flag:
        nlines = _generate_nc(form, metric_obj, daily_flag)
        if nlines == 0:
            success_flag = False

    if success_flag:
        print('Generated {} annual net GHG fluxes NC file'.format(metric_obj.fout_name))
    else:
        print('No annual net GHG fluxes NC file generated')

    return