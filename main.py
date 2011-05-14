#!/usr/bin/env python
# -*- coding: utf-8 -*-

import operator
import os
from binascii import hexlify
from argparse import ArgumentParser
from PySide.QtCore import *
from PySide.QtGui import *
from pywow import wdbc


def price(value):
	"""
	Helper for MoneyField
	TODO use pywow.game.items.price
	"""
	if not value:
		return 0, 0, 0
	g = divmod(value, 10000)[0]
	s = divmod(value, 100)[0] % 100
	c = value % 100
	return g, s, c


class WDBCClient(QApplication):
	name = "WDBC Reader"
	
	def __init__(self, argv):
		QApplication.__init__(self, argv)
		
		QTextCodec.setCodecForCStrings(QTextCodec.codecForName("UTF-8"))
		
		self.mainWindow = MainWindow()
		self.mainWindow.setWindowTitle(self.name)
		self.mainWindow.resize(1024, 768)
		self.mainWindow.setMinimumSize(640, 480)
		
		arguments = ArgumentParser(prog="wdbc")
		arguments.add_argument("-b", "--build", type=int, dest="build", default=0)
		arguments.add_argument("--get", action="store_true", dest="get", help="get from the environment")
		arguments.add_argument("files", nargs="+")
		args = arguments.parse_args(argv[1:])
		self.defaultBuild = args.build
		
		self.mainWindow.statusBar().showMessage("Ready")
		
		for name in args.files:
			if args.get:
				self.openByGet(name)
			else:
				self.open(name)
	
	def openByGet(self, path):
		self.mainWindow.addTab(wdbc.get(path, self.defaultBuild))
		self.mainWindow.setWindowTitle("%s - %s" % (path, self.name))
	
	def open(self, path):
		self.mainWindow.addTab(wdbc.fopen(path, self.defaultBuild))
		self.mainWindow.setWindowTitle("%s - %s" % (path, self.name))


class MainWindow(QMainWindow):
	def __init__(self, *args):
		QMainWindow.__init__(self, *args)
		
		self.__addMenus()
		self.__addToolbar()
		
		self.tabWidget = QTabWidget()
		self.tabWidget.setDocumentMode(True)
		self.tabWidget.setMovable(True)
		self.tabWidget.setTabsClosable(True)
		self.tabWidget.tabCloseRequested.connect(self.actionCloseTab)
		self.setCentralWidget(self.tabWidget)
	
	def __addMenus(self):
		def closeOrExit():
			index = self.tabWidget.currentIndex()
			if index == -1:
				self.close()
			else:
				self.actionCloseTab(index)
		
		fileMenu = self.menuBar().addMenu("&File")
		fileMenu.addAction(QIcon.fromTheme("document-open"), "&Open...", self.actionOpen, "Ctrl+O")
		fileMenu.addAction("Change &build", self.actionChangeBuild, "Ctrl+B")
		fileMenu.addAction(QIcon.fromTheme("document-open-recent"), "Open &Recent").setDisabled(True)
		fileMenu.addSeparator()
		fileMenu.addAction(QIcon.fromTheme("window-close"), "&Close", closeOrExit, "Ctrl+W")
		fileMenu.addSeparator()
		fileMenu.addAction(QIcon.fromTheme("application-exit"), "&Quit", self.close, "Ctrl+Q")
		
		helpMenu = self.menuBar().addMenu("&Help")
		helpMenu.addAction(QIcon.fromTheme("help-about"), "About")
	
	def __addToolbar(self):
		toolbar = self.addToolBar("Toolbar")
		toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		toolbar.addAction(QIcon.fromTheme("document-open"), "Open").triggered.connect(self.actionOpen)
		toolbar.addAction(QIcon.fromTheme("x-office-spreadsheet"), "Export").triggered.connect(self.actionExportData)
	
	def actionChangeBuild(self):
		file = self.currentModel().file
		current = file.build
		build, ok = QInputDialog.getInt(self, "Change build", "Build number", value=current, minValue=-1)
		if ok and build != current:
			self.currentModel().setFile(wdbc.fopen(file.file.name, build))
	
	def actionCloseTab(self, index):
		widget = self.tabWidget.widget(index)
		del widget.model().file
		del widget
		self.tabWidget.removeTab(index)
	
	def actionExportData(self):
		basename, _ = os.path.splitext(self.currentModel().file.file.name)
		filename, ok = QInputDialog.getText(self, "Choose a filename", "File name to export to", QLineEdit.Normal, "%s.csv" % (basename))
		if ok and filename:
			with open(filename, "w") as f:
				f.write(",".join(self.currentModel().rootData))
				f.write("\n")
				for row in self.currentModel().itemData:
					f.write(",".join(str(x) for x in row))
					f.write("\n")
	
	def actionOpen(self):
		filename, filters = QFileDialog.getOpenFileName(self, "Open file", "/var/www/sigrie/caches", "DBC/Cache files (*.dbc *.wdb *.db2 *.dba *.wcf)")
		if filename:
			file = wdbc.fopen(filename)
			self.addTab(file)
	
	def addTab(self, file):
		view = TableView()
		model = TableModel()
		model.setFile(file)
		view.setModel(model)
		view._m_model = model # BUG
		self.tabWidget.addTab(view, QIcon.fromTheme("x-office-spreadsheet"), os.path.basename(file.file.name))
	
	def currentModel(self):
		view = self.tabWidget.currentWidget()
		return view._m_model # BUG


