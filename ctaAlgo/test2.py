# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 11:20:15 2017

@author: wxyc
"""
import time
import sys
from PyQt4.QtGui import *

from Tkinter import *
from ctaBase import *
# from vtGateway import *
from ctaTemplate import CtaTemplate
from vtConstant import *
from timeDialog import OrderConfirmDialog


class Test2(CtaTemplate):
    """测试策略2多合约展期"""

    className = 'Test2'
    author = u'lm'
    name = 'test2'  # 策略实例名称

    # **********************************************************************
    # 策略参数
    spreadLimit = 66         # 展期价差
    direction = -1           # 方向，1大于，-1小于
    direction1 = u'卖平'     # 合约1操作方向，1买开，2卖平，3卖开，4买平
    direction2 = u'买平'     # 合约2操作方向，1买开，2卖平，3卖开，4买平
    countLimit = 4           # 子单次数限制，一个子单操作一个数量的合约，一个母单包含多个子单。
    volume1 = countLimit     # 合约1数量
    volume2 = countLimit     # 合约2数量
    limitTime = 1            # 超时限制时间（秒）

    # **********************************************************************

    # 策略变量
    vtSymbol1 = EMPTY_STRING  # 交易的合约vt系统代码
    vtSymbol2 = EMPTY_STRING  # 交易的合约vt系统代码
    # vtSymbolList = []
    wait = 1
    price1 = EMPTY_FLOAT       # 合约1最新成交价
    price2 = EMPTY_FLOAT       # 合约2最新成交价
    count = EMPTY_INT          # 展期次数
    spreadRt = EMPTY_FLOAT     # 实时价差
    vtOrderID1 = EMPTY_STRING
    vtOrderID2 = EMPTY_STRING
    pos = {}  # 持仓情况，支持多合约，使用dict结构存储
    req = {}  # 策略需求，用于风控检查，提前锁定资金

    orderDict = {}  # 保存委托变化推送

    # 成交订单字典
    completeOrderDict = {}


    # K线字典
    bar = {}
    barMinute = {}
    lasttick = {}

    #  参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol1',
                 'direction1',
                 'vtSymbol2',
                 'direction2',
                 'spreadLimit',
                 'spreadRt']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'price1',
               'price2',
               'count',
               'countLimit']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(Test2, self).__init__(ctaEngine, setting)

        self.vtSymbol1 = self.vtSymbolList[0]
        self.vtSymbol2 = self.vtSymbolList[1]
        # 初始化持仓
        self.pos[self.vtSymbol1] = 0
        self.pos[self.vtSymbol2] = 0

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'测试策略2多合约展期初始化')

        # 读取UI界面输入的参数值


        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""

        # 确定操作所需的合约，进行风控检查，提前锁定仓位和资金
        self.writeCtaLog(u'进行策略风控检查')

        self.req = {}
        self.req[self.vtSymbol1] = [self.direction1, self.volume1]
        self.req[self.vtSymbol2] = [self.direction2, self.volume2]
        self.writeCtaLog(u'策略需求为：\n%s,%s,%d\n%s,%s,%d' % (self.vtSymbol1, self.direction1, self.volume1, self.vtSymbol2, self.direction2, self.volume2))

        # 提交风控检查，并返回结果
        state = self.requireCheck(self.req)
        if state:
            self.writeCtaLog(u'风控检查通过')
            self.writeCtaLog(u'测试策略2多合约展期启动')
            self.putEvent()
        else:
            self.writeCtaLog(u'风控检查未通过，策略禁止启动')
            self.putEvent()
        # state = True
        return state


    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""

        # 未成交需求进行释放


        self.writeCtaLog(u'测试策略2多合约展期停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        # 记录最新价格
        if tick.vtSymbol == self.vtSymbol1:
            # print time.strftime("%H:%M:%S"), tick.vtSymbol, tick.bidPrice1, tick.bidVolume1, tick.askPrice1, tick.askVolume1
            self.tickDict[self.vtSymbol1] = [tick.bidPrice1, tick.askPrice1]
            # self.price1 = tick.bidPrice1
        if tick.vtSymbol == self.vtSymbol2:
            self.tickDict[self.vtSymbol2] = [tick.bidPrice1, tick.askPrice1]
            self.price2 = tick.askPrice1

        # print time.strftime("%H:%M:%S"), tick.vtSymbol, tick.lastPrice
        # print 'posBufferDict', self.ctaEngine.posBufferDict


        try:
            self.price1 = self.getPrice(self.vtSymbol1, self.direction1)
            self.price2 = self.getPrice(self.vtSymbol2, self.direction2)
            self.spreadRt = abs(self.price1 - self.price2)  # 实时价差
            # print time.strftime("%H:%M:%S"), self.spreadRt
            if self.trading:
                if (self.direction == 1 and self.spreadRt >= self.spreadLimit) or (self.direction == -1 and self.spreadRt <= self.spreadLimit):
                    if abs(self.pos[self.vtSymbol1]) < self.countLimit and abs(self.pos[self.vtSymbol2]) < self.countLimit and self.count < self.countLimit:
                        # 弹窗确认模块
                        # global t
                        # global root
                        #
                        # root = Tk()
                        # root.title("hello world")
                        # root.geometry('300x200')
                        #
                        # t = None
                        #
                        # l = Label(root, text=u"弹窗确认模块", font=("Arial", 12))
                        # l.pack(side=TOP)
                        #
                        # Button(root, text="Yes", command = self.yes).pack(side=LEFT)
                        # Button(root, text="No", command = self.no).pack(side=RIGHT)
                        # print t
                        # root.mainloop()
                        # print t
                        #
                        # if t == 'yes':
                        #     print 'right'

                        self.vtOrderID1 = self.sendOrder(self.direction1, self.price1, 1, self.vtSymbol1, False)  # 卖出平仓  vtSymbol1
                        # self.vtOrderID1 = self.buy(self.price1, 1, self.vtSymbol1)
                        print self.vtSymbol1, self.direction1, self.price1, self.vtOrderID1, time.strftime("%H:%M:%S")

                        self.vtOrderID2 = self.sendOrder(self.direction2, self.price2, 1, self.vtSymbol2, False)  # 买入开仓  vtSymbol2
                        # vtOrderID2 = self.short(self.price2, 1, self.vtSymbol2)
                        print self.vtSymbol2, self.direction2, self.price2, self.vtOrderID2, time.strftime("%H:%M:%S")

                        # 确认下单成功，
                        if self.vtOrderID1 != EMPTY_STRING and self.vtOrderID2 != EMPTY_STRING:
                            self.count += 1
                        print 'count', self.count

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
                            if vtSymbol == self.vtSymbol1:
                                self.price1 = self.getPrice(self.vtSymbol1, self.direction1)
                                self.vtOrderID1 = self.sendOrder(self.direction1, self.price1, 1, self.vtSymbol1,
                                                                 False)  # 卖出平仓  vtSymbol1
                                print self.vtSymbol1, self.direction1, self.price1, self.vtOrderID1

                                self.orderDict[vtOrderID] = 'Finished'  # 删除已撤销条目

                            if vtSymbol == self.vtSymbol2:
                                self.price2 = self.getPrice(self.vtSymbol2, self.direction2)
                                self.vtOrderID2 = self.sendOrder(self.direction2, self.price2, 1, self.vtSymbol2,
                                                                 False)  # 卖出平仓  vtSymbol1
                                print self.vtSymbol2, self.direction2, self.price2, self.vtOrderID2

                                self.orderDict[vtOrderID] = 'Finished'  # 删除已撤销条目

                        # 未成交，未撤单，查看是否超时，若超时，撤单
                        else:
                            print order.status, order.orderTime
                            nowList = time.strftime("%H:%M:%S").split(":", 3)  # 当前时间
                            orderList = order.orderTime.split(":", 3)  # 下单时间
                            nowMinute = int(nowList[1])
                            nowSecond = int(nowList[2])
                            orderTimeMinute = int(orderList[1])
                            orderTimeSecond = int(orderList[2])
                            timeOut = (nowMinute * 60 + nowSecond) - (orderTimeMinute * 60 + orderTimeSecond) > self.limitTime  # 是否超时
                            print 'timeOut', timeOut

                            # 如果超时，撤单
                            if timeOut:
                                print u'超时未成交，撤单'
                                self.cancelOrder(vtOrderID)

                # 发出状态更新事件
                self.putEvent()
        except:
            print u'没有行情'

        # 检查是否已有委托，判断是否成交
        # if self.vtOrderID1 != EMPTY_STRING:
        #     try:
        #         order = self.orderDict[self.vtSymbol1]
        #         print '委托状态：', order.status
        #         if order.status == STATUS_ALLTRADED:
        #             vtSymbol2Bid1 = self.tickDict[self.vtSymbol2][0]  # 买一价
        #             vtOrderID2 = self.short(vtSymbol2Bid1, 1, self.vtSymbol2)  # 卖出开仓  vtSymbol2
        #             print self.vtSymbol2, vtSymbol2Bid1, vtOrderID2
        #             self.count += 1
        #             print 'count', self.count
        #             self.vtOrderID1 = EMPTY_STRING  # 重置委托单号
        #     except:
        #         print '没有委托'




        # 计算K线

        # tickMinute = tick.datetime.minute  # by hw
        #
        # if tick.vtSymbol in self.barMinute.keys():  # by hw
        #     barMinute = self.barMinute[tick.vtSymbol]
        # else:
        #     barMinute = EMPTY_STRING
        # # if tick.askPrice1 - tick.bidPrice1 >1:
        # #    print dt,tick.vtSymbol,tick.lastPrice,tick.bidPrice1,tick.askPrice1
        # # 撤单判断与执行,待修改
        #
        #
        # if tickMinute != barMinute:
        #     if tick.vtSymbol in self.bar.keys():  # by hw
        #         self.onBar(self.bar[tick.vtSymbol])  # by hw
        #
        #     bar = CtaBarData()
        #     bar.vtSymbol = tick.vtSymbol
        #     bar.symbol = tick.symbol
        #     bar.exchange = tick.exchange
        #
        #     bar.open = tick.lastPrice
        #     bar.high = tick.lastPrice
        #     bar.low = tick.lastPrice
        #     bar.close = tick.lastPrice
        #
        #     bar.date = tick.date
        #     bar.time = tick.time
        #     bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间
        #
        #     # 实盘中用不到的数据可以选择不算，从而加快速度
        #     # bar.volume = tick.volume
        #     # bar.openInterest = tick.openInterest
        #
        #     self.bar[tick.vtSymbol] = bar  # 这种写法为了减少一层访问，加快速度 by hw
        #     self.barMinute[tick.vtSymbol] = tickMinute  # 更新当前的分钟 by hw
        # else:  # 否则继续累加新的K线
        #     bar = self.bar[tick.vtSymbol]  # 写法同样为了加快速度
        #
        #     bar.high = max(bar.high, tick.lastPrice)
        #     bar.low = min(bar.low, tick.lastPrice)
        #     bar.close = tick.lastPrice


    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 主动成交
        # try:
        # if self.direction1 == u'买开' or self.direction1 == u'买平':  # 1买开、4买平
        #     self.price1 = self.tickDict[self.vtSymbol1][1]  # ask1
        # elif self.direction1 == u'卖开' or self.direction1 == u'卖平':  # 2卖平、3卖开
        #     self.price1 = self.tickDict[self.vtSymbol1][0]  # bid1
        #
        # if self.direction2 == u'买开' or self.direction2 == u'买平':  # 1买开、4买平
        #     self.price2 = self.tickDict[self.vtSymbol2][1]  # ask1
        # elif self.direction2 == u'卖开' or self.direction2 == u'卖平':  # 2卖平、3卖开
        #     self.price2 = self.tickDict[self.vtSymbol2][0]  # bid1

        # if self.price1 != EMPTY_FLOAT and self.price2 != EMPTY_FLOAT:  # 判断价格是否为零

        # self.price1 = self.getPrice(self.vtSymbol1, self.direction1)
        # self.price2 = self.getPrice(self.vtSymbol2, self.direction2)
        # self.spreadRt = abs(self.price1 - self.price2)  # 实时价差
        # print self.spreadRt
        # if (self.direction == 1 and self.spreadRt >= self.spreadLimit) or (self.direction == -1 and self.spreadRt <= self.spreadLimit):
        #     if self.count < self.countLimit:
        #         # 弹窗确认模块
        #         # global t
        #         # global root
        #         #
        #         # root = Tk()
        #         # root.title("hello world")
        #         # root.geometry('300x200')
        #         #
        #         # t = None
        #         #
        #         # l = Label(root, text=u"弹窗确认模块", font=("Arial", 12))
        #         # l.pack(side=TOP)
        #         #
        #         # Button(root, text="Yes", command = self.yes).pack(side=LEFT)
        #         # Button(root, text="No", command = self.no).pack(side=RIGHT)
        #         # print t
        #         # root.mainloop()
        #         # print t
        #         #
        #         # if t == 'yes':
        #         #     print 'right'
        #
        #         self.vtOrderID1 = self.sendOrder(self.direction1, self.price1, 1, self.vtSymbol1, False)  # 卖出平仓  vtSymbol1
        #         # self.vtOrderID1 = self.buy(self.price1, 1, self.vtSymbol1)
        #         print self.vtSymbol1, self.direction1, self.price1, self.vtOrderID1
        #
        #         self.vtOrderID2 = self.sendOrder(self.direction2, self.price2, 1, self.vtSymbol2, False)  # 买入开仓  vtSymbol2
        #         # vtOrderID2 = self.short(self.price2, 1, self.vtSymbol2)
        #         print self.vtSymbol2, self.direction2, self.price2, self.vtOrderID2
        #         self.count += 1
        #         print 'count', self.count
        #
        # # 检查订单成交情况，如果超过1分钟未成交，先撤单，在下单
        # for vtOrderID in self.orderDict:
        #     order = self.orderDict[vtOrderID]
        #     if order != 'Finished':
        #         orderFinished = order.status == STATUS_ALLTRADED   # 是否完成
        #
        #         if orderFinished:   # 已成交，从字典中删除
        #             self.orderDict[vtOrderID] = 'Finished'   # 删除条目
        #         else:   # 未成交，查看是否超时
        #             print order.status, order.orderTime
        #             print 'orderFinished', orderFinished
        #             now_list = time.strftime("%H:%M:%S").split(":", 3)   # 当前时间
        #             order_list = order.orderTime.split(":", 3)           # 下单时间
        #             now_minute = int(now_list[1])
        #             now_second = int(now_list[2])
        #             orderTime_minute = int(order_list[1])
        #             orderTime_second = int(order_list[2])
        #             timeOut = (now_minute*60 - now_second) - (orderTime_minute*60 + orderTime_second) > self.limitTime  # 是否超时
        #             print 'timeOut', timeOut
        #
        #             # 如果超时，撤单
        #             if timeOut:
        #                 print u'超时未成交，撤单'
        #                 self.cancelOrder(vtOrderID)
        #
        #         # 已撤销，重新下单
        #         if order.status == STATUS_CANCELLED:
        #             vtSymbol = order.vtSymbol
        #             if vtSymbol == self.vtSymbol1:
        #                 self.price1 = self.getPrice(self.vtSymbol1, self.direction1)
        #                 self.vtOrderID1 = self.sendOrder(self.direction1, self.price1, 1, self.vtSymbol1, False)  # 卖出平仓  vtSymbol1
        #                 print self.vtSymbol1, self.direction1, self.price1, self.vtOrderID1
        #
        #                 self.orderDict[vtOrderID] = 'Finished'  # 删除已撤销条目
        #
        #             if vtSymbol == self.vtSymbol2:
        #                 self.price2 = self.getPrice(self.vtSymbol2, self.direction2)
        #                 self.vtOrderID2 = self.sendOrder(self.direction2, self.price2, 1, self.vtSymbol2, False)  # 卖出平仓  vtSymbol1
        #                 print self.vtSymbol2, self.direction2, self.price2, self.vtOrderID2
        #
        #                 self.orderDict[vtOrderID] = 'Finished'  # 删除已撤销条目

        # 发出状态更新事件
        # self.putEvent()

    # def yes():
    #     global t
    #     t = 'Yes'
    #     root.destroy()
    #
    # def no():
    #     global t
    #     t = 'No'
    #     root.destroy()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        self.orderDict[order.vtOrderID] = order


    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        vtOrderID = trade.vtOrderID
        if vtOrderID not in self.completeOrderDict:
            self.completeOrderDict[vtOrderID] = trade

        print '****************************************'
        print u'成交回报', time.strftime("%H:%M:%S")
        print 'vtSymbol', trade.vtSymbol, 'price', trade.price, 'tradeTime', trade.tradeTime, 'OrderID',trade.vtOrderID
        print '****************************************'















