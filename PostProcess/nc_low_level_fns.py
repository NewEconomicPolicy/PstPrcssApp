#-------------------------------------------------------------------------------
# Name:        nc_low_level_fns.py
# Purpose:     Functions to create and write to netCDF files and return latitude and longitude indices
# Author:      Mike Martin
# Created:     25/01/2020
# Description: taken from netcdf_funcs.py in obsolete project PstPrcssNc
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'nc_low_level_fns.py'
__version__ = '0.0.0'
__author__ = 's03mm5'

from sys import stdout
from _datetime import datetime
from locale import format_string
from numpy import arange
from time import time

missing_value = -999.0
sleepTime = 3
imiss_value = int(missing_value)

WARNING_STR = '*** Warning *** '

def update_progress_bar(last_time, trans_nlines, num_out_lines, num_bad_lines):
        """
        Update progress bar
        """
        new_time = time()
        if new_time - last_time > sleepTime:
            last_time = new_time
            num_out_str = format_string("%d", int(num_out_lines), grouping=True)
            nremain = format_string("%d", trans_nlines - num_out_lines, grouping=True)
            stdout.write('\rLines output: {}\trejected: {}\tremaining: {}'
                         .format(num_out_str, num_bad_lines, nremain))

        return last_time

def generate_mnthly_atimes(fut_start_year, num_months):
    """
    expect 1092 for 91 years plus 2 extras for 40 and 90 year differences
    """

    atimes = arange(num_months)     # create ndarray
    atimes_strt = arange(num_months)
    atimes_end  = arange(num_months)

    date_1900 = datetime(1900, 1, 1, 12, 0)
    imnth = 1
    year = fut_start_year
    prev_delta_days = -999
    for indx in arange(num_months + 1):
        date_this = datetime(year, imnth, 1, 12, 0)
        delta = date_this - date_1900   # days since 1900-01-01

        # add half number of days in this month to the day of the start of the month
        # ==========================================================================
        if indx > 0:
            atimes[indx-1] = prev_delta_days + int((delta.days - prev_delta_days)/2)
            atimes_strt[indx-1] = prev_delta_days
            atimes_end[indx-1] =  delta.days - 1

        prev_delta_days = delta.days
        imnth += 1
        if imnth > 12:
            imnth = 1
            year += 1

    return atimes, atimes_strt, atimes_end

def get_nc_coords(form, latitude, longitude, max_lat_indx, max_lon_indx):
    """

    """
    ll_lon, ll_lat, ur_lon, ur_lat = form.bbox_nc
    resol = form.study_defn['resolution']

    lat_indx = round((latitude  - ll_lat)/resol)
    lon_indx = round((longitude - ll_lon)/resol)

    if lat_indx < 0 or lat_indx > max_lat_indx:
        print()
        print(WARNING_STR + 'latitude index {} out of bounds for latitude {}\tmax indx: {}'
                                                            .format(lat_indx, round(latitude, 4), max_lat_indx))
        return -1, -1

    if lon_indx < 0 or lon_indx > max_lon_indx:
        print()
        print(WARNING_STR + 'longitude index {} out of bounds for longitude {}\tmax indx: {}'
                                                            .format(lon_indx, round(longitude, 4), max_lon_indx))
        return -1, -1

    return lat_indx, lon_indx

def generate_yearly_atimes(fut_start_year, num_years):
    """
    expect 1092 for 91 years plus 2 extras for 40 and 90 year differences
    """

    atimes = arange(num_years)     # create ndarray
    atimes_strt = arange(num_years)
    atimes_end  = arange(num_years)

    date_1900 = datetime(1900, 1, 1, 12, 0)
    year = fut_start_year
    prev_delta_days = -999
    for indx in arange(num_years + 1):
        date_this = datetime(year, 1, 1, 12, 0)
        delta = date_this - date_1900   # days since 1900-01-01

        # add half number of days in this month to the day of the start of the month
        # ==========================================================================
        if indx > 0:
            atimes[indx-1] = prev_delta_days + int((delta.days - prev_delta_days)/2)
            atimes_strt[indx-1] = prev_delta_days
            atimes_end[indx-1] =  delta.days - 1

        prev_delta_days = delta.days
        year += 1

    return atimes, atimes_strt, atimes_end