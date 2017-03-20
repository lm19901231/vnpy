# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 11:20:15 2017

@author: wxyc
"""

import talib as ta
import numpy as np

from ctaBase import *
from ctaTemplate import CtaTemplate


class TalibDoubleSmaDemo(CtaTemplate):
    """基于Talib模块的双指数均线策略Demo"""
    
    className = 'TalibDoubleSmaDemo'
    author = u'lm'
    
    # 策略参数
    fastPeriod = 5    # 快速均线参数
    slowPeriod = 20   # 慢速均线参数
    initDays = 5      # 初始化数据所用的天数
    
    # 策略变量
    bar = None
    barMinute = EMPTY_STRING
    
    closeHistory = []  # 缓存K线收盘价的数组
    maxHistory = 50    # 最大缓存数量
    
    fastMa0 = EMPTY_FLOAT  # 当前最新的快速均线数值
    fastMa1 = EMPTY_FLOAT  # 上一根的快速均线数值
    
    slowMa0 = EMPTY_FLOAT  # 慢速均线数值
    slowMa1 = EMPTY_FLOAT
    
    
    #  参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastPeriod',
                 'slowPeriod']
                 
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'fastMa0',
               'fastMa1',
               'slowMa0',
               'slowMa1']
 
    #---------------------------------------------------------------------- 
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TalibDoubleSmaDemo, self).__init__(ctaEngine, setting)
        self.vtSymbol = self.vtSymbol[0]
        print self.vtSymbol
        # 初始化持仓
        self.pos[self.vtSymbol] = 0
        print self.pos
        
    
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双SMA演示策略初始化')
        
        initData = self.loadBar(self.vtSymbol, self.initDays)
        for bar in initData:
            self.onBar(bar)
            
        self.putEvent()
        
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双SMA演示策略启动')
        self.putEvent()
        
        
    #----------------------------------------------------------------------    
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双SMA演示策略停止')
        self.putEvent()
    
    
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
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
#            bar.vloume = tick.volume
#            bar.openInterest = tick.openInterest
            
            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟
            
        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度
            
            bar.hign = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice
            
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        #　把最新的收盘价缓存到列表中
        self.closeHistory.append(bar.close)
        
        # 检查列表长度，如果超过缓存上限则移除最老的数据
        # 这样是为了减少计算用的数据量，提高速度
        if len(self.closeHistory) > self.maxHistory:
            self.closeHistory.pop(0)
        # 如果小于缓存上限，则说明初始化数据尚未足够，不进行后续计算
        else:
            return
        
        # 将缓存的收盘价数转化为numpy数组后，传入talib的函数SMA中计算
        closeArray = np.array(self.closeHistory)
        fastSMA = ta.SMA(closeArray, self.fastPeriod)
        slowSMA = ta.SMA(closeArray, self.slowPeriod)
        
        # 读取当前K线和上一根K线的数值，用于判断均线交叉
        self.fastMa0 = fastSMA[-1]
        self.fastMa1 = fastSMA[-2]
        self.slowMa0 = slowSMA[-1]
        self.slowMa1 = slowSMA[-2]
        
        # 判断买卖
        crossOver = self.fastMa0 > self.slowMa0 and self.fastMa1 < self.slowMa1  # 短线上穿长线，金叉
        crossBelow = self.fastMa0 < self.slowMa0 and self.fastMa1 > self.slowMa1  # 长线下穿短线，死叉
        
        # 金叉和死叉的条件是互斥
#        action = 1
        if crossOver:
            # 如果金叉时手头没有持仓，则直接做多
            if self.pos[bar.vtSymbol] == 0:
                print u'出现金叉，没有持仓.'
                self.buy(bar.close, 1, bar.vtSymbol)
            # 如果有空头持仓，则先平空，再做多
            elif self.pos[bar.vtSymbol] < 0:
                print u'出现金叉，有空头持仓'
                self.cover(bar.close, 1, bar.vtSymbol)
                self.buy(bar.close, 1, bar.vtSymbol)
            
        # 死叉和金叉相反
        elif crossBelow:
            if self.pos[bar.vtSymbol] == 0:
                print u'出现死叉，没有持仓'
                self.short(bar.close, 1, bar.vtSymbol)
            elif self.pos[bar.vtSymbol] > 0:
                print u'出现死叉，没有持仓'
                self.sell(bar.close, 1, bar.vtSymbol)
                self.short(bar.close, 1, bar.vtSymbol)
                
        # 发出状态更新事件
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        pass
            
            
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    