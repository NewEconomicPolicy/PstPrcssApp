#-------------------------------------------------------------------------------
# Name:
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'csv_to_raw_nc.py'
__version__ = '0.0.1'
__author__ = 's03mm5'


from locale import format_string
from time import time
from netCDF4 import Dataset
from sys import stdout

from input_output_funcs import open_file_sets, read_one_line
from nc_low_level_fns import get_nc_coords
from netcdf_funcs import create_raw_nc_dset

sleepTime = 5.0
bad_fobj_key = 'bad_lines'

# make sure you have the variable names in the same order as the conversion factors
# result names (same in both folders), must match order of other lists (assume they have .txt suffix)
#  'plant_C_inp':'kgC/ha/yr'}
METRICS      = list(['co2','no3','n2o','soc', 'npp'])
SOIL_METRICS = dict({'C_content':'kgC/ha', 'bulk_dens':'g/cm3', 'pH':'pH', 'clay':'%', 'silt':'%', 'sand':'%'})

out_delim = '\t'
out_delim = ','
line_length = 79

def _update_progress(last_time, metric, cell_id):
        """ Update progress bar """
        if time() - last_time > sleepTime:
            line = ('\rCompleted {} cells for {} metric'.format(cell_id, metric))
            len_line = len(line)
            padding = ' ' * (line_length - len_line)
            line += padding
            stdout.write(line)
            last_time = time()

        return last_time

def csv_to_raw_netcdf(form):
    '''
    NC file is deleted if it already exists
    '''
    nc_fname = create_raw_nc_dset(form, METRICS, SOIL_METRICS)
    if isinstance(nc_fname, int):
        return
    try:
        nc_dset = Dataset(nc_fname,'a', format='NETCDF4')
    except TypeError as err:
        print('Unable to open output file. {}'.format(err))
        return

    trans_files = form.trans_defn['file_list']     # Files comprising the LU transition result
    if len(trans_files) == 0:
        print('No transition files to process')
        return

    # max_lines = int(form.w_nlines.text())
    max_lines = 9999999                                        # stop processing after this number of lines
    max_lat_indx = nc_dset.variables['latitude'].shape[0]  - 1
    max_lon_indx = nc_dset.variables['longitude'].shape[0] - 1

    # open all files
    # ==============
    trans_fobjs, soil_header = open_file_sets(trans_files)

    # read and process each line
    # ==========================
    nline = 0
    num_out_lines = 0
    num_bad_lines = 0
    last_time = time()
    while (nline <= max_lines):

        # read in land use transition results
        # ===================================
        num_trans_time_vals, nsoil_metrics, line_prefix, atom_tran = read_one_line(trans_fobjs)
        if atom_tran == None:
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
            latitude  = float(slat)
            longitude = float(slon)
            lat_indx, lon_indx = get_nc_coords(form, latitude, longitude, max_lat_indx, max_lon_indx)
            if lat_indx == -1:
                continue

            nc_dset.variables['area'][lat_indx, lon_indx] = area
            nc_dset.variables['mu_global'][lat_indx, lon_indx] = mu_global

            for varname in atom_tran.keys():
                if atom_tran[varname] is None or varname not in nc_dset.variables:
                    continue

                nvals = len(atom_tran[varname])
                if varname == 'soil':

                    for indx, metric in enumerate(SOIL_METRICS):
                        nc_dset.variables[metric][lat_indx, lon_indx] = atom_tran[varname][indx]
                else:
                    if varname == 'npp':
                        atom_rec = [val/2 for val in atom_tran[varname]]    # divide by 2 for flux co2 from dry matter
                    else:
                        atom_rec = atom_tran[varname]
                    try:
                        nc_dset.variables[varname][lat_indx, lon_indx, :nvals] = atom_rec
                    except (IndexError, ValueError, RuntimeError) as err:
                        mess = '\nError {}\tCould not write {} values for metric {} at lat/lon indexes: {} {}'\
                                                            .format(err, nvals, varname, lat_indx, lon_indx)
                        form.lgr.critical(mess)
                        print(mess)
                        return -1

                    # Borneo addition: take difference between December of first year and last value
                    # ===============
                    if len(atom_tran[varname]) > 492:           # mustr have at least 40 years
                        val_decem_yr1  = atom_tran[varname][11]
                        val_decem_yr40 = atom_tran[varname][480 + 11]
                        val_decem_yr90 = atom_tran[varname][-1]
                        nc_dset.variables[varname][lat_indx, lon_indx, -2] = val_decem_yr40 - val_decem_yr1
                        nc_dset.variables[varname][lat_indx, lon_indx, -1] = val_decem_yr90 - val_decem_yr1

        num_out_lines += 1

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

