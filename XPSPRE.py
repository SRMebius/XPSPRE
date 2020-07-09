#!/usr/bin/env python
#coding:utf-8
# =============================================================================
# First Created on 2020/4/23/9:31:02 PM
# @ author ZKY
# =============================================================================

__version__ = '3.1'

from functools import partial
from struct import pack

import pandas as pd
import numpy as np
from qtpy.QtCore import Qt
from PySide2.QtGui import QIcon
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QWidget, QVBoxLayout, QApplication, QMessageBox, QFileDialog, QLabel, QSizePolicy, QPushButton
from matplotlib import rc, cbook
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT, FigureCanvasQTAgg as FigureCanvas)

import resource
from normalization import Normalization


def RC_Initial():
    rc('font', family=['Times New Roman'], size=11)
    rc('axes', labelsize='xx-Large')
    rc('xtick', labelsize='Large', direction='in')
    rc('xtick.major', size=4)
    rc('xtick.minor', visible=True)
    rc('ytick', labelsize='Large', direction='in')
    rc('ytick.major', size=4)
    rc('legend', fontsize='xx-Large', frameon=False)
    
RC_Initial()


class NavigationToolbar(NavigationToolbar2QT):

    toolitems = (
        (None, None, None, None),
        ('Home', 'Reset original view', 'home', 'home'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        (None, None, None, None),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
        (None, None, None, None),
        )
    
    def _init_toolbar(self):
        self.basedir = str(cbook._get_data_path('images'))

        background_color = self.palette().color(self.backgroundRole())
        foreground_color = self.palette().color(self.foregroundRole())
        icon_color = (foreground_color
                      if background_color.value() < 128 else None)

        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.addSeparator()
            else:
                a = self.addAction(self._icon(image_file + '.png', icon_color),
                                   text, getattr(self, callback))
                self._actions[callback] = a
                if callback in ['zoom', 'pan']:
                    a.setCheckable(True)
                if tooltip_text is not None:
                    a.setToolTip(tooltip_text)
        a = self.addAction(self._icon("qt4_editor_options.png",icon_color),
                           'Customize', self.edit_parameters)
        a.setToolTip('Edit axis, curve and image parameters')

        if self.coordinates:
            self.locLabel = QLabel("", self)
            self.locLabel.setAlignment(Qt.AlignHCenter| Qt.AlignVCenter)
            self.locLabel.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored))
            labelAction = self.addWidget(self.locLabel)
            labelAction.setVisible(True) 
    
    def _update_buttons_checked(self):
        pass


class MplWidget(QWidget):
    
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)

        self.canvas = FigureCanvas(Figure())
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        vertical_layout = QVBoxLayout()
        vertical_layout.setSpacing(0)
        vertical_layout.addWidget(self.canvas)
        vertical_layout.addWidget(self.toolbar)

        self.setLayout(vertical_layout)


