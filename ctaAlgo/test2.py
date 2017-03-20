# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 11:20:15 2017

@author: wxyc
"""
import time
import sys
from PyQt4.QtGui import *
# from t import *
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
    name = 'zhangqi'  # 策略实例名称

    # **********************************************************************
    # 策略参数
    spreadLimit = 40    # 展期价差
    # direction = -1      # 展期方向，1多头展期，-1空头展期
    direction1 = u'买开'      # 合约1操作方向，1买开，2卖平，3卖开，4买平
    direction2 = u'卖开'      # 合约1操作方向，1买开，2卖平，3卖开，4买平
    countLimit = 1      # 子单次数限制，一个子单操作一个数量的合约，一个母单包含多个子单。

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
    tickDict = {}              # 保存最新bid，ask价格，key为vtSymbol, value为[bid1, ask1]
    orderDict = {}             # 保存委托变化推送
    vtOrderID1 = EMPTY_STRING
    vtOrderID2 = EMPTY_STRING

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
        self.writeCtaLog(u'测试策略2多合约展期启动')

        # 确定操作所需的合约，进行风控检查，提前锁定仓位和资金


        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'测试策略2多合约展期停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 记录最新价格
        if tick.vtSymbol == self.vtSymbol1:
            self.tickDict[self.vtSymbol1] = [tick.bidPrice1, tick.askPrice1]

        if tick.vtSymbol == self.vtSymbol2:
            self.tickDict[self.vtSymbol2] = [tick.bidPrice1, tick.askPrice1]

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

        tickMinute = tick.datetime.minute  # by hw

        if tick.vtSymbol in self.barMinute.keys():  # by hw
            barMinute = self.barMinute[tick.vtSymbol]
        else:
            barMinute = EMPTY_STRING
        # if tick.askPrice1 - tick.bidPrice1 >1:
        #    print dt,tick.vtSymbol,tick.lastPrice,tick.bidPrice1,tick.askPrice1
        # 撤单判断与执行,待修改


        if tickMinute != barMinute:
            if tick.vtSymbol in self.bar.keys():  # by hw
                self.onBar(self.bar[tick.vtSymbol])  # by hw

            bar = CtaBarData()
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            # 实盘中用不到的数据可以选择不算，从而加快速度
            # bar.volume = tick.volume
            # bar.openInterest = tick.openInterest

            self.bar[tick.vtSymbol] = bar  # 这种写法为了减少一层访问，加快速度 by hw
            self.barMinute[tick.vtSymbol] = tickMinute  # 更新当前的分钟 by hw
        else:  # 否则继续累加新的K线
            bar = self.bar[tick.vtSymbol]  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice


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

        self.price1 = self.getPrice(self.vtSymbol1, self.direction1)
        self.price2 = self.getPrice(self.vtSymbol2, self.direction2)
        self.spreadRt = abs(self.price1 - self.price2)  # 实时价差
        print self.spreadRt
        if self.spreadRt <= self.spreadLimit:
            if self.count < self.countLimit:
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
                print self.vtSymbol1, self.direction1, self.price1, self.vtOrderID1

                self.vtOrderID2 = self.sendOrder(self.direction2, self.price2, 1, self.vtSymbol2, False)  # 买入开仓  vtSymbol2
                # vtOrderID2 = self.short(self.price2, 1, self.vtSymbol2)
                print self.vtSymbol2, self.direction2, self.price2, self.vtOrderID2
                self.count += 1
                print 'count', self.count

                    # else:
                    #     self.writeCtaLog(u'展期次数超过限制')
                    #     print u'展期次数超过限制'

        # 检查订单成交情况，如果超过1分钟未成交，先撤单，在下单
        # for vtOrderID in self.orderDict:
        #     order = self.orderDict[vtOrderID]
        #     print order.status, order.orderTime
        #     orderFinished = (order.status == STATUS_ALLTRADED or order.status == STATUS_CANCELLED)  # 是否完成
            # timeOut = order.orderTime < time.time()   # 是否超时
            # if not orderFinished and timeOut:
            #     self.cancelOrder(vtOrderID)
            #
            # # 已撤销，重新下单
            # if order.status == STATUS_CANCELLED:
            #     vtSymbol = order.vtSymbol
            #     if vtSymbol == self.vtSymbol1:
            #         self.price1 = self.getPrice(self.vtSymbol1, self.direction1)
            #         self.vtOrderID1 = self.sendOrder(self.direction1, self.price1, 1, self.vtSymbol1, False)  # 卖出平仓  vtSymbol1
            #         print self.vtSymbol1, self.direction1, self.price1, self.vtOrderID1
            #
            #         del self.orderDict[vtOrderID]  # 删除条目
            #
            #     if vtSymbol == self.vtSymbol2:
            #         self.price2 = self.getPrice(self.vtSymbol2, self.direction2)
            #         self.vtOrderID2 = self.sendOrder(self.direction2, self.price2, 1, self.vtSymbol2, False)  # 卖出平仓  vtSymbol1
            #         print self.vtSymbol2, self.direction2, self.price2, self.vtOrderID2
            #
            #         del self.orderDict[vtOrderID]  # 删除条目



        # except:
        #     print u'没有tick行情'

        # if bar.vtSymbol == self.vtSymbol1:
        #     self.price1 = bar.close
        #     print 'price1',self.price1
        #
        # if bar.vtSymbol == self.vtSymbol2:
        #     self.price2 = bar.close
        #     print 'price2',self.price2
        #
        # print abs(self.price1 - self.price2)
        #
        # # 判断信号
        # if self.price1 != EMPTY_FLOAT and self.price2 != EMPTY_FLOAT:     # 判断价格是否为零
        #     self.spreadRt = self.price1 - self.price2   # 实时价差
        #     print self.spreadRt
        #     if abs(self.spreadRt) <= self.spreadLimit:
        #         if self.count < self.countLimit:
        #             print u'多头展期', self.count
        #
        #             # 弹窗确认模块
        #
        #
        #             vtSymbol1Bid1 = self.tickDict[self.vtSymbol1][0]          # 买一价
        #             self.vtOrderID1 = self.short(vtSymbol1Bid1, 1, self.vtSymbol1)  # 卖出平仓  vtSymbol1
        #             print self.vtSymbol1, vtSymbol1Bid1, self.vtOrderID1
        #
        #             vtSymbol2Ask1 = self.tickDict[self.vtSymbol2][1]             # 卖一价
        #             vtOrderID2 = self.buy(vtSymbol2Ask1, 1, self.vtSymbol2)   # 买入开仓  vtSymbol2
        #             print self.vtSymbol2, vtSymbol2Ask1, vtOrderID2
        #             self.count += 1
        #             print 'count',self.count
        #
        #         else:
        #             self.writeCtaLog(u'展期次数超过限制')
        #             print u'展期次数超过限制'
        #
        #     elif self.direction == -1:   # 空头展期
        #         self.spreadRt = self.price1 - self.price2
        #         print self.spreadRt
        #
        #         # 检查是否已有委托，判断是否成交
        #         # if self.vtOrderID1 != EMPTY_STRING:
        #         #     try:
        #         #         order = self.orderDict[self.vtSymbol1]
        #         #         print '委托状态：', order.status
        #         #         if order.status == STATUS_ALLTRADED:
        #         #             vtSymbol2Bid1 = self.tickDict[self.vtSymbol2][0]  # 买一价
        #         #             vtOrderID2 = self.short(vtSymbol2Bid1, 1, self.vtSymbol2)  # 卖出开仓  vtSymbol2
        #         #             print self.vtSymbol2, vtSymbol2Bid1, vtOrderID2
        #         #             self.count += 1
        #         #             print 'count', self.count
        #         #             self.vtOrderID1 = EMPTY_STRING   # 重置委托单号
        #         #     except:
        #         #         print '没有委托'
        #
        #         if self.vtOrderID1 == EMPTY_STRING:
        #             if self.spreadRt <= self.spreadLimit:
        #                 if self.count < self.countLimit and abs(self.pos[self.vtSymbol1]) < 1 and abs(self.pos[self.vtSymbol2]) < 1 :
        #                     print u'空头展期',self.count
        #
        #                     # 弹窗确认模块
        #
        #
        #                     vtSymbol1Ask1 = self.tickDict[self.vtSymbol1][1]             # 卖一价
        #                     self.vtOrderID1 = self.buy(vtSymbol1Ask1, 1, self.vtSymbol1)    # 买入平仓  vtSymbol1
        #                     print self.vtSymbol1, vtSymbol1Ask1, self.vtOrderID1
        #                 else:
        #                     self.writeCtaLog(u'展期次数超过限制')
        #                     print u'展期次数超过限制'
        #     else:
        #         self.writeCtaLog(u'展期方向错误')
        #         print u'展期方向错误'
        #
        # 发出状态更新事件
        self.putEvent()

    def yes():
        global t
        t = 'Yes'
        root.destroy()

    def no():
        global t
        t = 'No'
        root.destroy()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        if order.vtSymbol == self.vtSymbol1:
            self.orderDict[self.vtSymbol1] = order

        if order.vtSymbol == self.vtSymbol2:
            self.orderDict[self.vtSymbol2] = order


    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        vtOrderID = trade.vtOrderID
        if vtOrderID not in self.completeOrderDict:
            self.completeOrderDict[vtOrderID] = trade

        print u'成交回报'
        print 'OrderID',trade.vtOrderID
        print 'TradeID',trade.vtTradeID


    def getPrice(self, vtSymbol, direction):
        """提取对应操作的买一卖一价格"""
        if direction == u'买开' or direction == u'买平':  # 1买开、4买平
            price = self.tickDict[vtSymbol][1]  # ask1
        elif direction == u'卖开' or direction == u'卖平':  # 2卖平、3卖开
            price = self.tickDict[vtSymbol][0]  # bid1

        return price













