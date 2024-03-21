#-------------------------------------------------------------------------------
# Name:
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2017
# Description: create dimensions: "longitude", "latitude" and "time"
#              create five ECOSSE variables i.e. 'n2o','soc','co2', 'no3', and 'ch4'
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'create_co2e_nc_class.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from os.path import splitext, isfile, join
from os import remove
import time
from netCDF4 import Dataset
from numpy import arange, float32

from nc_low_level_fns import generate_mnthly_atimes

MISSING_VALUE = -999.0
MAX_FIELDS_MONTHLY = 3600     # if there are more than this number of fields then assume CSV files are from a daily timestep
FLUXES = list(['ch4', 'co2', 'no3', 'n2o'])

def create_co2e_nc_dset(form, metric_obj):
    """
    return NC files name
    """
    func_name =  __prog__ + ' create_co2e_nc_dset'

    study   = metric_obj.study
    out_dir = metric_obj.out_dir
    metric  = metric_obj.metric
    fout_name = metric_obj.fout_name

    nfields      = form.trans_defn['nfields']
    delete_flag  = form.w_del_nc.isChecked()

    resolution     = form.study_defn['resolution']
    fut_end_year   = form.study_defn['futEndYr']
    clim_dset = form.study_defn['climScnr']

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
    alons = arange(ll_lon, ur_lon, resol, dtype=float32)
    alats = arange(ll_lat, ur_lat, resol, dtype=float32)
    num_alons = len(alons)
    num_alats = len(alats)
    form.bbox_nc = bbox

    mess = 'Number of longitudes: {} and latitudes: {}'.format(num_alons, num_alats)
    print(mess)

    # setup time dimension
    # ====================
    if nfields > MAX_FIELDS_MONTHLY:
        nmonths = int(12*(nfields)/365)
        timestep = 'Daily'
    else:
        nmonths = nfields
        timestep = 'Monthly'

    num_years = int(nmonths/12)
    fut_start_year = fut_end_year - num_years + 1

    atimes, atimes_strt, atimes_end = generate_mnthly_atimes(fut_start_year, nmonths)

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
    # lats = nc_dset.createVariable('latitude',dtype('float32').char,('latitude',))
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

    times = nc_dset.createVariable('time','f4',('time',))
    times.units = 'days since 1900-01-01'
    times.calendar = 'standard'
    times.axis = 'T'
    times.bounds = 'time_bnds'
    times[:] = atimes

    # create time_bnds variable
    # =========================
    time_bnds = nc_dset.createVariable('time_bnds','f4',('time','bnds'), fill_value = MISSING_VALUE)
    time_bnds._ChunkSizes = 1, 2
    time_bnds[:,0] = atimes_strt
    time_bnds[:,1] = atimes_end

    # create the area variable
    # ========================
    areas = nc_dset.createVariable('area','f4',('latitude','longitude'), fill_value = MISSING_VALUE)
    areas.units = 'km**2'
    areas.MISSING_VALUE = MISSING_VALUE

    # create the time dependent metrics and assign default data
    # =========================================================
    var_name = metric_obj.var_name
    var_varia = nc_dset.createVariable(var_name,'f4',('time', 'latitude','longitude'), fill_value = MISSING_VALUE)
    var_varia.long_name = metric_obj.long_name
    var_varia.units = metric_obj.units

    # close netCDF file
    # ================
    nc_dset.sync()
    nc_dset.close()

    mess = 'Created: ' + fout_name
    print(mess)
    # form.lgr.info()

    return fout_name, var_name, nmonths

class Co2e_nc_defn(object, ):
    '''
    instantiate
    '''
    def __init__(self, metric, rqrd_flist, land_use, out_dir, study, delete_flag = True):
        """

        """
        if land_use == 'ara':
            crop_name = 'Arable'
        elif land_use == 'gra':
            crop_name = 'Grassland'
        else:
            crop_name = land_use

        # long name
        # =========
        # long_name = 'flux ' + metric + ' carbon dioxide equivalent ' + crop_name
        long_name = 'flux ' + metric + ' ' + crop_name
        units = 'kg C m-2 yr-1'
        fname = join(out_dir, study + '_' + metric + '.nc')

        self.var_name = 'f' + metric + '_soil_' + land_use
        self.metric = metric
        self.long_name = long_name
        self.units = units
        self.out_dir = out_dir
        self.study = study
        self.rqrd_flist = rqrd_flist

        if isfile(fname):
            if delete_flag:
                try:
                    remove(fname)
                    print('Deleted: ' + fname)
                except PermissionError:
                    print('File: {} already exists but could not delete'.format(fname))
                    fname = None
            else:
                print('File ' + fname + ' already exists')
                fname = None

        self.fout_name = fname