class Manipulation():

    def __init__(self):
        self.initial_data()
    
    def initial_data(self):
        self.Elements_Contents = None
        self.Full_Scan_BE = None
        self.Full_Scan_Intensity = None
        self.Fine_Scan_Elements = None 
        self.Fine_Scan_BE = {}
        self.Fine_Scan_Intensity = {}
        self.delta_BE = None

    def read_element_content(self, address):
        file = pd.read_table(address)
        elements = file.values[-2:][0][0].strip().split()
        contents = file.values[-2:][1][0].strip().split()
        self.Elements_Contents = dict(zip(elements, list(map(float, contents))))

    def read_full_scan(self, address):        
        file = pd.read_csv(address,
                           names = ['BE', 'Intensity'],
                           skiprows = 4)
        
        self.Full_Scan_BE = file['BE'].values
        self.Full_Scan_Intensity = file['Intensity'].values
        
    def read_fine_scan(self, address):
        file = pd.read_csv(address,
                           nrows = 3)
        
        self.Fine_Scan_Elements = file.values[1].tolist()[::2]
        
        name = [f'{element}_{suffix}' \
                for element in self.Fine_Scan_Elements \
                for suffix in ['BE', 'Intensity']]
        
        file = pd.read_csv(address,
                           names = name,
                           skiprows = 4)

        for element in self.Fine_Scan_Elements:
            self.Fine_Scan_BE[element] = file[f'{element}_BE'].values
            self.Fine_Scan_Intensity[element] = file[f'{element}_Intensity'].values
            
            nan_index = np.where(np.isnan(self.Fine_Scan_BE[element]))[0]
            self.Fine_Scan_BE[element] = np.delete(self.Fine_Scan_BE[element], nan_index, axis=0)
            self.Fine_Scan_Intensity[element] = np.delete(self.Fine_Scan_Intensity[element], nan_index, axis=0)
    
    def Elements_Contents_Update(self):
        if len(self.Fine_Scan_Elements) > len(self.Elements_Contents):
            elements = list(set(self.Fine_Scan_Elements).difference(set(self.Elements_Contents)))
            for element in elements:
                self.Elements_Contents[element] = 0
    
    def calibrate_BE(self):
        for element in self.Fine_Scan_BE:
            for i in range(len(self.Fine_Scan_BE[element])):
                self.Fine_Scan_BE[element][i] += self.delta_BE 

    def check_files(self, file_names, file_address):
        correct_file_names = [f'{file_address}N-a.txt', f'{file_address}S-a.csv', f'{file_address}N-a.csv']
        
        if len(file_names) == 3 and set(file_names).difference(set(correct_file_names)) == set():
            self.initial_data()
            self.read_element_content(correct_file_names[0])
            self.read_full_scan(correct_file_names[1])
            self.read_fine_scan(correct_file_names[2])
            self.Elements_Contents_Update()
            self.delta_BE = 0.0
            return True
        else:
            return False
    
    def calculate_atomic_ratio(self, element_1, element_2):
        content_1 = self.Elements_Contents[element_1]
        content_2 = self.Elements_Contents[element_2]
        return f'{(content_1/content_2):.2f}'
    
    def save_txt(self, address):
        for element in self.Fine_Scan_Elements:
            np.savetxt(f'{address}{element}.txt',
                       np.column_stack((self.Fine_Scan_BE[element], self.Fine_Scan_Intensity[element])),
                       fmt = '%f')
    
    def save_xps(self, path):
        s = b''
        num = len(self.Fine_Scan_Elements)
        
        for element in self.Fine_Scan_Elements:
            points = len(self.Fine_Scan_BE[element])
            bin_points = pack('h', points)
            bin_points_ = pack('h', points+1)
            
            bin_BE = [pack('f', BE) for BE in self.Fine_Scan_BE[element]]
            bin_Intensity = [pack('f', Intensity) for Intensity in self.Fine_Scan_Intensity[element]]
            bin_tail = pack('4f', np.max(self.Fine_Scan_BE[element]), np.min(self.Fine_Scan_BE[element]),
                            np.max(self.Fine_Scan_Intensity[element]), np.min(self.Fine_Scan_Intensity[element]))
            
            s += b'\x44\x50' + bin_points + b'\xff\xff\x00\x00' + b'\x20'*20 + bin_points + \
            b'\x01\x00' + bin_points_ + b'\x00'*10 + b''.join(bin_BE) + \
            b'\x01\x00' + bin_points_ + b'\x00'*10 + b''.join(bin_Intensity) + bin_tail + b'\x00'*60 + \
            (b'\x01\x00' + bin_points_ + b'\x00'*10 + b'\x00'*points*4)*6 + b'\x00' * 18
        
        s = b'\x58\x50\x53\x50\x45\x41\x4b\x20\x34\x2e\x30' + s + \
        b'\x44\x41'*(61-num) + b'\x00'*80  + b'\x08\x00\x00\x00'
        
        with open(path, 'wb') as f:
            f.write(s)


class CalculatorWindow():
    
    def __init__(self):
        self.ui_calculator = QUiLoader().load('UIs/calculator.ui')
        self.setButtonConnect()
        self.ui_calculator.show()
        
    def setButtonConnect(self):
        btn_list = self.ui_calculator.findChildren(QPushButton)        
        for btn in btn_list:
            if btn.text() == 'C':
                btn.clicked.connect(self.clear)
            elif btn.text() == '<':
                btn.clicked.connect(self.backspace)
            elif btn.text() == '=':
                btn.clicked.connect(self.calculate)
            else:
                btn.clicked.connect(partial(self.express, btn.text()))
    
    def clear(self):
        self.ui_calculator.lineEdit.clear()
        self.expression = ''
    
    def backspace(self):
        self.expression = self.expression[:-1]
        self.ui_calculator.lineEdit.setText(self.expression)
    
    def calculate(self):
        try:
            value = eval(self.expression)
        except (SyntaxError, AttributeError):
            value = None
        else:
            self.ui_calculator.lineEdit.setText(f'{value}')
            self.ui_calculator.textBrowser.append(f'{self.expression} = {value}\n')
            self.expression = ''
    
    def express(self, s):
        self.expression = self.ui_calculator.lineEdit.text() + s
        self.ui_calculator.lineEdit.setText(self.expression)


