import os
import json
import time
from PySide2 import QtCore

class GetCollectionItems(QtCore.QObject):

    init_run = QtCore.Signal(str)

    start_process = QtCore.Signal(int)
    add_entry = QtCore.Signal(dict)
    end_process = QtCore.Signal()
    cancel_process = QtCore.Signal()

    def __init__(self):
        super(GetCollectionItems, self).__init__()
        
        self.cancel = False
        self.init_run.connect(self.run)

    @QtCore.Slot()
    def run(self, collection_folder):

        if not collection_folder or not os.path.exists(collection_folder):
            return
        self.cancel = False

        files = [f for f in os.listdir(collection_folder) if f.endswith(".json")]
        if self.cancel:
            self.cancel_process.emit()
            return

        if files:
            self.start_process.emit(len(files))

        for f in files:
            
            if self.cancel:
                self.cancel_process.emit()
                return

            with open(collection_folder + os.sep + f) as m:
                metadata = json.load(m)
            if self.cancel:
                self.cancel_process.emit()
                return

            self.add_entry.emit(metadata)

        self.end_process.emit()
