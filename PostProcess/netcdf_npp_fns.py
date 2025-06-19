#-------------------------------------------------------------------------------
# Name:        spec_NCfuncs.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2017
# Description: create dimensions: "longitude", "latitude" and "time"
#              create five ECOSSE variables i.e. 'n2o','soc','co2', 'no3', and 'ch4'
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'netcdf_funcs.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import normpath, isfile, join
from os import remove
import time
from netCDF4 import Dataset
from numpy import arange, float64

from nc_low_level_fns import generate_mnthly_atimes

missing_value = -999.0
maxFieldsMonthly = 3600     # if there are more than this number of fields then assume CSV files are from a daily timestep
imiss_value = int(missing_value)

def create_npp_ncs(form, metrics, crop_names, land_use, out_dir, study, npp_units = 'kg C m-2 yr-1'):
    """
    return list of NC files names
    """
    func_name =  __prog__ + ' create_nc_file'

    if land_use == 'Arable':
        study += 'cropland'
    else:
        study += land_use.lower()

    resolution     = form.study_defn['resolution']
    fut_end_year   = form.study_defn['futEndYr']
    fut_start_year = form.study_defn['futStrtYr']
    bbox = form.study_defn['bbox']
    clim_dset = form.study_defn['climScnr']

    num_trans_fields = (fut_end_year - fut_start_year + 1)*12
    delete_flag = form.w_del_nc.isChecked()

    # expand bounding box to make sure all results are included
    # =========================================================
    ll_lon, ll_lat, ur_lon, ur_lat = form.study_defn['bbox']
    resol = resolution
    resol_d2 = resol/2.0

    ll_lon = resol*int(ll_lon/resol) - resol_d2
    ll_lat = resol*int(ll_lat/resol) - resol_d2

    # Extend the upper right coords so that alons and alats arrays encompass data
    # ===========================================================================
    ur_lon = resol*int(ur_lon/resol) + 2*resol + resol_d2
    ur_lat = resol*int(ur_lat/resol) + 2*resol + resol_d2

    bbox = list([ll_lon, ll_lat, ur_lon, ur_lat])

    # build lat long arrays
    # =====================
    alons = arange(ll_lon, ur_lon, resol, dtype=float64)
    alats = arange(ll_lat, ur_lat, resol, dtype=float64)
    num_alons = len(alons)
    num_alats = len(alats)
    form.bbox_nc = bbox

    mess = 'Number of longitudes: {} and latitudes: {}\n'.format(num_alons, num_alats)
    print(mess)

    # setup time dimension
    # ====================
    if num_trans_fields > maxFieldsMonthly:
        nmonths = int(12*(num_trans_fields)/365)
        # timestep = 'Daily'
    else:
        nmonths = num_trans_fields
        # timestep = 'Monthly'
    # num_years = int(nmonths/12)

    atimes, atimes_strt, atimes_end = generate_mnthly_atimes(fut_start_year, nmonths)

    # atimes_yr, atimes_strt_yr, atimes_end_yr = _generate_yearly_atimes(fut_start_year, num_years)

    fout_name_prfx = normpath(join(out_dir, study))

    # construct the output file name and delete if it already exists
    # ==============================================================
    fout_names = {}
    var_names = {}
    for crop in crop_names:
            var_names[crop] = {}

    for metric in metrics:

        fout_name = normpath(fout_name_prfx + '_' + metric + '.nc')
        if isfile(fout_name):
            if delete_flag:
                try:
                    remove(fout_name)
                    print('Deleted: ' + fout_name)
                except PermissionError:
                    print('Function: {}\tcould not delete file: {}'.format(func_name, fout_name))
                    return [-1, 0, 0]
            else:
                print('File ' + fout_name + ' already exists')
                return [-2, 0, 0]

        # call the Dataset constructor to create file
        # ===========================================

        nc_dset = Dataset(fout_name,'w', format='NETCDF4')

        # create global attributes
        # ========================
        nc_dset.history = study + ' consisting of ' + study + ' study'
        date_stamp = time.strftime('%H:%M %d-%m-%Y')
        nc_dset.attributation = 'Created at ' + date_stamp + ' from Spatial Ecosse'
        nc_dset.weather_dataset = clim_dset
        data_used = 'Data used: HWSD soil and {} weather dataset'.format(clim_dset)
        nc_dset.dataUsed = data_used

        # we create the dimensions using the createDimension method of a Group (or Dataset) instance
        nc_dset.createDimension('latitude', num_alats)
        nc_dset.createDimension('longitude', num_alons)
        nc_dset.createDimension('time', len(atimes))
        nc_dset.createDimension('bnds', 2)

        # create the variable (4 byte float in this case)
        # to create a netCDF variable, use the createVariable method of a Dataset (or Group) instance.
        # first argument is name of the variable, second is datatype, third is a tuple with the name (s) of the dimension(s).
        # lats = nc_dset.createVariable('latitude',dtype('float64').char,('latitude',))
        #
        lats = nc_dset.createVariable('latitude','f4',('latitude',))
        lats.description = 'degrees of latitude North to South in ' + str(resol) + ' degree steps'
        lats.units = 'degrees_north'
        lats.long_name = 'latitude'
        lats.axis = 'Y'
        lats[:] = alats

        lons = nc_dset.createVariable('longitude','f4',('longitude',))
        lons.units = 'degrees of longitude West to East in ' + str(resol) + ' degree steps'
        lons.units = 'degrees_east'
        lons.long_name = 'longitude'
        lons.axis = 'X'
        lons[:] = alons

        # monthly times
        # =============
        times = nc_dset.createVariable('time','f4',('time',))
        times.units = 'days since 1900-01-01'
        times.calendar = 'standard'
        times.axis = 'T'
        times.bounds = 'time_bnds'
        times[:] = atimes

        # create time_bnds variable
        # =========================
        time_bnds = nc_dset.createVariable('time_bnds','f4',('time','bnds'), fill_value = missing_value)
        time_bnds._ChunkSizes = 1, 2
        time_bnds[:,0] = atimes_strt
        time_bnds[:,1] = atimes_end

        # create the area variable
        # ========================
        areas = nc_dset.createVariable('area','f4',('latitude','longitude'), fill_value = missing_value)
        areas.units = 'km**2'
        areas.missing_value = missing_value

        # create the time dependent metrics and assign default data
        # =========================================================
        if metric == 'soc':
            long_name = 'soil organic carbon'
            units = 'kg C m-2'
        else:
            if metric == 'no3' or metric == 'n2o':
                units = 'kg N m-2 yr-1'
            elif metric == 'co2':
                units = 'kg C m-2 yr-1'
            elif metric == 'npp':
                units = npp_units

        for crop in crop_names:
            # var_name = 'f' + metric + '_soil_' + crop
            var_name = crop
            var_names[crop][metric] = var_name
            var_varia = nc_dset.createVariable(var_name,'f4',('time', 'latitude','longitude'), fill_value = missing_value)

            long_name = 'Net primary production'
            var_varia.long_name = long_name
            var_varia.units = units

        # close netCDF file
        # ================
        nc_dset.sync()
        nc_dset.close()
        fout_names[metric] = fout_name

        mess = 'Created: ' + fout_name
        print(mess)
        # form.lgr.info()

    return fout_names, var_names, nmonths