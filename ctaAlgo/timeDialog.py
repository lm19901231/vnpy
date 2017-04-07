
import sys
from PyQt4 import QtGui

class OrderConfirmDialog(QtGui.QDialog):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        button1 = QtGui.QPushButton(self)
        button2 = QtGui.QPushButton(self)
        text = QtGui.QLabel(self)
        text.setText("this is a order string")
        self.setGeometry(400, 400, 400, 200)
        self.status = 'empty'

        button1.setText("yes")
        button2.setText("No")
        button1.move(100, 150)
        button2.move(200, 150)
        button1.clicked.connect(self.showdialog1)
        button2.clicked.connect(self.showdialog2)
        self.setWindowTitle(u"Attention!!!")
        self.show()

    def showdialog1(self):
        self.status = 'yes'
        print 'yes'
        self.close()

    def showdialog2(self):
        self.status = 'no'
        print 'no'
        self.close()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    w = OrderConfirmDialog()
    w.show()
    print w.status
    sys.exit(app.exec_())
