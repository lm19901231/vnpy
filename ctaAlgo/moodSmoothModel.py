# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 11:20:15 2017

@author: wxyc
"""

import time
from ctaBase import *
from vtConstant import *
from ctaTemplate import CtaTemplate


class MoodSmoothModel(CtaTemplate):
    """市场情绪平稳度策略"""

    className = 'MoodSmooth'
    author = u'lm'
    name = 'mood smooth'  # 策略实例名称

    # 策略参数
    direction = EMPTY_STRING  # 合约操作方向，1买开，2卖平，3卖开，4买平
    countLimit = 1  # 子单次数限制，一个子单操作一个数量的合约，一个母单包含多个子单。
    count = EMPTY_INT
    volume = countLimit
    limitTime = 2
    start = 30
    threshold = 0.0008
    limitLen = 30
    limitRate = 0.5

    # 策略变量
    bar = None
    barMinute = EMPTY_STRING
    barList = []
    price = EMPTY_FLOAT
    sign = EMPTY_INT
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
        super(MoodSmoothModel, self).__init__(ctaEngine, setting)

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

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 记录最新价格
        if tick.vtSymbol == self.vtSymbol:
            # print time.strftime("%H:%M:%S"), tick.vtSymbol, tick.bidPrice1, tick.bidVolume1, tick.askPrice1, tick.askVolume1
            self.tickDict[self.vtSymbol] = [tick.bidPrice1, tick.askPrice1]

        # 计算K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:
            if self.bar:
                self.onBar(self.bar)

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

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟

        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.barList.append(bar.close)

        # 从数据库提历史数据
        observeList = self.barList
        e = self.threshold
        keep = 3 * self.threshold

        # 判断交易信号
        if self.trading:
            length = len(self.barList)
            if length >= self.limitLen:
                localMax = self.barList.index(max(self.barList))
                localMin = self.barList.index(min(self.barList))

                mdMean = 1; mdrMean = 1; marketMood = 1; buyPrice = 0; sellPrice = 10000
                if length - localMax + 1 >= self.limitLen or length - localMin + 1 >= self.limitLen:
                    mdMean, mdrMean = self.compute_smooth(observeList, localMax, localMin)
                    marketMood = min(mdMean, mdrMean)

                if self.sign == 0 and self.count < self.countLimit:
                    if marketMood < self.threshold and marketMood != 0:
                        if mdMean < mdrMean - e:
                            self.sign = 1
                            self.direction = DIRECTION_LONG
                            self.price = self.getPrice(self.vtSymbol, self.direction)
                            buyPrice = self.price
                            vtOrderID = self.buy(self.price, 1, self.vtSymbol)
                            print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                            if vtOrderID:
                                self.count += 1

                        elif mdrMean < mdMean - e:
                            self.sign = -1
                            self.direction = DIRECTION_SHORT
                            self.price = self.getPrice(self.vtSymbol, self.direction)
                            sellPrice = self.price
                            vtOrderID = self.short(self.price, 1, self.vtSymbol)
                            print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                            if vtOrderID:
                                self.count += 1

                if self.sign == 1:
                    mdMean1 = self.compute_smooth(observeList, 0, localMin)
                    maxPrice = max(observeList[localMin:])
                    limitLine = maxPrice - (maxPrice - observeList[localMin]) * self.limitRate
                    # 平仓条件
                    if mdMean1 >= keep:
                        self.price = self.getPrice(self.vtSymbol, DIRECTION_SHORT)
                        vtOrderID = self.sell(self.price, 1, self.vtSymbol)
                        print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                        self.sign = 0
                    # 从高下跌(买入价格大于止损线)，跌破止损线，且跌幅大于10
                    elif observeList[-1] <= limitLine and buyPrice > limitLine:
                        self.sign = 2    # 2表示止损，记录止损价格
                        self.price = self.getPrice(self.vtSymbol, DIRECTION_SHORT)
                        vtOrderID = self.sell(self.price, 1, self.vtSymbol)
                        print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                        self.sign = 0

                elif self.sign == -1:
                    mdrMean1 = self.compute_smooth(observeList, localMax, 0)
                    minPrice = min(observeList[localMax:])
                    limitLine = minPrice + (observeList[localMax] - minPrice) * self.limitRate
                    if mdrMean1 >= keep:
                        self.price = self.getPrice(self.vtSymbol, DIRECTION_LONG)
                        vtOrderID = self.cover(self.price, 1, self.vtSymbol)
                        print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                        self.sign = 0

                    # 从低上涨(卖出价格低于止损线)，涨破止损线，且涨幅大于10
                    elif observeList[-1] >= limitLine and sellPrice < limitLine:
                        self.sign = 2  # 2表示止损，记录止损价格
                        self.price = self.getPrice(self.vtSymbol, DIRECTION_LONG)
                        vtOrderID = self.cover(self.price, 1, self.vtSymbol)
                        print self.vtSymbol, self.direction, vtOrderID, time.strftime("%H:%M:%S")
                        self.sign = 0


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
                            vtOrderID1 = self.sendOrder(self.direction, self.price, 1, self.vtSymbol,
                                                        False)  # 卖出平仓  vtSymbol1
                            print self.vtSymbol, self.direction, self.price, vtOrderID1, time.strftime("%H:%M:%S")

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


    def compute_smooth(self, observeList, localMax, localMin):
        """计算市场情绪平稳度"""
        mdMean = 1
        mdrMean = 1
        # 计算正向最大回撤
        if localMin != 0:
            upList = observeList[localMin:]  # 取最小值开始的序列
            len1 = len(upList)
            if len1 >= self.limitLen:     # 长度达到最短长度要求
                mdList = []
                for j in range(len1):
                    reback = 1 - upList[j] / max(upList[:j]) # 正向最大回撤, 上升力量
                    mdList.append(reback)

                mdMean = sum(mdList)/len(mdList)

        else:
            upList = observeList[localMax:]
            len1 = len(upList)
            mdList = []
            for j in range(len1):
                reback = 1 - upList[j] / max(upList[:j])  # 正向最大回撤, 上升力量
                mdList.append(reback)
            mdMean = sum(mdList)/len(mdList)


        # 计算反向最大回撤
        if localMax != 0:
            downList = observeList[localMax:]    # 取最大值开始的序列
            len2 = len(downList)
            if len2 >= self.limitLen:   # 长度达到最短长度要求
                mdrList = []
                for j in range(len2):
                    reback = downList[j] / min(downList[:j]) - 1  # 反向最大回撤，下降力量
                    mdrList.append(reback)

                mdrMean = sum(mdrList)/len(mdrList)
        # 取最小值开始的序列，与正向最大回撤同步，用来比较两者的差别
        else:
            downList = observeList[localMin:]
            len2 = len(downList)
            mdrList = []
            for j in range(len2):
                reback = downList[j] / min(downList[:j]) - 1     # 反向最大回撤，下降力量
                mdrList.append(reback)

                mdrMean = sum(mdrList) / len(mdrList)

        return mdMean, mdrMean

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

















