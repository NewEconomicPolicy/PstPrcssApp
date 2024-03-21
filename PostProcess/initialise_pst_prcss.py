"""
#-------------------------------------------------------------------------------
# Name:        initialise_pst_prcss.py
# Purpose:     script to read read and write the setup and configuration files
# Author:      Mike Martin
# Created:     16/05/2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""

__prog__ = 'initialise_pst_prcss.py'
__version__ = '0.0.0'

# Version history
# ---------------
# 
from os.path import normpath, exists, isfile, isdir, join, lexists
from os import getcwd, makedirs
from json import dump as json_dump, load as json_load
from time import sleep
from set_up_logging import set_up_logging
from input_output_funcs import ecosse_results_files, check_cut_csv_files

sleepTime = 5
ERROR_STR = '*** Error *** '

CONFIG_ATTRIBUTES = ['extra_metrics', 'user_settings']
MIN_GUI_LIST = ['results_dir', 'sims_dir', 'overwrite', 'make_rslts_dir', 'nyears_trim', 'aggreg_daily']    # , 'sngl_sim'
EXTRA_METRICS = ['no3', 'npp']

IPCC_CO2EQUIV_CH4 = 28      # from the latest IPCC report (IPCC, 2021)
IPCC_CO2EQUIV_N2O = 273

def initiation(form):
    '''
    initiate the programme
    '''
    # retrieve settings
    # =================
    applic_str = 'post_process'
    form.settings = _read_setup_file(applic_str)
    form.settings['config_file'] = normpath(form.settings['config_dir'] + '/' + applic_str + '_config.json')
    form.settings['co2equiv_ch4 '] = IPCC_CO2EQUIV_CH4
    form.settings['co2equiv_n2o'] = IPCC_CO2EQUIV_N2O
    set_up_logging(form, applic_str)

    return

def _read_setup_file(applic_str):
    """
    read settings used for programme from the setup file, if it exists,
    or create setup file using default values if file does not
    """
    func_name =  __prog__ +  ' _read_setup_file'

    # validate setup file
    # ===================
    settings_list = ['config_dir', 'log_dir', 'fname_png']
    fname_setup = applic_str + '_setup.json'

    setup_file = join(getcwd(), fname_setup)
    if exists(setup_file):
        try:
            with open(setup_file, 'r') as fsetup:
                setup = json_load(fsetup)

        except (OSError, IOError) as err:
                print(str(err))
                sleep(sleepTime)
                exit(0)
    else:
        setup = _write_default_setup_file(setup_file)

    # initialise vars
    # ===============
    settings = setup['setup']
    for key in settings_list:
        if key not in settings:
            print(ERROR_STR + 'setting {} is required in setup file {} '.format(key, setup_file))
            sleep(sleepTime)
            exit(0)

    settings['applic_str'] = applic_str

    # make sure directories exist
    # ===========================
    config_dir = settings['config_dir']
    if not lexists(config_dir):
        makedirs(config_dir)

    log_dir = settings['log_dir']
    if not lexists(log_dir):
        makedirs(log_dir)

    # report settings
    # ===============
    print('Resource location:')
    print('\tconfiguration files: ' + config_dir)
    print('\tlog files: ' + log_dir)
    print('')

    return settings

def read_config_file(form):
    """
    read widget settings used in the previous programme session from the config file, if it exists,
    or create config file using default settings if config file does not exist
    """
    func_name =  __prog__ +  ' read_config_file'

    config_file = form.settings['config_file']
    if exists(config_file):
        try:
            with open(config_file, 'r') as fconfig:
                config = json_load(fconfig)
                print('Read config file ' + config_file)
        except (OSError, IOError) as err:
                print(str(err))
                return False
    else:
        config = _write_default_config_file(config_file)

    # ====================
    for key in CONFIG_ATTRIBUTES:
        if key not in config:
            print(ERROR_STR + 'attribute {} is required in configuration file {} '.format(key, config_file))
            sleep(sleepTime)
            exit(0)

    # ====================

    grp = 'user_settings'
    for key in MIN_GUI_LIST:
        if key not in config[grp]:
            print(ERROR_STR + 'attribute {} is required for group {} in configuration file {} '.format(key, grp,
                                                                                                         config_file))
            sleep(sleepTime)
            exit(0)

    # ====================
    grp = 'user_settings'
    aggreg_daily = config[grp]['aggreg_daily']
    # sngl_sim = config[grp]['sngl_sim']
    results_dir = config[grp]['results_dir']
    sims_dir = config[grp]['sims_dir']
    overwrite_flag = config[grp]['overwrite']
    mk_rslts_dir_flag = config[grp]['make_rslts_dir']
    nyears_trim = config[grp]['nyears_trim']

    # displays detail
    # ===============
    form.w_lbl_sims.setText(sims_dir)
    form.w_lbl_rslts.setText(results_dir)
    descriptor, form.trans_defn = ecosse_results_files(results_dir, 'Contents: ')
    form.w_lbl06.setText(descriptor)
    form.w_nyears.setText(str(nyears_trim))

    # set check boxes
    # ===============
    if aggreg_daily:
        form.w_aggreg.setCheckState(2)
    else:
        form.w_aggreg.setCheckState(0)

    if mk_rslts_dir_flag:
        form.w_create_outdir.setCheckState(2)
    else:
        form.w_create_outdir.setCheckState(0)

    if overwrite_flag:
        form.w_del_nc.setCheckState(2)
    else:
        form.w_del_nc.setCheckState(0)

    check_cut_csv_files(form)       # adjust push button

    # ====================
    grp = 'extra_metrics'
    for key in EXTRA_METRICS:
        metric_flag = config[grp][key]
        if metric_flag:
            form.w_metrics[key].setCheckState(2)
        else:
            form.w_metrics[key].setCheckState(0)

    return True

def _write_default_config_file(config_file):
    """
    stanza if config_file needs to be created
    """
    default_config = {
        'user_settings': {
            'aggreg_daily': True,
            'make_rslts_dir': True,
            'nyears_trim': 0,
            'overwrite': True,
            'results_dir': '',
            'sims_dir': ''
        }
    }
    # create configuration file
    # =========================
    with open(config_file, 'w') as fconfig:
        json_dump(default_config, fconfig, indent=2, sort_keys=True)
        print('Wrote default configuration file: ' + config_file)

    return default_config

def write_config_file(form, message_flag = True):
    """
    # write current selections to config file
    """
    config_file = form.settings['config_file']

    config = {
        'user_settings': {
            'aggreg_daily': form.w_aggreg.isChecked(),
            'make_rslts_dir': form.w_create_outdir.isChecked(),
            'nyears_trim': int(form.w_nyears.text()),
            'overwrite':   form.w_del_nc.isChecked(),
            'results_dir': form.w_lbl_rslts.text(),
            'sims_dir': form.w_lbl_sims.text()
        },
        'extra_metrics': {
            'no3': form.w_metrics['no3'].isChecked(),
	        'npp': form.w_metrics['npp'].isChecked()
        }
    }
    with open(config_file, 'w') as fconfig:
        json_dump(config, fconfig, indent=2, sort_keys=True)
        print('Wrote configuration file: ' + config_file)

    return

def report_csv_contents(form, fname):
    """
    write settings to form
    """
    if not isfile(fname):
        return

    with open(fname, 'r') as fobj:
        nlines = len(fobj.readlines())

    form.w_lbl08.setText('Number of lines: {}'.format(nlines))
    return

def _write_default_setup_file(setup_file):
    """
    stanza if setup_file needs to be created - TODO: improve
    """
    root_dir = None

    for drive in list(['E:\\','C:\\']):
        if isdir(drive):
            root_dir = join(drive, 'AbUniv\\GlobalEcosseSuite')
            break

    default_setup = {
        'setup': {
            'config_dir': join(root_dir, 'config'),
            'log_dir'   : join(root_dir, 'logs'),
            'fname_png' : join(root_dir, 'Images', 'World_small.PNG')
        }
    }
    # create setup file
    # =================
    with open(setup_file, 'w') as fsetup:
        json_dump(default_setup, fsetup, indent=2, sort_keys=True)
        print('Wrote default setup file: ' + setup_file)

    return default_setup