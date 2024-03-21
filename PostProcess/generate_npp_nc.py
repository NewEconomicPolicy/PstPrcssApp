#-------------------------------------------------------------------------------
# Name:
# Purpose:     main function to process Spec results
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Comments:    Global warming potential(GWP)
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'generate_npp_nc.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import split
from locale import format_string
from time import time
from netCDF4 import Dataset
from statistics import mean
from pandas import read_csv
from sys import stdout
from glob import glob
from math import exp
from netcdf_npp_fns import create_npp_ncs
from nc_low_level_fns import get_nc_coords

sleepTime = 5.0
bad_fobj_key = 'bad_lines'
NGRANULARITY = 120         # HWSD resolution - 120 * 30 arc seconds = 1 degree
maxFieldsMonthly = 3600

nc_metrics      = list(['npp'])

out_delim = '\t'
out_delim = ','
line_length = 79
hectares_to_m2 = 0.0001

crop_names = {'maize': 'Grain Maize', 'swheat': 'Spring Wheat'}
crop_names = {'npp': 'npp'}
rescale_factor = {'Arable': 0.44, 'Grassland':0.44, 'Forestry':0.8, 'Semi-natural':0.44, 'Miscanthus':1.6, 'SRC':0.88}
fractions      = {'Arable': 0.53, 'Grassland':0.71, 'Forestry':0.8, 'Semi-natural':0.8,  'Miscanthus':0.3, 'SRC':0.23}
land_use_mappings = {'ara':'Arable', 'gra':'Grassland', 'for':'Forestry', 'nat':'Semi-natural', 'mis':'Miscanthus',
                                                                                                        'src':'SRC'}

def _miami_dyce(land_use, temp, precip):
    '''
    modification of the miami model by altering coefficients
        NB no need to reparameterise exponent terms since model is effectively linear in climate range of the UK

    rescale factor: multiply npp values according to land cover type:
        forest (3) = 0.875
        semi-natural (4), grassland (2), arable (1): forest/2 = 0.44
        Miscanthus (5): multiply by 1.6 (from comparison of unadjusted Miami results with Miscanfor peak yield results)
        SRC (6): as forest - peak yield is just over half that of Miscanthus

    for plant inputs to soil:  multiply npp values by different fractions according to land cover
        Miscanthus: 0.3  (widely reported as losing around 1/3 of peak mass before harvest; small amount returns to rhizome)
        SRC:        0.15 (assumed as forest)
    '''
    nppt = 3000/(1 + exp(1.315 - 0.119*temp))
    nppp = 3000*(1 - exp(-0.000664*precip))
    npp = 0.5*10*rescale_factor[land_use]*min(nppt, nppp)  # times 10 for unit conversion (g/m^2 to Kg/ha) and .5 for C

    soil_input = fractions[land_use]*npp     # soil input of vegetation

    return npp

