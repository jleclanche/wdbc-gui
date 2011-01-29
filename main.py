#!/usr/bin/env python
# -*- coding: utf-8 -*-

import operator
import os
from binascii import hexlify
from optparse import OptionParser
from PySide.QtCore import *
from PySide.QtGui import *
from pywow import wdbc


class WDBCClient(QApplication):
	name = "WDBC Reader"
	
	def __init__(self, argv):
		QApplication.__init__(self, argv)
		
		QTextCodec.setCodecForCStrings(QTextCodec.codecForName("UTF-8"))
		
		self.mainWindow = MainWindow()
		self.mainWindow.setWindowTitle(self.name)
		self.mainWindow.resize(1024, 768)
		self.mainWindow.setMinimumSize(640, 480)
		
		arguments = OptionParser()
		arguments.add_option("-b", "--build", type="int", dest="build", default=0)
		arguments.add_option("--get", action="store_true", dest="get", help="get from the environment")
		
		args, files = arguments.parse_args(argv[1:])
		
		self.defaultBuild = args.build
		
		for name in files:
			if args.get:
				self.get(path)
			else:
				file = wdbc.fopen(name, args.build)
			
			self.mainWindow.setFile(file)
	
	def get(self, path):
		f = wdbc.get(path, self.defaultBuild)
		self.mainWindow.model.setFile(f)
		self.mainWindow.setWindowTitle("%s - %s" % (path, self.name))
	
	def open(self, path):
		f = wdbc.fopen(path, self.defaultBuild)
		self.mainWindow.model.setFile(f)
		self.mainWindow.setWindowTitle("%s - %s" % (path, self.name))

class MainWindow(QMainWindow):
	def __init__(self, *args):
		QMainWindow.__init__(self, *args)
		
		self.__addMenus()
		self.__addToolbar()
		
		centralWidget = QWidget(self)
		self.setCentralWidget(centralWidget)
		
		verticalLayout = QVBoxLayout(centralWidget)
		self.mainTable = MainTable(centralWidget)
		tabWidget = QTabWidget()
		tabWidget.setDocumentMode(True)
		tabWidget.setMovable(True)
		tabWidget.addTab(self.mainTable, "Untitled")
		verticalLayout.addWidget(tabWidget)
	
	def __addMenus(self):
		fileMenu = self.menuBar().addMenu("&File")
		fileMenu.addAction(QIcon.fromTheme("document-open"), "&Open...", self.actionOpen, "Ctrl+O")
		fileMenu.addAction("Change &build", self.actionChangeBuild, "Ctrl+B")
		fileMenu.addAction(QIcon.fromTheme("document-open-recent"), "Open &Recent").setDisabled(True)
		fileMenu.addSeparator()
		fileMenu.addAction(QIcon.fromTheme("window-close"), "&Close", lambda: None, "Ctrl-W")
		fileMenu.addSeparator()
		fileMenu.addAction(QIcon.fromTheme("application-exit"), "&Quit", self.close, "Ctrl+Q")
		
		helpMenu = self.menuBar().addMenu("&Help")
		helpMenu.addAction(QIcon.fromTheme("help-about"), "About")
	
	def __addToolbar(self):
		toolbar = self.addToolBar("Toolbar")
		toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		toolbar.addAction(QIcon.fromTheme("document-open"), "Open").triggered.connect(self.actionOpen)
	
	def actionChangeBuild(self):
		current = self.file.build
		build, ok = QInputDialog.getInt(self, "Change build", "Build number", value=current, minValue=-1)
		if ok and build != current:
			file = wdbc.fopen(self.file.file.name, build)
			self.setFile(file)
	
	def actionOpen(self):
		filename, filters = QFileDialog.getOpenFileName(self, "Open file", "/var/www/sigrie/caches", "DBC/Cache files (*.dbc *.wdb *.db2 *.dba *.wcf)")
		if filename:
			file = wdbc.fopen(filename)
			self.setFile(file)
	
	def setFile(self, file):
		self.file = file
		self.mainTable.model().setFile(file)
		msg = "%i rows - Using %s build %i" % (self.mainTable.model().rowCount(), file.structure, file.build)
		self.statusBar().showMessage(msg)


class MainTable(QTableView):
	def __init__(self, *args):
		QTableView.__init__(self, *args)
		
		self.setModel(TableModel(self))
		self.verticalHeader().setVisible(True)
		self.setSortingEnabled(True)
		self.verticalHeader().setDefaultSectionSize(25)

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
		self.emit(SIGNAL("layoutAboutToBeChanged()"))
		self.itemData = file.rows()
		self.rootData = file.structure.column_names
		self.structure = file.structure
		self.emit(SIGNAL("layoutChanged()"))

	def sort(self, column, order):
		self.emit(SIGNAL("layoutAboutToBeChanged()"))
		self.itemData = sorted(self.itemData, key=operator.itemgetter(column))
		if order == Qt.AscendingOrder:
			self.itemData.reverse()
		self.emit(SIGNAL("layoutChanged()"))


def main():
	import signal
	import sys
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	app = WDBCClient(sys.argv)
	
	app.mainWindow.show()
	sys.exit(app.exec_())

if __name__ == "__main__":
	main()
