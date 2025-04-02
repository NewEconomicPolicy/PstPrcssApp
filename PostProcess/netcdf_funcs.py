# -------------------------------------------------------------------------------
# Name:        spec_NCfuncs.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2017
# Description: create dimensions: "longitude", "latitude" and "time"
#              create five ECOSSE variables i.e. 'n2o','soc','co2', 'no3', and 'ch4'
# Licence:     <your licence>
# -------------------------------------------------------------------------------
#
__prog__ = 'netcdf_funcs.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import normpath, isfile, join
from os import remove
import time
from netCDF4 import Dataset
from numpy import arange, float32

MISSING_VALUE = -999.0
IMISS_VALUE = int(MISSING_VALUE)

def create_raw_nc_dset(form, metrics, soil_metrics):
    """
    call this function before running spec against simulation files
    output_variables = list(['soc', 'co2', 'ch4', 'no3', 'n2o'])
    for var_name in output_variables[0:1]:
    """
    func_name = __prog__ + ' create_raw_nc_dset'

    study = form.study_defn['study']

    if form.study_defn['resolution'] is None:
        print('Error - cannot proceed - resolution is set to None')
        return 1

    # delete_flag = form.w_del_nc.isChecked()
    delete_flag = True

    # expand bounding box to make sure all results are included
    # =========================================================
    ll_lon, ll_lat, ur_lon, ur_lat = form.study_defn['bbox']
    resol = form.study_defn['resolution']
    resol_d2 = resol/2.0

    ll_lon = resol*int(ll_lon/resol) - resol_d2
    ll_lat = resol*int(ll_lat/resol) - resol_d2

    # Extend the upper right coords so that alons and alats arrays encompass data
    # ===========================================================================
    ur_lon = resol*int(ur_lon/resol) + resol + resol_d2
    ur_lat = resol*int(ur_lat/resol) + resol + resol_d2

    bbox = list([ll_lon, ll_lat, ur_lon, ur_lat])

    # build lat long arrays
    # =====================
    alons = arange(ll_lon, ur_lon, resol, dtype=float32)
    alats = arange(ll_lat, ur_lat, resol, dtype=float32)
    num_alons = len(alons)
    num_alats = len(alats)
    form.bbox_nc = bbox

    mess = 'Number of longitudes: {} and latitudes: {}\n'.format(num_alons, num_alats)
    print(mess)
    '''
    sys.stdout.write(mess)
    sys.stdout.flush()
    '''
    years = arange(form.study_defn['futStrtYr'], form.study_defn['futEndYr'] + 1)
    nyears = len(years)
    atimes = arange(form.trans_defn['nfields'] + 2)  # expect 1092 for 91 years plus 2 extras for 40 and 90 year differences

    # construct the output file name and delete if it already exists
    # ==============================================================
    out_dir = form.w_lbl_rslts.text()
    fout_name = normpath(join(out_dir, study + '.nc'))
    if isfile(fout_name):
        if delete_flag:
            try:
                remove(fout_name)
                print('Deleted file: ' + fout_name)
            except PermissionError:
                print('Function: {}\tcould not delete file: {}'.format(func_name, fout_name))
                return 1
        else:
            return fout_name

    # call the Dataset constructor to create file
    # ===========================================
    fut_clim_scen = 'EObs'
    nc_dset = Dataset(fout_name, 'w')

    # create global attributes
    # ========================
    nc_dset.history = study + ' consisting of ' + study + ' study'
    date_stamp = time.strftime('%H:%M %d-%m-%Y')
    nc_dset.attributation = 'Created at ' + date_stamp + ' from Spatial Ecosse '
    nc_dset.future_climate_scenario = fut_clim_scen
    data_used = 'Data used: HWSD soil, '
    data_used += '{} past weather and {} future climate'.format(fut_clim_scen, fut_clim_scen)
    nc_dset.dataUsed = data_used

    # we create the dimensions using the createDimension method of a Group (or Dataset) instance
    nc_dset.createDimension('lat', num_alats)
    nc_dset.createDimension('lon', num_alons)
    nc_dset.createDimension('time', len(atimes))

    # create the variable (4 byte float in this case)
    # to create a netCDF variable, use the createVariable method of a Dataset (or Group) instance.
    # first argument is name of the variable, second is datatype, third is a tuple with the name (s) of the dimension(s).
    # lats = nc_dset.createVariable('latitude',dtype('float32').char,('lat',))
    #
    lats = nc_dset.createVariable('latitude', 'f4', ('lat',))
    lats.units = 'degrees of latitude North to South in ' + str(resol) + ' degree steps'
    lats.long_name = 'latitude'
    lats[:] = alats

    lons = nc_dset.createVariable('longitude', 'f4', ('lon',))
    lons.units = 'degrees of longitude West to East in ' + str(resol) + ' degree steps'
    lons.long_name = 'longitude'
    lons[:] = alons

    # TODO: check these
    times = nc_dset.createVariable('time', 'i2', ('time',))
    times.units = 'months from January {} - {} years'.format(form.study_defn['futStrtYr'], nyears)
    times[:] = atimes

    # create the area variable
    # ========================
    var_varia = nc_dset.createVariable('area', 'f4', ('lat', 'lon'), fill_value=MISSING_VALUE)
    var_varia.units = 'km**2'
    var_varia.missing_value = MISSING_VALUE

    # create the mu_global variable
    # =============================
    var_varia = nc_dset.createVariable('mu_global', 'i4', ('lat', 'lon'), fill_value=imiss_value)
    var_varia.units = 'HWSD global mapping unit'
    var_varia.missing_value = IMISS_VALUE

    # create the soil variables
    # =========================
    for metric in soil_metrics:
        var_varia = nc_dset.createVariable(metric, 'f4', ('lat', 'lon'), fill_value=MISSING_VALUE)
        var_varia.units = soil_metrics[metric]
        var_varia.missing_value = MISSING_VALUE

    # create the time dependent metrics and assign default data
    # =========================================================
    for var_name in metrics:
        var_varia = nc_dset.createVariable(var_name, 'f4', ('lat', 'lon', 'time'), fill_value=MISSING_VALUE)
        var_varia.units = 'kg/hectare'
        var_varia.missing_value = MISSING_VALUE

    # create the change in soc from start of simulation to end year
    # =============================================================
    var_varia = nc_dset.createVariable('soc_diff', 'f4', ('lat', 'lon'), fill_value=MISSING_VALUE)
    var_varia.long_name = ''
    var_varia.units = 'kg/hectare'

    # close netCDF file
    # ================
    nc_dset.sync()
    nc_dset.close()

    mess = 'Created {} netCDF file'.format(fout_name)
    print(mess)
    # form.lgr.info()

    return fout_name
