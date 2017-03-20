
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *



class OrderConfirmDialog(QDialog):
    def __init__(self):
        QWidget.__init__(self)
        button1 = QPushButton(self)
        button2 = QPushButton(self)
        text = QLabel(self)
        text.setText("this is a order string")
        self.setGeometry(400, 400, 400, 200)

        button1.setText("yes")
        button2.setText("No")
        button1.move(100, 150)
        button2.move(200, 150)
        button1.clicked.connect(self.showdialog1)
        button2.clicked.connect(self.showdialog2)
        self.setWindowTitle(u"Attention!!!")
        self.show()

    def showdialog1(self):
        global a
        a = 'yes'
        self.close()
        return

    def showdialog2(self):
        # self.close()
        global a
        a = "no"
        self.close()
        return

if __name__ == "__main__":
    global a
    a = 0
    app = QApplication(sys.argv)
    w = OrderConfirmDialog()
    w.show()
    print a
    # sys.exit(app.exec_())
    app.exec_()
    print a