class ComparationWindow():
    
    def __init__(self):
        self.Nor = Normalization()
        self.sample_names = []
        self.all_data = pd.DataFrame()
        
        loader = QUiLoader()
        loader.registerCustomWidget(MplWidget)
        self.ui_comparation = loader.load('UIs/comparation.ui')
       
        self.ui_comparation.widget.canvas.axes = self.ui_comparation.widget.canvas.figure.add_axes([0.12,0.12,0.8,0.8])
        
        self.set_ui_comparation_connect()
        self.ui_comparation.show()
    
    def set_ui_comparation_connect(self):
        self.ui_comparation.toolButton_1.clicked.connect(self.openFile_dialog)
        self.ui_comparation.toolButton_2.clicked.connect(self.undo_nor)
        self.ui_comparation.pushButton_1.clicked.connect(self.add_plot)
        self.ui_comparation.pushButton_2.clicked.connect(self.remove_plot)
        self.ui_comparation.pushButton_3.clicked.connect(self.clear_plot)
        self.ui_comparation.pushButton_4.clicked.connect(self.save_to_cp)
        self.ui_comparation.radioButton_1.clicked.connect(partial(self.nor, 1))
        self.ui_comparation.radioButton_2.clicked.connect(partial(self.nor, 2))
        self.ui_comparation.radioButton_3.clicked.connect(partial(self.nor, 3))
        self.ui_comparation.radioButton_4.clicked.connect(partial(self.nor, 4))
    
    def openFile_dialog(self):
        self.file_path, _ = QFileDialog.getOpenFileName(self.ui_comparation,
                                                        'Select the Element Spectrum to open',
                                                        filter='Data files (*.txt *.csv *.cp)')
        self.ui_comparation.lineEdit_1.setText(self.file_path)
        
        if self.file_path.endswith('.cp'):
            self.all_data = pd.read_pickle(self.file_path)
            self.sample_names = [name.split('_')[0] for name in self.all_data.columns[::2]]
            self.recover_plot()
    
    def recover_plot(self):
        self.ui_comparation.widget.canvas.axes.clear()
        for i in range(0, len(self.sample_names)):
            self.plot(self.all_data.iloc[:,2*i],
                      self.all_data.iloc[:,2*i+1],
                      self.sample_names[i])
    
    def nor_plot(self, df):
        self.ui_comparation.widget.canvas.axes.clear()
        for sample_name in self.sample_names:
            self.plot(df[f'{sample_name}_BE'], df[f'{sample_name}_Intensity'], sample_name)
        
    def nor(self, m):
        df = self.all_data.copy()
        try:
            x1 = float(self.ui_comparation.lineEdit_3.text())
            x2 = float(self.ui_comparation.lineEdit_4.text())
        except ValueError:
            pass
        else:
            if m == 4:
                for sample_name in self.sample_names:
                    df[f'{sample_name}_Intensity'] = self.Nor.method_4(df[[f'{sample_name}_BE', f'{sample_name}_Intensity']], x1, x2)
        finally:
            if m == 1:
                for sample_name in self.sample_names:
                    df[f'{sample_name}_Intensity'] = self.Nor.method_1(df[f'{sample_name}_Intensity'])
            elif m == 2:
                for sample_name in self.sample_names:
                    df[f'{sample_name}_Intensity'] = self.Nor.method_2(df[f'{sample_name}_Intensity'])
            elif m ==3:
                for sample_name in self.sample_names:
                    df[f'{sample_name}_Intensity'] = self.Nor.method_3(df[f'{sample_name}_Intensity'])
            self.nor_plot(df)
        
    def undo_nor(self):
        self.nor_plot(self.all_data)
    
    def plot(self, x, y, label):
        self.ui_comparation.widget.canvas.axes.plot(x, y, label=label)
        self.ui_comparation.widget.canvas.axes.set_xlabel('B.E. (eV)')
        self.ui_comparation.widget.canvas.axes.set_ylabel('Intensity (a.u.)')
        self.ui_comparation.widget.canvas.axes.legend()
        self.ui_comparation.widget.canvas.draw()
        
    def add_plot(self):
        sample_name = self.ui_comparation.lineEdit_2.text()
        
        if sample_name not in [' '*i for i in range(10)] and sample_name not in self.sample_names:
            try:
                if self.file_path.endswith('.csv'):
                    data = pd.read_csv(self.file_path,
                                       names = [f'{sample_name}_BE', f'{sample_name}_Intensity'],
                                       skiprows = 4)
                elif self.file_path.endswith('.txt'):
                    data = pd.read_csv(self.file_path,
                                        sep = ' ',
                                        names = [f'{sample_name}_BE', f'{sample_name}_Intensity'])                
            except Exception:
                pass
            else:
                self.plot(data[f'{sample_name}_BE'],
                          data[f'{sample_name}_Intensity'],
                          sample_name)
    
                self.ui_comparation.lineEdit_2.setText('')
                self.sample_names.append(sample_name)
                self.all_data = pd.concat([self.all_data, data], axis = 1)
    
    def remove_plot(self):
        sample_name = self.ui_comparation.lineEdit_2.text()
        
        if sample_name in self.sample_names:
            self.ui_comparation.widget.canvas.axes.lines[self.sample_names.index(sample_name)].remove()
            self.ui_comparation.widget.canvas.axes.legend()
            self.ui_comparation.widget.canvas.draw()
        
            self.ui_comparation.lineEdit_2.setText('')
            self.sample_names.remove(sample_name)
            self.all_data = self.all_data.drop([f'{sample_name}_BE', f'{sample_name}_Intensity'], axis = 1)
        
    def clear_plot(self):
        self.ui_comparation.widget.canvas.axes.clear()
        self.ui_comparation.widget.canvas.draw()
        
        self.sample_names = []
        self.all_data = pd.DataFrame()
    
    def save_to_cp(self):
        if len( self.all_data) != 0:
            path, _ = QFileDialog.getSaveFileName(self.ui_comparation,
                                                  'Save',
                                                  filter='Data files (*.cp)')
            if path.endswith('.cp'):
                self.all_data.to_pickle(path)
                QMessageBox.information(self.ui_comparation,
                                        'INFO',
                                        'File saved.')


