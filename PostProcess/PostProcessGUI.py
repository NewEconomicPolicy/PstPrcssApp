#-------------------------------------------------------------------------------
# Name:        PostProcessGUI.py
# Purpose:     Creates a GUI to run limited data files for Ecosse
# Author:      Mike Martin
# Created:     16/05/2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'PostProcessGUI.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import normpath, isdir, isfile, split, join
from os import mkdir
from glob import glob
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QWidget, QApplication, QHBoxLayout, QVBoxLayout, QGridLayout, \
                                                             QPushButton, QCheckBox, QFileDialog, QLineEdit
from time import sleep

from initialise_pst_prcss import initiation, read_config_file, write_config_file
from input_output_funcs import read_study_definition, ecosse_results_files, change_create_rslts_dir, cut_csv_files
from input_output_funcs import check_cut_csv_files, aggregate_csv_create_coards, clean_and_zip, chng_study_create_co2e

from aggregate_rslts_to_csv import aggreg_metrics_to_csv, aggregate_soil_data_to_csv
from generate_npp_nc import sims_results_to_nc
from csv_to_raw_nc import csv_to_raw_netcdf
from csv_to_co2e_nc import csv_to_co2e_netcdf
from csv_to_coards_nc import csv_to_coards_netcdf
from spec_utilities import trim_summaries
from spec_check import check_spec_results

STD_FLD_SIZE = 60
STD_BTN_SIZE = 110
STD_CMBO_SIZE = 150
NREGIONS = 5

EXTRA_METRICS = ['no3', 'npp']