def sims_results_to_nc(form):
    """
    #    call this function before running spec against simulation files
    #    output_variables = list(['soc', 'co2', 'ch4', 'no3', 'n2o'])
    #    for var_name in output_variables[0:1]:
    """
    mess = '*** Yearly data will be generated from Miami-Dyce'
    cal_method_new = True

    print(mess + ' input ***')
    out_dir = 'E:\\temp'
    last_time = time()

    # gather required vars from UI
    # ============================
    lu = form.study_defn['land_use']
    if lu in land_use_mappings:
        land_use = land_use_mappings[lu]
    else:
        mess = 'Land use abbreviation ' + lu + ' not found in land use mappings keys: '
        mess += str(land_use_mappings.keys())
        print(mess  +  ' will use ara (Arable) instead')
        land_use = form.study_defn['ara']

    sims_dir = form.w_lbl_sims.text()
    dummy, tail_name = split(sims_dir)
    study = tail_name.split('_')[0] + '_'      # for example we should get Elbasan_

    nc_fnames, var_names, num_months = create_npp_ncs(form, nc_metrics, crop_names, land_use, out_dir, study,
                                                      npp_units = 'kg C ha-1 yr-1')
    if isinstance(nc_fnames, int):
        return

    # open the newly created NC files
    # ===============================
    nc_dsets = {}
    for nc_metric in nc_metrics:
        try:
            nc_dsets[nc_metric] = Dataset(nc_fnames[nc_metric],'a', format='NETCDF4')
        except TypeError as err:
            mess = 'Unable to open output file. {0}'.format(err)
            print(mess)
            return

    max_lat_indx = nc_dsets[nc_metric].variables['latitude'].shape[0]  - 1
    max_lon_indx = nc_dsets[nc_metric].variables['longitude'].shape[0] - 1

    # main loop - cycle through weather and simulations
    # =================================================
    # sims_dirs = glob(sims_dir + '/' + study + '*')
    wthr_dirs = glob(sims_dir + '\\[0-9]*')
    num_locations = len(wthr_dirs)
    nlocs_out = 0
    var_name = 'npp'
    metric   = 'npp'
    for wthr_dir in wthr_dirs:
        dummy, sdir = split(wthr_dir)
        gran_lat, gran_lon = sdir.split('_')
        met_files = glob(wthr_dir + '\\met*s.txt')
        npp_list = []

        # render each met file as a data frame
        # ====================================
        precip_ann = 0
        temp_list = []
        for met_fname in met_files:
            npp_1yr_list = []       # npp for year based on temperature and precip for each month
            data_frame = read_csv(met_fname, sep='\t', names = ['mnth','precip','pet','temp'])
            for rec in data_frame.values:
                precip_ann += rec[1]
                precip      = 12*rec[1]      # scale precip to annual value
                temperature = rec[3]
                temp_list.append(temperature)
                npp = _miami_dyce(land_use, temperature, precip)
                npp_1yr_list.append(npp)

            # normalise
            # =========
            sum_npp = sum(npp_1yr_list)
            npp_norm = [val/sum_npp for val in npp_1yr_list]
            mean_temp= mean(temp_list)
            npp = _miami_dyce(land_use, mean_temp, precip_ann)
            npp_list += [12*val*npp for val in npp_norm]

        # read area from manifest file
        # ============================
        area = 0.0
        nrejects = 0
        latitude  = 90 - float(gran_lat)/NGRANULARITY
        longitude = float(gran_lon)/NGRANULARITY - 180

        lat_indx, lon_indx = get_nc_coords(form, latitude, longitude, max_lat_indx, max_lon_indx)
        if lat_indx == -1:
            nrejects += 1
            continue

        try:
            nc_dsets[metric].variables['area'][lat_indx, lon_indx] = area

            nc_dsets[metric].variables[var_name][:num_months, lat_indx, lon_indx] = npp_list
            nlocs_out += 1
            '''
                             _rescale_metric_values(num_months, npp_list, metric, daily_flag)
            '''

        except (IndexError, ValueError, RuntimeError) as err:
            mess = '\nError {}\nCould not write {} values for metric {} at lat/lon indexes: {} {}'\
                                                    .format(err, num_months, metric, lat_indx, lon_indx)
            # form.lgr.critical(err)
            print(mess)
            return -1


        # inform user with progress message
        # =================================
        new_time = time()
        if new_time - last_time > sleepTime:
            last_time = new_time
            num_out_str = format_string('%10d', int(nlocs_out), grouping=True)
            nremain = format_string("%10d", num_locations - nlocs_out, grouping=True)
            stdout.write('\rLines output: {}\trejected: {:10d}\tremaining: {}'
                                                                    .format(num_out_str, nrejects, nremain))
    for metric in nc_metrics:
        nc_dsets[metric].close()

    print('\nFinished - having written {} lines to {} NC files'.format(nlocs_out, len(nc_fnames)))

    return