class RetrieveWindow():

    def __init__(self):
        self.ui_retrieve = QUiLoader().load('UIs/PTE.ui')
        self.ui_retrieve.show()


class HelperWindow():
    
    def __init__(self):
        self.ui_helper = QUiLoader().load('UIs/helper.ui')
        self.ui_helper.treeWidget.itemSelectionChanged.connect(self.display)
        self.ui_helper.show()
    
    def display(self):
        item_list = ['Preface', 'Import', 'Element Spectrum', 'XPS File', \
                     'Calibration', 'Atomic Ratio', 'ViewALL', 'Calculator', \
                     'Comparation', 'Retrieve', 'Navigation Toolbar', 'Updata log']
        item = self.ui_helper.treeWidget.currentItem().text(0)
        if item != 'Export':
            self.ui_helper.stackedWidget.setCurrentIndex(item_list.index(item))
        

class AboutWindow():

    def __init__(self):
        self.ui_about = QUiLoader().load('UIs/about.ui')
        self.ui_about.show()


class ViewALLWindow():
    
    def __init__(self):
        
        loader = QUiLoader()
        loader.registerCustomWidget(MplWidget)
        self.ui_viewall = loader.load('UIs/viewall.ui')
        self.ui_viewall.show()


class MainWindow():
    
    def __init__(self):
        self.Manip = Manipulation()
        
        loader = QUiLoader()
        loader.registerCustomWidget(MplWidget)
        self.ui = loader.load('UIs/main.ui')
        
        self.ui.MplWidget.canvas.axes = self.ui.MplWidget.canvas.figure.add_axes([0.16, 0.15, 0.77, 0.77])
        
        self.set_ui_connect()
        self.ui.show()
        
    def set_ui_connect(self):
        self.ui.listWidget.itemClicked.connect(self.draw)
        
        self.ui.comboBox_1.currentIndexChanged.connect(self.lineedit_3)
        self.ui.comboBox_2.currentIndexChanged.connect(self.lineedit_3)
        
        self.ui.toolButton.clicked.connect(self.run_calibrate)
        
        self.ui.pushButton.clicked.connect(self.viewall)

        self.ui.actionImport_Files.triggered.connect(self.import_files)
        
        self.ui.actionElement_spectrum.triggered.connect(self.export_spectra_files)
        self.ui.actionXPS_File.triggered.connect(self.export_xpsfile)
        
        self.ui.actionExit.triggered.connect(self.exit)
                
        self.ui.actionCalculator.triggered.connect(self.calculator)
        
        self.ui.actionComparation.triggered.connect(self.comparation)
        
        self.ui.actionRetrieve.triggered.connect(self.retrieve)
        
        self.ui.actionHelp_Contents.triggered.connect(self.helper)
        self.ui.actionAbout_XPSPRE.triggered.connect(self.about)
        
    def clear_ui_contents(self):
        self.ui.listWidget.clear()
        self.ui.comboBox_1.clear()
        self.ui.comboBox_2.clear()
        self.ui.lineEdit_1.clear()
        self.ui.lineEdit_2.clear()
        self.ui.lineEdit_3.clear()
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.draw()
        try:
            self.vie.ui_viewall.close()
        except AttributeError:
            pass
        
    def lineedit_3(self):
        element_1 = self.ui.comboBox_1.currentText()
        element_2 = self.ui.comboBox_2.currentText()
        try:
            atomic_ratio = self.Manip.calculate_atomic_ratio(element_1, element_2)
        except (KeyError, ZeroDivisionError):
            atomic_ratio = 'NAN'
        finally:
            self.ui.lineEdit_3.setText(atomic_ratio)
        
    def listwidget(self, Elements_Contents):
        for element, content in Elements_Contents.items():
            self.ui.listWidget.addItem(f'{element}      {content}%')
    
    def lineedit_1(self, elements):
        if 'C1s' in elements:
            self.ui.lineEdit_1.setText('284.50')
    
    def comobox(self, elements):
        self.ui.comboBox_1.addItems(elements)
        self.ui.comboBox_2.addItems(elements)
    
    def import_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(self.ui,
                                                    'Select the three files to open',
                                                    filter='Data files (N-a.csv N-a.txt S-a.csv)')
        if len(file_names) != 0:
            self.file_address = file_names[0][:-7]
            
            if self.Manip.check_files(file_names, self.file_address) == True:
                self.clear_ui_contents()
                QMessageBox.information(self.ui,
                                        'INFO',
                                        'Files imported.')
                self.listwidget(self.Manip.Elements_Contents)
                self.lineedit_1(self.Manip.Elements_Contents.keys())
                self.comobox(self.Manip.Elements_Contents.keys())
            else:
                QMessageBox.warning(self.ui,
                                    'ERROR',
                                    'Please select the three files correctly !\nElement Content (.txt)\nFine Scan (.csv)\nFull Scan (.csv)')

    def export_spectra_files(self):
        if self.Manip.delta_BE == 0.0:
            if QMessageBox.question(self.ui,
                                    'Warning',
                                    'You have not calibrate the data yet\nAre you sure to export the .txt files?',
                                    QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                self.Manip.save_txt(self.file_address)
                QMessageBox.information(self.ui,
                                    'INFO',
                                    'Spectra files have been exported in .txt format for each element.')
        elif self.Manip.delta_BE != None:
            self.Manip.save_txt(self.file_address)
            QMessageBox.information(self.ui,
                                    'INFO',
                                    'Spectra files have been exported in .txt format for each element.')

    def export_xpsfile(self):
        if self.Manip.delta_BE == 0.0:
            if QMessageBox.question(self.ui,
                                    'Warning',
                                    'You have not calibrate the data yet\nAre you sure to export the .xps file?',
                                    QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                path, _ = QFileDialog.getSaveFileName(self.ui,
                                                      'Save',
                                                      filter='Data files (*.xps)')
                if path.endswith('.xps'):
                    self.Manip.save_xps(path)
                    QMessageBox.information(self.ui,
                                        'INFO',
                                        'Spectra files have been exported in .xps format.')
        elif self.Manip.delta_BE != None:
            path, _ = QFileDialog.getSaveFileName(self.ui,
                                                  'Save',
                                                  filter='Data files (*.xps)')
            if path.endswith('.xps'):
                self.Manip.save_xps(path)
                QMessageBox.information(self.ui,
                                        'INFO',
                                        'Spectra files have been exported in .xps format.')
    
    def run_calibrate(self):
#     '''
#     利用self.Fine_Scan_Elements判断是否已经导入数据，
#     若未导入则run_calibrate调用无效，self.Manip.delta_BE = None
#     若已导入但run_calibrate调用失败，self.Manip.delta_BE = 0.0（由导入时调用的check_files赋值）
#     若已导入且run_calibrate调用成功，self.Manip.delta_BE = 结合能差值
#     '''
        if self.Manip.Fine_Scan_Elements != None:
            Standard_BE = self.ui.lineEdit_1.text()
            Measured_BE = self.ui.lineEdit_2.text()
    
            try:
                self.Manip.delta_BE = float(Standard_BE) - float(Measured_BE)
            except ValueError:
                pass
            else:
                self.Manip.calibrate_BE()
                QMessageBox.information(self.ui,
                                        'INFO',
                                        'Calibration finished.')
                self.ui.MplWidget.canvas.axes.clear()
                self.draw()           
        
    def draw(self):
        
        def update_annotation(index):
            annotation.xy = (x[index], y[index])
            annotation.set_text(f'(x={x[index]}, y={y[index]})')

        def on_pick(event):
            index = event.ind
            update_annotation(index[0])
            annotation.set_visible(True)
            self.ui.lineEdit_2.setText(str(x[index[0]]))
            self.ui.MplWidget.canvas.draw_idle()

        selected_element = self.ui.listWidget.currentItem().text().split('      ')[0]
        x = self.Manip.Fine_Scan_BE[selected_element]
        y = self.Manip.Fine_Scan_Intensity[selected_element]
        
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.plot(x, y, label=selected_element)
        self.ui.MplWidget.canvas.axes.scatter(x, y, picker = True, pickradius = 3)
        self.ui.MplWidget.canvas.axes.set_xlabel('B.E. (eV)')
        self.ui.MplWidget.canvas.axes.set_ylabel('Intensity (a.u.)')
        self.ui.MplWidget.canvas.axes.invert_xaxis()
        self.ui.MplWidget.canvas.axes.legend()
     
        annotation = self.ui.MplWidget.canvas.axes.annotate('', xy = (0,0), xytext = (10,10), textcoords="offset points")
        annotation.set_visible(False)
        self.ui.MplWidget.canvas.mpl_connect('pick_event', on_pick)

        self.ui.MplWidget.canvas.draw()
        
    def viewall(self):
        try:
            self.vie.ui_viewall.close()
        except AttributeError:
            pass
        finally:
            self.vie = ViewALLWindow()

        styles = {1:231, 2:231, 3:231, 4:331, 5:331, 6:331, 7:431, 8:431, 9:431}
        try:
            n = len(self.Manip.Fine_Scan_Elements)
        except TypeError:
            pass
        else:
            if n <= 9:
                style = styles[n]
            else:
                style = 111
            for i in range(n):
                x = self.Manip.Fine_Scan_BE[self.Manip.Fine_Scan_Elements[i]]
                y = self.Manip.Fine_Scan_Intensity[self.Manip.Fine_Scan_Elements[i]]
                ax = self.vie.ui_viewall.widget.canvas.figure.add_subplot(style+i)
                ax.plot(x, y, label=self.Manip.Fine_Scan_Elements[i], c='black')
                ax.invert_xaxis()
                ax.legend()
     
            ax = self.vie.ui_viewall.widget.canvas.figure.add_subplot((style//100) * 100 + 10 + (style//100))
            ax.plot(self.Manip.Full_Scan_BE, self.Manip.Full_Scan_Intensity, label='Full Scan', c='black')
            ax.invert_xaxis()
            ax.set_xlabel('B.E. (eV)')
            ax.legend()
            
            self.vie.ui_viewall.widget.canvas.draw()
    
    def calculator(self):
        try:
            self.cal.ui_calculator.close()
        except AttributeError:
            pass
        finally:
            self.cal = CalculatorWindow()
    
    def comparation(self):
        try:
            self.com.ui_comparation.close()
        except AttributeError:
            pass
        finally:
            self.com = ComparationWindow()
    
    def retrieve(self):
        try:
            self.ret.ui_retrieve.close()
        except AttributeError:
            pass
        finally:
            self.ret = RetrieveWindow()

    def helper(self):
        self.hel = HelperWindow()
        
    def about(self):
        self.abo = AboutWindow()
        
    def exit(self):
        if QMessageBox.question(self.ui,
                                'Warning',
                                'Sure to quit?',
                                QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:app.quit()  


if __name__  == '__main__':
    app = QApplication([])
    app.setWindowIcon(QIcon('window.png'))
#     app.setStyle('fusion')
    Main = MainWindow()
    app.exec_()