class Form(QWidget):

    def __init__(self, parent=None):

        super(Form, self).__init__(parent)

        # read settings
        initiation(self)

        # define two vertical boxes, in LH vertical box put the painter and in RH put the grid
        # define horizon box to put LH and RH vertical boxes in
        hbox = QHBoxLayout()
        hbox.setSpacing(15)

        # left hand vertical box consists of png image
        # ============================================
        lh_vbox = QVBoxLayout()

        # LH vertical box contains image only
        w_lbl20 = QLabel()
        pixmap = QPixmap(self.settings['fname_png'])
        w_lbl20.setPixmap(pixmap)

        lh_vbox.addWidget(w_lbl20)

        # add LH vertical box to horizontal box
        hbox.addLayout(lh_vbox)

        # right hand box consists of combo boxes, labels and buttons
        # ==========================================================
        rh_vbox = QVBoxLayout()

        # The layout is done with the QGridLayout
        grid = QGridLayout()
        grid.setSpacing(15)	# set spacing between widgets

        # line 3 - path to simulations
        # ============================
        irow = 2
        w_sims_dir = QPushButton("Simulations dir")
        helpText = 'Option to enable user to select a Global Ecosse simulations directory'
        w_sims_dir.setToolTip(helpText)
        w_sims_dir.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_sims_dir, irow, 0)
        w_sims_dir.clicked.connect(self.fetchSimsDir)

        w_lbl_sims = QLabel()
        grid.addWidget(w_lbl_sims, irow, 1, 1, 5)
        self.w_lbl_sims = w_lbl_sims

        irow += 1
        w_create_outdir = QCheckBox('Auto-create results directory')
        grid.addWidget(w_create_outdir, irow, 0, 1, 2)
        helpText = 'Check for results directory corresponding to simulations directory\n' + \
                   ' and create if it does not already exist'
        w_create_outdir.setToolTip(helpText)
        w_create_outdir.setChecked(True)
        self.w_create_outdir = w_create_outdir

        # display directory and report number of lines, etc.
        # =================================================
        irow += 1
        w_rslts_dir = QPushButton("Results directory")
        helpText = 'Global Ecosse outputs directory containing the aggregated CSV results.'
        w_rslts_dir.setFixedWidth(STD_BTN_SIZE)
        w_rslts_dir.setToolTip(helpText)
        grid.addWidget(w_rslts_dir, irow, 0)
        w_rslts_dir.clicked.connect(self.fetchRsltsDir)

        w_lbl_rslts = QLabel('')
        grid.addWidget(w_lbl_rslts, irow, 1, 1, 5)
        self.w_lbl_rslts = w_lbl_rslts

        # ========== results directory contents
        irow += 1
        w_lbl06 = QLabel('')
        w_lbl06.setMinimumWidth(600)
        grid.addWidget(w_lbl06, irow, 0, 1, 6)
        self.w_lbl06 = w_lbl06

        # ========== options
        irow += 1
        icol = 0
        w_lbl07 = QLabel('Extra metrics to create:')
        w_lbl07.setAlignment(Qt.AlignRight)
        grid.addWidget(w_lbl07, irow, icol)

        w_metrics = {}
        for metric in EXTRA_METRICS:
            icol += 1
            w_metrics[metric] = QCheckBox(metric)
            grid.addWidget(w_metrics[metric], irow, icol)

        self.w_metrics = w_metrics

        # ========== spacer
        # irow += 1
        # grid.addWidget(QLabel(), irow, 0)

        # line 12 - settings
        # ==================
        irow += 1
        w_del_nc = QCheckBox('Delete existing NC files')
        grid.addWidget(w_del_nc, irow, 0, 1, 2)
        helpText = 'Delete existing NC file'
        w_del_nc.setToolTip(helpText)
        w_del_nc.setChecked(True)
        self.w_del_nc = w_del_nc

        w_aggreg = QCheckBox('Aggregate daily values to monthly')
        grid.addWidget(w_aggreg, irow, 2, 1, 2)
        helpText = 'If inputs are daily values then aggregate to monthly'
        w_aggreg.setToolTip(helpText)
        w_aggreg.setChecked(True)
        self.w_aggreg = w_aggreg

        # ========== spacer
        irow += 2
        lbl13s = QLabel()
        grid.addWidget(lbl13s, irow, 0)

        # Operations
        # ==========
        irow += 1
        w_lbl09 = QLabel('Operations')
        w_lbl09.setAlignment(Qt.AlignCenter)
        w_lbl09.setToolTip('Each operation applies to selected simulation only')
        grid.addWidget(w_lbl09, irow, 0)

        irow += 1
        icol = 0
        w_lbl10 = QLabel('Unique:')
        w_lbl10.setAlignment(Qt.AlignRight)
        w_lbl10.setToolTip('Each operation applies to selected simulation only')
        grid.addWidget(w_lbl10, irow, icol)

        icol += 1
        w_aggr_to_csv = QPushButton('Aggregate to CSV')
        helpText = 'Aggregate data from previously created SUMMARY.OUT and soil data from input.txt files to CSV files'
        w_aggr_to_csv.setToolTip(helpText)
        w_aggr_to_csv.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_aggr_to_csv, irow, icol)
        w_aggr_to_csv.clicked.connect(self.aggregToCsvClicked)

        icol += 1
        w_csv_to_co2e = QPushButton('CSV to CO2e NC')
        helpText = 'Read data from previously created CSV files, calculate Net CO2e and write to a raw,\n' + \
                                                                'that is a non-COARDS compliant, NetCDF file'
        w_csv_to_co2e.setToolTip(helpText)
        w_csv_to_co2e.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_csv_to_co2e, irow, icol)
        w_csv_to_co2e.clicked.connect(self.csvDataToCO2eNcClicked)

        icol += 2
        w_csv_to_nc = QPushButton('CSV to raw NC')
        helpText = 'Read data from previously created CSV files and write to a raw,\n' + \
                                                                'that is a non-COARDS compliant, NetCDF file'
        w_csv_to_nc.setToolTip(helpText)
        w_csv_to_nc.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_csv_to_nc, irow, icol)
        w_csv_to_nc.clicked.connect(self.csvDataToRawNcClicked)

        # =======
        irow += 1
        icol = 0
        w_lbl11 = QLabel('General:')
        w_lbl11.setAlignment(Qt.AlignRight)
        w_lbl11.setToolTip('Each operation applies to selected simulation only')
        grid.addWidget(w_lbl11, irow, icol)

        icol += 3
        w_csv_to_crds = QPushButton('CSV to COARDS NCs')
        helpText = 'reads CSV result files and creates corresponding COARDS compliant NC files - \n' + \
                   'Cooperative Ocean/Atmosphere Research Data Service - \n' + \
                   'see: https://ferret.pmel.noaa.gov/Ferret/documentation/coards-netcdf-conventions'
        w_csv_to_crds.setFixedWidth(STD_BTN_SIZE)
        w_csv_to_crds.setToolTip(helpText)
        w_csv_to_crds.clicked.connect(self.writeCoardsNcClicked)
        grid.addWidget(w_csv_to_crds, irow, icol)

        icol += 1
        w_npp = QPushButton('Write NPP NC')
        helpText = 'reads weather data from the simulations directory for a Global ECOSSE project and creates an NC file'
        w_npp.setToolTip(helpText)
        w_npp.setFixedWidth(STD_BTN_SIZE)
        w_npp.clicked.connect(self.writeNppClicked)
        grid.addWidget(w_npp, irow, icol)

        icol += 1
        w_soil = QPushButton('Write Soil CSV')
        helpText = 'reads soil values from each simulation directory and creates an CSV file'
        w_soil.setToolTip(helpText)
        w_soil.setFixedWidth(STD_BTN_SIZE)
        w_soil.clicked.connect(self.writeSoilCsvClicked)
        grid.addWidget(w_soil, irow, icol)
        max_icol = icol

        # SV line
        # =======
        irow += 1
        icol = 0
        w_lbl14 = QLabel('Soils-R-GGREAT SV:')
        w_lbl14.setAlignment(Qt.AlignRight)
        w_lbl14.setToolTip('SV')
        grid.addWidget(w_lbl14, irow, icol)

        icol += 2
        w_cut_csv = QPushButton('Cut 200 years')
        helpText = 'If CSV files are 300 years then use cut to create new files with first 200 years removed'
        w_cut_csv.setToolTip(helpText)
        w_cut_csv.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_cut_csv, irow, icol)
        w_cut_csv.clicked.connect(self.cutCsvFilesClicked)
        self.w_cut_csv = w_cut_csv

        icol += 1
        w_prcss_all = QPushButton('Process all', self)
        helpText = 'Aggregate to CSV then calculate Net CO2e and write to a raw,\n' + \
                   'that is a non-COARDS compliant, NetCDF file for all related simulations'
        w_prcss_all.setToolTip(helpText)
        w_prcss_all.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_prcss_all, irow, icol)
        w_prcss_all.clicked.connect(lambda: self.maProcessAll(False))

        icol += 1
        w_zip_sv = QPushButton('Clean and Zip', self)
        helpText = 'Management version only e.g. simulation directories start with Reg_'
        w_zip_sv.setToolTip(helpText)
        w_zip_sv.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_zip_sv, irow, icol)
        w_zip_sv.clicked.connect(lambda: self.cleanZip(False))

        # MK line
        # =======
        irow += 1
        icol = 0
        w_lbl12 = QLabel('Verify MK:')
        w_lbl12.setAlignment(Qt.AlignRight)
        w_lbl12.setToolTip('MK operations')
        grid.addWidget(w_lbl12, irow, icol)

        icol += 1
        w_trim = QPushButton('Trim Summaries')
        helpText = 'reduce size of summary files'
        w_trim.setToolTip(helpText)
        w_trim.setFixedWidth(STD_BTN_SIZE)
        w_trim.clicked.connect(self.trimSummaryFiles)
        grid.addWidget(w_trim, irow, icol)

        icol += 1
        w_lbl20 = QLabel('N Years:')
        helpText = 'Retain last N years and discard all previous years'
        w_lbl20.setToolTip(helpText)
        w_lbl20.setAlignment(Qt.AlignRight)
        grid.addWidget(w_lbl20, irow, icol)

        icol += 1
        w_nyears = QLineEdit()
        w_nyears.setToolTip(helpText)
        w_nyears.setFixedWidth(STD_FLD_SIZE)
        w_nyears.textChanged.connect(self.chckYears)
        grid.addWidget(w_nyears, irow, icol)
        self.w_nyears = w_nyears

        icol += 1
        w_mk_prcss = QPushButton('All stages', self)
        helpText = 'Trim summaries, aggregate to CSV and write COARDS NCs - Matthias Kuhnert'
        w_mk_prcss.setToolTip(helpText)
        w_mk_prcss.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_mk_prcss, irow, icol)
        w_mk_prcss.clicked.connect(self.mkProcess)

        # SuperG
        # ======
        irow += 1
        icol = 0
        w_lbl13 = QLabel('Super-G MA:')
        w_lbl13.setAlignment(Qt.AlignRight)
        w_lbl13.setToolTip('MA operations')
        grid.addWidget(w_lbl13, irow, icol)

        icol += 1
        w_ma_prcss = QPushButton('MA process', self)
        helpText = 'Aggregate to CSV then calculate Net CO2e and write to a raw,\n' + \
                                                'that is a non-COARDS compliant, NetCDF file for this simulation'
        w_ma_prcss.setToolTip(helpText)
        w_ma_prcss.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_ma_prcss, irow, icol)
        w_ma_prcss.clicked.connect(self.maProcess)

        icol += 1
        w_cut_csv160 = QPushButton('Cut 160 years')
        helpText = 'If CSV files are 300 years then use cut to create new files with first 160 years removed'
        w_cut_csv160.setToolTip(helpText)
        w_cut_csv160.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_cut_csv160, irow, icol)
        w_cut_csv160.clicked.connect(self.cutCsvFiles1961Clicked)
        self.w_cut_csv160 = w_cut_csv160

        icol += 1
        w_ma_prcss = QPushButton('Process all', self)
        helpText = 'Aggregate to CSV then calculate Net CO2e and write to a raw,\n' + \
                   'that is a non-COARDS compliant, NetCDF file for all related simulations'
        w_ma_prcss.setToolTip(helpText)
        w_ma_prcss.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_ma_prcss, irow, icol)
        w_ma_prcss.clicked.connect(lambda: self.maProcessAll(True))

        # ==========
        irow += 1
        icol = 0
        w_lbl13 = QLabel('Management SV:')
        w_lbl13.setAlignment(Qt.AlignRight)
        w_lbl13.setToolTip('SV operations')
        grid.addWidget(w_lbl13, irow, icol)

        icol += 1
        w_chck_spec = QPushButton('Check spec results', self)
        helpText = 'Management version only e.g. simulation directories start with Reg_'
        w_chck_spec.setToolTip(helpText)
        w_chck_spec.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_chck_spec, irow, icol)
        w_chck_spec.clicked.connect(self.chckSpecRslts)

        icol += 1
        w_mgmt_prcs = QPushButton('MGMT process', self)
        helpText = 'Aggregate to CSV, Cut 200 years and write COARDS NCs for a single simulation starting with Reg_ or UK_'
        w_mgmt_prcs.setToolTip(helpText)
        w_mgmt_prcs.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_mgmt_prcs, irow, icol)
        w_mgmt_prcs.clicked.connect(self.mgmtProcess)

        icol += 1
        w_mgmt_prcs_all = QPushButton('MGMT process all', self)
        helpText = 'Aggregate to CSV, Cut 200 years and write COARDS NCs for multiple simulations starting with Reg_'
        w_mgmt_prcs_all.setToolTip(helpText)
        w_mgmt_prcs_all.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_mgmt_prcs_all, irow, icol)
        w_mgmt_prcs_all.clicked.connect(self.mgmtProcessAll)

        icol += 1
        w_clean_zip = QPushButton('Clean and Zip', self)
        helpText = 'Management version only e.g. simulation directories start with Reg_'
        w_clean_zip.setToolTip(helpText)
        w_clean_zip.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_clean_zip, irow, icol)
        w_clean_zip.clicked.connect(self.cleanZip)

        # ==========
        irow += 1
        w_save = QPushButton("Save")
        helpText = 'Save configuration file'
        w_save.setToolTip(helpText)
        w_save.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_save, irow, max_icol - 1)
        w_save.clicked.connect(self.saveClicked)

        w_exit = QPushButton('Exit', self)
        w_exit.setFixedWidth(STD_BTN_SIZE)
        grid.addWidget(w_exit, irow, max_icol)
        w_exit.clicked.connect(self.exitClicked)

        # add grid to RH vertical box
        rh_vbox.addLayout(grid)

        # vertical box goes into horizontal box
        hbox.addLayout(rh_vbox)

        # the horizontal box fits inside the window
        self.setLayout(hbox)

        # posx, posy, width, height
        # =========================
        self.setGeometry(300, 300, 650, 250)
        self.setWindowTitle('Write Global ECOSSE results to a NetCDF file')
        read_config_file(self)

    # ============= Unique operations ==========================
    #
    def aggregToCsvClicked(self):
        """

        """
        if read_study_definition(self):
            if aggreg_metrics_to_csv(self):

                # update to reflect aggregation result
                # ====================================
                descriptor, self.trans_defn = ecosse_results_files(self.w_lbl_rslts.text(),'Results: ')
                self.w_lbl06.setText(descriptor)
                check_cut_csv_files(self)
        return

    def cutCsvFilesClicked(self):
        """

        """
        cut_csv_files(self)
        return

    def cutCsvFiles1961Clicked(self):
        """

        """
        cut_str = '-f1-8,1929-3608'
        cut_csv_files(self, cut_str)
        return

    def csvDataToCO2eNcClicked(self):
        """

        """

        if read_study_definition(self):
            csv_to_co2e_netcdf(self)
        return

    def csvDataToRawNcClicked(self):
        """

        """
        if read_study_definition(self):
            csv_to_raw_netcdf(self)
        return

    # ============= General operations ==========================
    #
    def writeCoardsNcClicked(self):
        """

        """
        if read_study_definition(self):
            csv_to_coards_netcdf(self)
        return

    def writeNppClicked(self):
        """

        """
        if read_study_definition(self):
            sims_results_to_nc(self)
        return

    def writeSoilCsvClicked(self):
        """

        """
        if read_study_definition(self):
            aggregate_soil_data_to_csv(self)
        return

    # ============= MK operations ==========================
    #
    def trimSummaryFiles(self):
        """

        """
        if read_study_definition(self):
            trim_summaries(self)
        return

    def chckYears(self):
        """

        """
        pass

    def mkProcess(self):
        """

        """
        if not read_study_definition(self):
            return

        trim_summaries(self)
        self.aggregToCsvClicked()
        self.writeCoardsNcClicked()
        return

    # ============= MA operations ==========================
    #
    def maProcess(self):
        """

        """
        if not read_study_definition(self):
            return

        self.aggregToCsvClicked()
        csv_to_co2e_netcdf(self)
        return

    def maProcessAll(self, superg_flag):
        """

        """
        sims_dir = self.w_lbl_sims.text()
        root_dir, study = split(sims_dir)
        tmp_list = study.split('_')
        if superg_flag:
            search_str = '_'.join(tmp_list[:3]) + '_*'  # typical search_str:  'Anglesey_45_15_*'
            cut_str = '-f1-8,1929-3608'     # cut 160 years
        else:
            cut_str =  '-f1-8,2397-3608'    # cut 200 years
            search_str = '*' + tmp_list[-1] + '*'  # typical search_str:  'Wheat00A1B'

        study_defn_fns = []
        sim_dirs = []
        dirs = glob(root_dir + '\\' + search_str)
        for dirnm in dirs:
            if isdir(dirnm):
                sim_dirs.append(dirnm)
            else:
                # identify a study definition file
                # ================================
                if isfile(dirnm):
                    if dirnm.rfind('_study_definition') > 0:
                        study_defn_fns.append(dirnm)

        CO2E_ONLY_FLAG = False
        nstudies = len(sim_dirs)
        if nstudies > 0:
            for sim_dir, study_defn_fn in zip(sim_dirs, study_defn_fns):
                print('\nProcessing results in: ' + sim_dir)
                chng_study_create_co2e(self, sim_dir)
                if read_study_definition(self, study_defn_fn):

                    if not CO2E_ONLY_FLAG:
                        aggreg_metrics_to_csv(self, sim_dir)

                    aggreg_metrics_to_csv(self, sim_dir)
                    rslt_dir = sim_dir.replace('EcosseSims', 'EcosseOutputs')
                    descriptor, self.trans_defn = ecosse_results_files(rslt_dir, 'Results: ')

                    if CO2E_ONLY_FLAG:
                        rslts_dir = self.w_lbl_rslts.text()
                        out_dir = join(rslts_dir, 'cut_outdir')
                    else:
                        out_dir = cut_csv_files(self, cut_str)

                    descriptor, self.trans_defn = ecosse_results_files(out_dir, 'Results: ')
                    csv_to_co2e_netcdf(self)
        else:
            print('No studies found using search string: ' + search_str)

        return

    # ============= Management operations ==========================
    #
    def chckSpecRslts(self):
        """

        """
        check_spec_results(self)
        return

    def mgmtProcess(self):
        """

        """
        if not read_study_definition(self):
            return

        sims_dir = self.w_lbl_sims.text()
        if not isdir(sims_dir):
            print('Simulation directory: ' + sims_dir + ' does not exist')
        else:
            root_dir, reg_dir = split(sims_dir)
            if reg_dir.find('Reg_') == 0 or reg_dir.find('UK_') == 0:
                self.aggregToCsvClicked()
                cut_csv_files(self)
                self.writeCoardsNcClicked()
                print('Finished processing ' + reg_dir)
            else:
                print('Not a MGMT project')
        return

    def mgmtProcessAll(self):
        """

        """
        if not read_study_definition(self):
            return

        sims_dir = self.w_lbl_sims.text()
        root_dir, reg_dir = split(sims_dir)
        if reg_dir.find('Reg_') == 0:
            cmpnts = reg_dir.split('_')
            if len(cmpnts) >= 2:
                reg_str = cmpnts[0] + '_' + cmpnts[1]

                mgmt_dirs = []
                for fn in glob(join(root_dir, reg_str) + '*'):
                    if isdir(fn):
                        mgmt_dirs.append(fn)

                if len(mgmt_dirs) == 0:
                    print('No mgmt_dirs to process')
                else:
                    for mgmt_dir in mgmt_dirs:
                        print('Will process results in: ' + mgmt_dir)
                        aggregate_csv_create_coards(self, mgmt_dir)

        else:
            print('Not a MGMT project')

        return

    def cleanZip(self, mgmt_flag = True):
        """

        """
        if not read_study_definition(self):
            return

        rslts_dir = self.w_lbl_rslts.text()
        root_dir, reg_dir = split(rslts_dir)

        # put zip files here
        # ==================
        stage_dir = join(root_dir, 'staging area')
        if not isdir(stage_dir):
            mkdir(stage_dir)

        # fetch all directories
        # =====================
        dir_list = []
        if mgmt_flag:
            srch_str = 'Reg_*'
            for fn in glob(root_dir + '\\' + srch_str):
                if isdir(fn):
                    dir_list.append(fn)
        else:
            # only 2 scenarios
            # ================
            scenario = rslts_dir[-2:]
            if scenario != 'A2':
                scenario = 'A1B'

            for irun in range(0, 8):
                srch_str = '*Wheat0' + str(irun) + scenario + '\\cut_outdir'
                fns = glob(root_dir + '\\' + srch_str)
                for fn in fns:
                    if isdir(fn):
                        dir_list.append(fn)

                pass

        if len(dir_list) > 0:
            clean_and_zip(self, dir_list, stage_dir, mgmt_flag)
        else:
            print('Not a MGMT project - no regional directories e.g. ')

        return

    # ============= save and exit operations ==========================
    #
    def saveClicked(self):
        """

        """
        write_config_file(self)
        return

    def exitClicked(self):
        """

        """
        write_config_file(self)
        self.close()

    # ============= other ==========================
    #
    def fetchSimsDir(self):
        """
        select the directory under which the directories containing the ECOSSE simulation files are to be found
        """
        dirname = self.w_lbl_sims.text()
        dirname = QFileDialog.getExistingDirectory(self, 'Select simulations directory', dirname)
        if dirname != '':
            if isdir(dirname):
                self.w_lbl_sims.setText(normpath(dirname))
                change_create_rslts_dir(self)
                check_cut_csv_files(self)

        return

    def fetchRsltsDir(self):
        """

        """
        dialog = QFileDialog(self)
        dialog.ShowDirsOnly = False

        rslts_dir = self.w_lbl_rslts.text()
        rslts_dir = dialog.getExistingDirectory(self, 'Select directory containing the results', rslts_dir)

        if rslts_dir != '':
            rslts_dir = normpath(rslts_dir)
            self.w_lbl_rslts.setText(rslts_dir)

            descriptor, self.trans_defn = ecosse_results_files(rslts_dir, 'Contents: ')
            self.w_lbl06.setText(descriptor)
            check_cut_csv_files(self)

        return

# ============= entry point ==========================
#
def main():

    app = QApplication(sys.argv)  # create QApplication object
    form = Form()     # instantiate form
    form.show()       # paint form
    sys.exit(app.exec_())   # start event loop

if __name__ == '__main__':
    main()