class TableView(QTableView):
	def __init__(self, *args):
		QTableView.__init__(self, *args)
		self.setSortingEnabled(True)
		self.verticalHeader().setVisible(True)
		self.verticalHeader().setDefaultSectionSize(25)


class TableModel(QAbstractTableModel):
	def __init__(self, *args):
		QAbstractTableModel.__init__(self, *args)
		self.itemData = []
		self.rootData = []
	
	def columnCount(self, parent):
		return len(self.rootData)
	
	def data(self, index, role):
		if not index.isValid():
			return
		
		if role == Qt.DisplayRole:
			cell = self.itemData[index.row()][index.column()]
			field = self.structure[index.column()]
			
			if isinstance(field, wdbc.structures.HashField) or isinstance(field, wdbc.structures.DataField):
				cell = hexlify(cell)
			
			elif isinstance(field, wdbc.structures.BitMaskField):
				if cell is not None:
					cell = "0x%08x" % (cell)
			
			elif isinstance(field, wdbc.structures.MoneyField):
				gold, silver, copper = price(int(cell))
				
				gold = gold and "%ig" % (gold)
				silver = silver and "%is" % (silver)
				copper = copper and "%ic" % (copper)
				
				cell = " ".join(x for x in (gold, silver, copper) if x) or "0c"
			
			# Limit data within cells for performance reasons
			if isinstance(cell, str) and len(cell) > 200:
				cell = cell[:200] + "..."
			
			return cell
	
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return self.rootData[section]
		
		return QAbstractItemModel.headerData(self, section, orientation, role)
	
	def rowCount(self, parent=QModelIndex()):
		if parent.isValid():
			return 0
		return len(self.itemData)
	
	def setFile(self, file):
		self.layoutAboutToBeChanged.emit()
		self.file = file
		self.itemData = file.rows()
		self.rootData = file.structure.column_names
		self.structure = file.structure
		msg = "%i rows - Using %s build %i" % (self.rowCount(), file.structure, file.build)
		qApp.mainWindow.statusBar().showMessage(msg)
		self.layoutChanged.emit()
	
	def sort(self, column, order=Qt.AscendingOrder):
		self.layoutAboutToBeChanged.emit()
		self.itemData = sorted(self.itemData, key=operator.itemgetter(column))
		if order == Qt.AscendingOrder:
			self.itemData.reverse()
		self.layoutChanged.emit()


def main():
	import signal
	import sys
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	app = WDBCClient(sys.argv)
	
	app.mainWindow.show()
	sys.exit(app.exec_())

if __name__ == "__main__":
	main()
