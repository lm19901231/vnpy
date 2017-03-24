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
        self.accountFreeze = EMPTY_FLOAT    # 冻结可用资金
        self.posFreezeDict = {}             # 账户冻结持仓
        self.margin = EMPTY_FLOAT           # 保证金
        self.marginRatioIC = 0.41           # 保证金比例
        self.marginRatioIFIH = 0.41
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
        self.eventEngine.register(EVENT_ORDER, self.updateFreeze)      # 报单回报事件
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
        trade = event.dict_['data']
        # 判断是否为历史报单
        if self.startTime > trade.orderTime:
            # print u'历史报单'
            # print trade.vtSymbol, trade.vtOrderID, trade.status, trade.orderTime, trade.offset, trade.direction
            pass
        else:
            vtOrderID = trade.vtOrderID
            vtSymbol = trade.vtSymbol
            # 新的订单
            if vtOrderID not in self.orderDict:
                self.orderDict[vtOrderID] = trade
                # 开仓减少冻结保证金（因为开仓时可用保证金会减少，冻结保证金需同步减少）
                if trade.offset == OFFSET_OPEN:
                    if re.match('IH|IF', vtSymbol):
                        self.accountFreeze -= trade.totalVolume * trade.price * 300 * self.marginRatioIFIH  # 报单数量乘以保证金
                    else:
                        self.accountFreeze -= trade.totalVolume * trade.price * 200 * self.marginRatioIC  # 报单数量乘以保证金
            # 已有的订单
            else:
                if trade.offset == OFFSET_OPEN:
                    # 开仓撤单增加冻结保证金（因为开仓撤单时可用保证金会增加，冻结保证金需同步增加）
                    if trade.status == STATUS_CANCELLED:
                        if re.match('IH|IF', vtSymbol):
                            self.accountFreeze += trade.totalVolume * trade.price * 300 * self.marginRatioIFIH  # 报单数量乘以保证金
                        else:
                            self.accountFreeze += trade.totalVolume * trade.price * 200 * self.marginRatioIC  # 报单数量乘以保证金

                elif trade.offset == OFFSET_CLOSE:
                    # 平仓成交减少冻结持仓（因为平仓成交会导致持仓会减少，冻结持仓需同步减少）
                    if trade.status == STATUS_ALLTRADED:
                        # 多头平仓
                        if trade.direction == DIRECTION_LONG:
                            self.posFreezeDict[vtSymbol].shortPosition -= trade.totalVolume  # 空头减少
                        # 空头平仓
                        elif trade.direction == DIRECTION_SHORT:
                            self.posFreezeDict[vtSymbol].longPosition -= trade.totalVolume  # 多头减少


            print u'冻结保证金', self.accountFreeze
            print u'冻结持仓', self.posFreezeDict


    # ----------------------------------------------------------------------
    def strategyCheck(self, req, posBufferDict):
        """策略需求检查"""
        # by lm
        # 开仓检查保证金，平仓检查是否有持仓

        # 读取持仓和保证金情况
        for vtSymbol in req:
            require = req[vtSymbol]  # [方向，数量]
            # 开仓检查保证金
            if require[0] == u'买开' or require[0] == u'卖开':

                # 确定保证金
                if re.match('IF|IH', vtSymbol):
                    self.margin = self.marginRatioIFIH * self.tickDict[vtSymbol] * 300
                else:
                    self.margin = self.marginRatioIC * self.tickDict[vtSymbol] * 200

                # 真实可用保证金为：可用保证金 - 冻结保证金
                realMargin = self.account - self.accountFreeze

                # 所需保证金小于真实可用保证金
                if require[1] * self.margin <= realMargin:
                    self.accountFreeze += require[1] * self.margin  # 冻结保证金
                    print u'冻结保证金', self.accountFreeze
                    return True
                else:
                    print u'保证金不足'
                    return False

            # 买入平仓检查是否有持仓
            elif require[0] == u'买平':
                # 真实可用持仓为：持仓 - 冻结持仓
                if vtSymbol in self.posFreezeDict:
                    realPos = posBufferDict[vtSymbol].shortPosition - self.posFreezeDict[vtSymbol].shortPosition
                else:
                    posBuffer = PositionBuffer()
                    posBuffer.vtSymbol = vtSymbol
                    self.posFreezeDict[vtSymbol] = posBuffer
                    realPos = posBufferDict[vtSymbol].shortPosition

                # 平仓数量小于等于真实可用持仓
                if require[1] <= realPos:
                    self.posFreezeDict[vtSymbol].shortPosition += require[1]   # 冻结持仓
                    print u'冻结持仓', self.posFreezeDict[vtSymbol].shortPosition
                    return True
                else:
                    print u'空头持仓不足以平仓'
                    return False

            # 卖出平仓检查是否有持仓
            else:
                # 真实可用持仓为：持仓 - 冻结持仓
                if vtSymbol in self.posFreezeDict:
                    realPos = posBufferDict[vtSymbol].longPosition - self.posFreezeDict[vtSymbol].longPosition
                else:
                    posBuffer = PositionBuffer()
                    posBuffer.vtSymbol = vtSymbol
                    self.posFreezeDict[vtSymbol] = posBuffer
                    realPos = posBufferDict[vtSymbol].longPosition

                    # 平仓数量小于等于真实可用持仓
                if require[1] <= realPos:
                    self.posFreezeDict[vtSymbol].longPosition += require[1]  # 冻结持仓
                    print u'冻结持仓', self.posFreezeDict[vtSymbol].longPosition
                    return True
                else:
                    print u'多头持仓不足以平仓'
                    return False

    # ----------------------------------------------------------------------
    def abnormalCheck(self):
        """异常事件检查"""
        # by lm
        # 异常情况，停止策略
        if self.accountFreeze < 0 or self.posFreezeDict < 0:
            event1 = Event(type_=EVENT_RMSTOP)
            event1.dict_['data'] = 'name'
            self.eventEngine.put(event1)


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
