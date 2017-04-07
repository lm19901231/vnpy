# encoding: UTF-8

'''
本文件中实现了风控引擎，用于提供一系列常用的风控功能：
1. 委托流控（单位时间内最大允许发出的委托数量）
2. 总成交限制（每日总成交数量限制）
3. 单笔委托的委托数量控制
'''

import json
import os
import platform
import re
import time

from eventEngine import *
from vtConstant import *
from vtGateway import VtLogData
from ctaEngine import PositionBuffer


########################################################################
class RmEngine(object):
    """风控引擎"""
    settingFileName = 'RM_setting.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)    
    
    name = u'风控模块'

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 是否启动风控
        self.active = False
        
        # 流控相关
        self.orderFlowCount = EMPTY_INT     # 单位时间内委托计数
        self.orderFlowLimit = EMPTY_INT     # 委托限制
        self.orderFlowClear = EMPTY_INT     # 计数清空时间（秒）
        self.orderFlowTimer = EMPTY_INT     # 计数清空时间计时
    
        # 单笔委托相关
        self.orderSizeLimit = EMPTY_INT     # 单笔委托最大限制
    
        # 成交统计相关
        self.tradeCount = EMPTY_INT         # 当日成交合约数量统计
        self.tradeLimit = EMPTY_INT         # 当日成交合约数量限制
        
        # 活动合约相关
        self.workingOrderLimit = EMPTY_INT  # 活动合约最大限制

        # 策略需求风控检查相关 by lm
        self.account = EMPTY_FLOAT          # 账户可用资金
        self.posFreezeDict = {}             # 账户冻结持仓

        # 保证金相关
        self.marginDict = {}                # 保证金字典
        self.marginDict['IF'] = marginData()
        self.marginDict['IH'] = marginData()
        self.marginDict['IC'] = marginData()
        self.margin = EMPTY_FLOAT           # 保证金
        self.marginRatioIC = 0.31 * 200          # 保证金比例 * 每点价格
        self.marginRatioIF = 0.21 * 300
        self.marginRatioIH = 0.21 * 300
        self.accountLackCount = EMPTY_INT

        self.tickDict = {}                  # 实时价格行情
        self.orderDict = {}                 # 实时订单状态

        self.startTime = time.strftime("%H:%M:%S")  # 风控启动时间
        
        self.loadSetting()
        self.registerEvent()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取配置"""
        with open(self.settingFileName) as f:
            d = json.load(f)
            
            # 设置风控参数
            self.active = d['active']
            
            self.orderFlowLimit = d['orderFlowLimit']
            self.orderFlowClear = d['orderFlowClear']
            
            self.orderSizeLimit = d['orderSizeLimit']
            
            self.tradeLimit = d['tradeLimit']
            
            self.workingOrderLimit = d['workingOrderLimit']
        
    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存风控参数"""
        with open(self.settingFileName, 'w') as f:
            # 保存风控参数
            d = {}

            d['active'] = self.active
            
            d['orderFlowLimit'] = self.orderFlowLimit
            d['orderFlowClear'] = self.orderFlowClear
            
            d['orderSizeLimit'] = self.orderSizeLimit
            
            d['tradeLimit'] = self.tradeLimit
            
            d['workingOrderLimit'] = self.workingOrderLimit
            
            # 写入json
            jsonD = json.dumps(d, indent=4)
            f.write(jsonD)

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TRADE, self.updateTrade)       # 成交回报事件
        # self.eventEngine.register(EVENT_ORDER, self.updateFreeze)      # 报单回报事件
        self.eventEngine.register(EVENT_TIMER, self.updateTimer)       # 计时器事件，每隔1秒发送一次
        self.eventEngine.register(EVENT_ACCOUNT, self.updateAccount)   # 账户回报事件
        self.eventEngine.register(EVENT_TICK, self.updateTick)         # Tick行情事件
    
    #----------------------------------------------------------------------
    def updateTrade(self, event):
        """更新成交数据"""
        trade = event.dict_['data']
        self.tradeCount += trade.volume
    
    #----------------------------------------------------------------------
    def updateTimer(self, event):
        """更新定时器"""
        self.orderFlowTimer += 1
        
        # 如果计时超过了流控清空的时间间隔，则执行清空
        if self.orderFlowTimer >= self.orderFlowClear:
            self.orderFlowCount = 0
            self.orderFlowTimer = 0

    # ----------------------------------------------------------------------
    def updateAccount(self, event):
        """更新账户可用资金"""
        account = event.dict_['data']
        self.account = account.available
        # print 'account', self.account, time.strftime("%H:%M:%S")

        # 原有保证金需求
        marginNeedTotal = self.marginDict['IF'].marginNeed + self.marginDict['IH'].marginNeed + self.marginDict['IC'].marginNeed
        # print marginNeedTotal
        # 可用保证金小于所需保证金
        if self.account < marginNeedTotal:
            # 保证金不足计数
            self.accountLackCount += 1
            #
            if self.accountLackCount > 1:
                event1 = Event(type_=EVENT_RMSTOP)
                event1.dict_['data'] = 'name'
                self.eventEngine.put(event1)
                self.writeRiskLog(u'发生异常情况：可用保证金小于所需保证金，停止所有策略')
                print u'发生异常情况：可用保证金小于所需保证金，停止所有策略'
        else:
            self.accountLackCount = 0

    # ----------------------------------------------------------------------
    def updateTick(self, event):
        """更新实时价格行情"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol
        self.tickDict[vtSymbol] = tick.lastPrice


    #----------------------------------------------------------------------
    def writeRiskLog(self, content):
        """快速发出日志事件"""
        # 发出报警提示音

        if platform.uname() == 'Windows':
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ASYNC) 
        
        # 发出日志事件
        log = VtLogData()
        log.logContent = content
        log.gatewayName = self.name
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def checkRisk(self, orderReq):
        """检查风险"""
        # 如果没有启动风控检查，则直接返回成功
        if not self.active:
            return True
        
        # 检查委托数量
        if orderReq.volume > self.orderSizeLimit:
            self.writeRiskLog(u'单笔委托数量%s，超过限制%s' 
                              %(orderReq.volume, self.orderSizeLimit))
            return False
        
        # 检查成交合约量
        if self.tradeCount >= self.tradeLimit:
            self.writeRiskLog(u'今日总成交合约数量%s，超过限制%s' 
                              %(self.tradeCount, self.tradeLimit))
            return False
        
        # 检查流控
        if self.orderFlowCount >= self.orderFlowLimit:
            self.writeRiskLog(u'委托流数量%s，超过限制每%s秒%s' 
                              %(self.orderFlowCount, self.orderFlowClear, self.orderFlowLimit))
            return False
        
        # 检查总活动合约
        workingOrderCount = len(self.mainEngine.getAllWorkingOrders())
        if workingOrderCount >= self.workingOrderLimit:
            self.writeRiskLog(u'当前活动委托数量%s，超过限制%s'
                              %(workingOrderCount, self.workingOrderLimit))
            return False
        
        # 对于通过风控的委托，增加流控计数
        self.orderFlowCount += 1
        
        return True

    # ----------------------------------------------------------------------
    def updateFreeze(self, event):
        """更新冻结资金和持仓"""
        # by lm
        # 策略需求检查时增加了冻结资金和持仓
        # 开仓：下单时冻结资金相应减少，撤单时冻结资金相应增加
        # 平仓：下单成交时冻结持仓减少
        order = event.dict_['data']
        # 判断是否为历史报单
        # print self.startTime, order.orderTime
        if self.startTime > order.orderTime:
            # print u'历史报单'
            # print order.vtSymbol, order.vtOrderID, order.status, order.orderTime, order.offset, order.direction
            pass
        else:
            vtOrderID = order.vtOrderID
            vtSymbol = order.vtSymbol
            vtSymbolType = vtSymbol[0:2]
            # 新的订单
            if vtOrderID not in self.orderDict:
                self.orderDict[vtOrderID] = order
                if order.offset == OFFSET_OPEN:
                    # 开仓减少冻结保证金（因为开仓时可用保证金会减少，冻结保证金需同步减少）
                    self.adjustMarginDict(order)
                    # 打印保证金字典
                    self.printMarginDict(vtSymbolType)

            # 已有的订单
            else:
                # 开仓撤单增加冻结保证金（因为开仓撤单时可用保证金会增加，冻结保证金需同步增加）
                if order.offset == OFFSET_OPEN and order.status == STATUS_CANCELLED:
                    self.adjustMarginDict(order)
                    # 打印保证金字典
                    self.printMarginDict(vtSymbolType)

                elif order.offset == OFFSET_CLOSE:
                    # 平仓成交减少冻结持仓（因为平仓成交会导致持仓会减少，冻结持仓需同步减少）
                    if order.status == STATUS_ALLTRADED:
                        # 多头平仓
                        if order.direction == DIRECTION_LONG:
                            self.posFreezeDict[vtSymbol].shortPosition -= order.totalVolume  # 空头减少
                        # 空头平仓
                        elif order.direction == DIRECTION_SHORT:
                            self.posFreezeDict[vtSymbol].longPosition -= order.totalVolume  # 多头减少

    # ----------------------------------------------------------------------
    def printMarginDict(self, vtSymbolType):
        """打印保证金字典"""
        # by lm
        print u'%s保证金字典' % vtSymbolType
        print u'时间：%s' % time.strftime("%H:%M:%S")
        print u'多头数量：%d' % self.marginDict[vtSymbolType].long
        print u'多头保证金：%f' % self.marginDict[vtSymbolType].marginLong
        print u'空头数量：%d' % self.marginDict[vtSymbolType].short
        print u'空头保证金：%f' % self.marginDict[vtSymbolType].marginShort
        print u'所需保证金：%f' % self.marginDict[vtSymbolType].marginNeed

    # ----------------------------------------------------------------------
    def printPosition(self, posBufferDict, content):
        """打印持仓"""
        # by lm
        print content
        print u'时间：%s' % time.strftime("%H:%M:%S")
        for vtSymbol in posBufferDict:
            posBuffer = posBufferDict[vtSymbol]
            print u'合约%s多头%d(可用%d)，空头%d(可用%d)。' % (vtSymbol, posBuffer.longPosition, posBuffer.longAvailable, posBuffer.shortPosition, posBuffer.shortAvailable)

    # ----------------------------------------------------------------------
    def adjustMarginDict(self, order):
        """调整保证金字典"""
        # by lm
        vtSymbol = order.vtSymbol
        vtSymbolType = vtSymbol[0:2]
        marginRatio = self.getMarginRatio(vtSymbolType)

        margin = marginData()
        # 开仓
        if order.offset == OFFSET_OPEN:
            # 下单减少冻结保证金（因为开仓时可用保证金会减少，冻结保证金需同步减少）
            if order.status != STATUS_CANCELLED:
                # 开多
                if order.direction == DIRECTION_LONG:
                    margin.long -= order.totalVolume
                    margin.marginLong -= order.totalVolume * marginRatio * order.price
                # 开空
                elif order.direction == DIRECTION_SHORT:
                    margin.short -= order.totalVolume
                    margin.marginShort -= order.totalVolume * marginRatio * order.price

            # 撤单增加冻结保证金（因为开仓撤单时可用保证金会增加，冻结保证金需同步增加）
            else:
                # 开多
                if order.direction == DIRECTION_LONG:
                    margin.long += order.totalVolume
                    margin.marginLong += order.totalVolume * marginRatio * order.price
                # 开空
                elif order.direction == DIRECTION_SHORT:
                    margin.short += order.totalVolume
                    margin.marginShort += order.totalVolume * marginRatio * order.price

            # 更新保证金字典
            self.marginDict[vtSymbolType] = self.merge(self.marginDict[vtSymbolType], margin)

    # ----------------------------------------------------------------------
    def strategyCheck(self, req, posBufferDict):
        """策略需求检查"""
        # by lm
        # 开仓检查保证金，平仓检查是否有持仓
        statusMargin = True
        statusPosition = True
        # 保证金需求
        marginDict = {}
        marginDict['IF'] = marginData()
        marginDict['IH'] = marginData()
        marginDict['IC'] = marginData()
        vtSymbolTypeDict = {}

        # 读取持仓和保证金情况
        for vtSymbol in req:
            require = req[vtSymbol]  # [方向，数量]
            vtSymbolType = vtSymbol[0:2]
            if vtSymbolType not in vtSymbolTypeDict:
                vtSymbolTypeDict[vtSymbolType] = 1

            # 开仓检查保证金
            if require[0] == u'买开' or require[0] == u'卖开':
                # 计算保证金需求
                marginDict = self.computeMargin(vtSymbol, require, marginDict)

            # 平仓检查是否有持仓
            else:
                # 打印持仓信息
                self.printPosition(posBufferDict, u'现有持仓')
                # 打印冻结信息
                self.printPosition(self.posFreezeDict, u'冻结持仓')
                # 检查持仓是否足够
                if vtSymbol in posBufferDict:
                    statusPosition = statusPosition & self.checkPosition(vtSymbol, require, posBufferDict[vtSymbol])
                else:
                    print u'%s没有持仓。' % vtSymbol
                    statusPosition = False

        # 判断保证金是否足够
        # 策略所需保证金为
        marginNeed = marginDict['IF'].marginNeed + marginDict['IH'].marginNeed + marginDict['IC'].marginNeed
        if marginNeed > 0:
            print u'策略所需保证金为：%.2f' % marginNeed
            print u'现有可用保证金为：%.2f' % self.account
            # 原有保证金需求
            marginNeedTotal = self.marginDict['IF'].marginNeed + self.marginDict['IH'].marginNeed + self.marginDict['IC'].marginNeed
            if marginNeed + marginNeedTotal <= self.account:
                print u'保证金足够'
                # 更新保证金字典
                self.updateMarginDict(marginDict)
                # 打印保证金字典
                for vtSymbolType in vtSymbolTypeDict:
                    self.printMarginDict(vtSymbolType)
            else:
                print u'保证金不足，缺少%.2f' % (marginNeed + marginNeedTotal - self.account)
                # self.writeRiskLog(u'保证金不足')
                statusMargin = False

        return statusMargin & statusPosition

    # ----------------------------------------------------------------------
    def getMarginRatio(self, vtSymbolType):
        """合约保证金比例和合约点价格"""
        # by lm
        if vtSymbolType == 'IF':
            return self.marginRatioIF
        elif vtSymbolType == 'IH':
            return self.marginRatioIH
        elif vtSymbolType == 'IC':
            return self.marginRatioIC

    # ----------------------------------------------------------------------
    def computeMargin(self, vtSymbol, require, marginDict):
        """计算保证金需求"""
        # by lm
        vtSymbolType = vtSymbol[:2]  # 合约类型：IF,IH,IC
        marginRatio = self.getMarginRatio(vtSymbolType)

        # 查询是否在保证金字典中
        if vtSymbolType not in marginDict:
            margin = marginData()
        else:
            margin = marginDict[vtSymbolType]

        if require[0] == u'买开':
            margin.long += require[1]
            margin.marginLong += require[1] * marginRatio * self.tickDict[vtSymbol]
        elif require[0] == u'卖开':
            margin.short += require[1]
            margin.marginShort += require[1] * marginRatio * self.tickDict[vtSymbol]


        # 所需保证金为多空保证金之和
        # margin.marginNeed = margin.marginLong + margin.marginShort
        # 所需保证金为多空保证金中的较大者
        margin.marginNeed = max(margin.marginLong, margin.marginShort)
        # 保存
        marginDict[vtSymbolType] = margin
        return marginDict

    # ----------------------------------------------------------------------
    def checkPosition(self, vtSymbol, require, posBuffer):
        """检查持仓"""
        # by lm
        # 买入平仓检查是否有持仓
        if require[0] == u'买平':
            # 真实可用持仓为：可用持仓 - 预冻结持仓
            if vtSymbol in self.posFreezeDict:
                realPos = posBuffer.shortAvailable - self.posFreezeDict[vtSymbol].shortPosition
            else:
                posBuffer = PositionBuffer()
                posBuffer.vtSymbol = vtSymbol
                self.posFreezeDict[vtSymbol] = posBuffer
                realPos = posBuffer.shortAvailable

            # 平仓数量小于等于真实可用持仓
            if require[1] <= realPos:
                self.posFreezeDict[vtSymbol].shortPosition += require[1]  # 冻结持仓
                print vtSymbol, u'冻结持仓', self.posFreezeDict[vtSymbol].shortPosition
                return True
            else:
                print u'%s空头持仓不足以平仓' % vtSymbol
                self.writeRiskLog(u'%s空头持仓不足以平仓' % vtSymbol)
                return False

        # 卖出平仓检查是否有持仓
        else:
            # 真实可用持仓为：持仓 - 冻结持仓
            if vtSymbol in self.posFreezeDict:
                realPos = posBuffer.longAvailable - self.posFreezeDict[vtSymbol].longPosition
            else:
                posBuffer = PositionBuffer()
                posBuffer.vtSymbol = vtSymbol
                self.posFreezeDict[vtSymbol] = posBuffer
                realPos = posBuffer.longAvailable

                # 平仓数量小于等于真实可用持仓
            if require[1] <= realPos:
                self.posFreezeDict[vtSymbol].longPosition += require[1]  # 冻结持仓
                print vtSymbol, u'冻结持仓', self.posFreezeDict[vtSymbol].longPosition
                return True
            else:
                print u'%s多头持仓不足以平仓' % vtSymbol
                self.writeRiskLog(u'%s多头持仓不足以平仓' % vtSymbol)
                return False

    # ----------------------------------------------------------------------
    def updateMarginDict(self, marginDict):
        """更新保证金字典"""
        # by lm
        for vtSymbolType in self.marginDict:
            self.marginDict[vtSymbolType] = self.merge(self.marginDict[vtSymbolType], marginDict[vtSymbolType])

    # ----------------------------------------------------------------------
    def merge(self, dict1, dict2):
        """合并保证金字典"""
        # by lm
        dict = marginData()
        dict.long = dict1.long + dict2.long
        dict.marginLong = dict1.marginLong + dict2.marginLong
        dict.short = dict1.short + dict2.short
        dict.marginShort = dict1.marginShort + dict2.marginShort
        dict.marginNeed = max(dict.marginLong, dict.marginShort)
        return dict

    # ----------------------------------------------------------------------
    def abnormalCheck(self):
        """异常事件检查"""
        # by lm
        # 异常情况，停止策略
        # 原有保证金需求
        marginNeedTotal = self.marginDict['IF'].marginNeed + self.marginDict['IH'].marginNeed + self.marginDict['IC'].marginNeed
        # 可用保证金小于所需保证金
        if self.account < marginNeedTotal:
            event1 = Event(type_=EVENT_RMSTOP)
            event1.dict_['data'] = 'name'
            self.eventEngine.put(event1)
            self.writeRiskLog(u'发生异常情况：可用保证金小于所需保证金，停止所有策略')
            print u'发生异常情况：可用保证金小于所需保证金，停止所有策略'


    # ----------------------------------------------------------------------
    def compareTime(self, time1, time2):
        """比较两个时间大小"""

    #----------------------------------------------------------------------
    def clearOrderFlowCount(self):
        """清空流控计数"""
        self.orderFlowCount = 0
        self.writeRiskLog(u'清空流控计数')
        
    #----------------------------------------------------------------------
    def clearTradeCount(self):
        """清空成交数量计数"""
        self.tradeCount = 0
        self.writeRiskLog(u'清空总成交计数')
        
    #----------------------------------------------------------------------
    def setOrderFlowLimit(self, n):
        """设置流控限制"""
        self.orderFlowLimit = n
        
    #----------------------------------------------------------------------
    def setOrderFlowClear(self, n):
        """设置流控清空时间"""
        self.orderFlowClear = n
        
    #----------------------------------------------------------------------
    def setOrderSizeLimit(self, n):
        """设置委托最大限制"""
        self.orderSizeLimit = n
        
    #----------------------------------------------------------------------
    def setTradeLimit(self, n):
        """设置成交限制"""
        self.tradeLimit = n
        
    #----------------------------------------------------------------------
    def setWorkingOrderLimit(self, n):
        """设置活动合约限制"""
        self.workingOrderLimit = n
        
    #----------------------------------------------------------------------
    def switchEngineStatus(self):
        """开关风控引擎"""
        self.active = not self.active
        
        if self.active:
            self.writeRiskLog(u'风险管理功能启动')
        else:
            self.writeRiskLog(u'风险管理功能停止')


########################################################################
class marginData(object):
    """保证金数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.long = EMPTY_INT          # 多头数量
        self.marginLong = EMPTY_FLOAT  # 多头保证金
        self.short = EMPTY_INT         # 空头数量
        self.marginShort = EMPTY_FLOAT # 空头保证金
        self.marginNeed = EMPTY_FLOAT  # 所需保证金
