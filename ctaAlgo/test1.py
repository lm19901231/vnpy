# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 11:20:15 2017

@author: wxyc
"""

import time
from ctaBase import *
from vtConstant import *
from ctaTemplate import CtaTemplate
from uiBasicWidget import *


class Test1(CtaTemplate):
    """测试策略1"""
    signal = QtCore.pyqtSignal(type(Event()))
    className = 'Test1'
    author = u'lm'
    name = 'test1'  # 策略实例名称

    # 策略参数
    direction = u'买开'  # 合约操作方向，1买开，2卖平，3卖开，4买平
    countLimit = 1  # 子单次数限制，一个子单操作一个数量的合约，一个母单包含多个子单。
    count = EMPTY_INT
    volume = countLimit
    limitTime = 2
    signalStatus = False

    # 策略变量
    price = EMPTY_FLOAT
    pos = {}  # 持仓情况，支持多合约，使用dict结构存储
    req = {}  # 策略需求，用于风控检查，提前锁定资金

    orderDict = {}  # 保存委托变化推送


    #  参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'direction']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'price',
               'count',
               'countLimit']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(Test1, self).__init__(ctaEngine, setting)

        self.vtSymbol = self.vtSymbolList[0]

        self.status = False

        # 初始化持仓
        self.pos[self.vtSymbol] = 0

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'测试策略1初始化')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""

        self.writeCtaLog(u'进行策略风控检查')

        self.req = {}
        self.req[self.vtSymbol] = [self.direction, self.volume]
        self.writeCtaLog(u'策略需求为：%s,%s,%d' % (self.vtSymbol, self.direction, self.volume))

        # 提交风控检查，并返回结果
        state = self.requireCheck(self.req)
        if state:
            self.writeCtaLog(u'风控检查通过')
            self.writeCtaLog(u'测试策略1多合约展期启动')
            self.putEvent()
        else:
            self.writeCtaLog(u'风控检查未通过，策略禁止启动')
            self.putEvent()
        # state = True
        return state

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'测试策略1停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onPopup(self, popup):
        """弹窗结果返回"""
        print 000005
        self.status = popup.status
        print '5',self.status

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 记录最新价格
        if tick.vtSymbol == self.vtSymbol:
            # print time.strftime("%H:%M:%S"), tick.vtSymbol, tick.bidPrice1, tick.bidVolume1, tick.askPrice1, tick.askVolume1
            self.tickDict[self.vtSymbol] = [tick.bidPrice1, tick.askPrice1]

            print 1
            if not self.signalStatus:
                self.ctaEngine.popupRequire(tick.vtSymbol, self.name)
                self.signalStatus = True
            print self.status
        # while self.status == 'yes':
        #     print self.status
        #     print u'成功'
        #
        #
        # # 弹窗结果返回
        # print 000006
        # print self.status


        if self.trading:
            self.price = self.getPrice(self.vtSymbol, self.direction)
            # print self.price
            if self.count < self.countLimit:
                if self.price > 0:
                    # 弹窗请求
                    print 000001
                    # self.signal1.emit
                    # self.signal.connect(self.openPopup)
                    # self.signal.emit
                    # self.ctaEngine.popupRequire(tick.vtSymbol, self.name)

                    vtOrderID = self.sendOrder(self.direction, self.price, 1, self.vtSymbol, False)
                    print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                    if vtOrderID:
                        self.count += 1

            # 检查订单成交情况，如果超过1分钟未成交，先撤单，在下单
            for vtOrderID in self.orderDict:
                order = self.orderDict[vtOrderID]
                if order != 'Finished':
                    # 已成交，从字典中删除
                    if order.status == STATUS_ALLTRADED:
                        self.orderDict[vtOrderID] = 'Finished'  # 删除条目

                    # 已撤销，重新下单
                    elif order.status == STATUS_CANCELLED:
                        vtSymbol = order.vtSymbol
                        if vtSymbol == self.vtSymbol:
                            self.price = self.getPrice(self.vtSymbol, self.direction)
                            vtOrderID1 = self.sendOrder(self.direction, self.price, 1, self.vtSymbol, False)  # 卖出平仓  vtSymbol1
                            print self.vtSymbol, self.direction, self.price, vtOrderID1 , time.strftime("%H:%M:%S")

                            self.orderDict[vtOrderID] = 'Finished'  # 删除已撤销条目

                    # 未成交，未撤单，查看是否超时，若超时，撤单
                    else:
                        nowList = time.strftime("%H:%M:%S").split(":", 3)  # 当前时间
                        orderList = order.orderTime.split(":", 3)  # 下单时间
                        nowMinute = int(nowList[1])
                        nowSecond = int(nowList[2])
                        orderTimeMinute = int(orderList[1])
                        orderTimeSecond = int(orderList[2])
                        timeOut = (nowMinute * 60 + nowSecond) - (orderTimeMinute * 60 + orderTimeSecond) > self.limitTime  # 是否超时
                        print order.status, order.orderTime, 'timeOut', timeOut

                        # 如果超时，撤单
                        if timeOut:
                            print u'超时未成交，撤单', time.strftime("%H:%M:%S")
                            self.cancelOrder(vtOrderID)

        # 发出状态更新事件
        self.putEvent()


    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        self.orderDict[order.vtOrderID] = order


    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        vtOrderID = trade.vtOrderID

        print u'成交回报', time.strftime("%H:%M:%S")
        print 'vtSymbol', trade.vtSymbol, 'price', trade.price, 'tradeTime', trade.tradeTime, 'OrderID',trade.vtOrderID

    # ----------------------------------------------------------------------
    def openPopup(self, event=None):
        """打开弹窗"""

        # popup = event.dict_['data']
        # print 'popup', popup.require, popup.status
        # if popup.require:

        pp = OrderConfirmDialog()
        print 'pp.status', pp.status
        pp.show()
        # 等待弹窗赋值
        # popup.status = pp.status
        status = pp.status
        print status

        # while status != 'empty':
        #     # 结果返回
        #     print 000003
        #     self.ctaEngine.processPopup(popup)

########################################################################
class OrderConfirmDialog(QtGui.QDialog):
    """弹窗确认"""

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
        # self.show()

    def showdialog1(self):
        self.status = 'yes'
        print 'yes'
        self.ctaEngine.processPopup(self.status)
        self.close()

    def showdialog2(self):
        self.status = 'no'
        print 'no'
        self.ctaEngine.processPopup(self.status)
        self.close()














