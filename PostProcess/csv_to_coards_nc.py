#-------------------------------------------------------------------------------
# Name:
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2020
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'csv_to_coards_nc.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

import os
from locale import format_string
from time import time
from netCDF4 import Dataset
from statistics import mean
from calendar import monthrange
from sys import stdout

from input_output_funcs import open_file_sets, read_one_line
from create_coards_nc_class import create_coards_nc_dset, Coard_nc_defn, find_metric_in_flist_names
from nc_low_level_fns import get_nc_coords

sleepTime = 5

MAX_FIELDS_MONTHLY = 3600
HECTARES_PER_M2 = 0.0001     # a hectare is 10,000 metres
NC_METRICS = list(['ch4', 'co2', 'no3', 'n2o', 'soc', 'npp'])
MAX_LINES = 10000000000  # stop processing after this number of lines

def rescale_metric_values(num_months, metric_vals, metric, daily_flag):
    '''
    metric_vals: list of daily or monthly values
    assume:
        first value is 1st Jan and each year is 365 days (ECOSSE norm)
        convert from hectares to square metre and from per second to per year
    '''
    monthly_vals = []
    imnth = 1
    if daily_flag:
        indx1 = 0
        for indx_mnth in range(num_months):
            frst_day, num_days = monthrange(2011, imnth)
            indx2 = indx1 + num_days
            if metric == 'soc':
                monthly_vals.append(HECTARES_PER_M2 * mean(metric_vals[indx1:indx2]))
            else:
                # get mean of daily values then scale up to a yearly value for that month
                # =======================================================================
                monthly_vals.append(HECTARES_PER_M2 * 365 * mean(metric_vals[indx1:indx2]))   # flux
            indx1 += num_days
            imnth += 1
            if imnth > 12:
                imnth = 1
    else:
        imnth = 1
        for indx_mnth in range(num_months):
            frst_day, num_days = monthrange(2011, imnth)
            if metric == 'soc':
                monthly_vals.append(HECTARES_PER_M2 * metric_vals[indx_mnth])
            elif metric == 'npp':
                monthly_vals.append(HECTARES_PER_M2 * metric_vals[indx_mnth] / 2)      # NB divide by 2
            else:
                monthly_vals.append(HECTARES_PER_M2 * 365 * metric_vals[indx_mnth] / num_days)
            imnth += 1
            if imnth > 12:
                imnth = 1

    return monthly_vals

def _generate_nc(form, metric_obj, daily_flag):
    """

    """
    nc_fname, var_name, num_months = create_coards_nc_dset(form, metric_obj)
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
    trans_fobjs, header_rec = open_file_sets(list([metric_obj.fname]), metric)

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

                    nc_dset.variables[var_name][:num_months, lat_indx, lon_indx] = \
                            rescale_metric_values(num_months, atom_tran[metric], metric, daily_flag)

                except (IndexError, ValueError, RuntimeError) as err:
                    mess = '\nError {}\nCould not write {} values for metric {} at lat/lon indexes: {} {}'\
                                                            .format(err, num_months, metric, lat_indx, lon_indx)
                    # form.lgr.critical(err)
                    print(mess)
                    return -1

            num_out_lines += 1

        # inform user with progress message
        # =================================
        new_time = time()
        if new_time - last_time > sleepTime:
            last_time = new_time
            num_out_str = format_string('%10d', int(num_out_lines), grouping=True)
            nremain = format_string("%10d", ntrans_lines - num_out_lines, grouping=True)
            stdout.write('\rLines output: {}\trejected: {:10d}\tremaining: {}'
                                                                    .format(num_out_str, num_bad_lines, nremain))

    # close file objects
    # ==================
    for key in trans_fobjs:
        trans_fobjs[key].close()

    nc_dset.close()

    print('\nFinished - having written {} lines to NC file: {}\n'.format(nlines, nc_fname))

    return nlines

def csv_to_coards_netcdf(form):
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
    study = form.study_defn['study']
    land_use = form.study_defn['land_use']
    file_list = form.trans_defn['file_list']

    nsuccess = 0
    for metric in NC_METRICS:
        fname = find_metric_in_flist_names(file_list, metric)
        if fname is None:
            continue

        metric_obj = Coard_nc_defn(metric, fname, land_use, out_dir, study, delete_flag)
        if metric_obj.fout_name is None:
            continue

        nlines = _generate_nc(form, metric_obj, daily_flag)
        if nlines > 0:
            nsuccess += 1

    if nsuccess == 0:
        print('No NC files generated')
    else:
        print('Generated {} COARDS compliant NC files'.format(nsuccess))

    return