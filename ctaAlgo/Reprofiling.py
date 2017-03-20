# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 11:20:15 2017

@author: wxyc
"""


from WindPy import *
from ctaBase import *
from ctaTemplate import CtaTemplate


class Reprofiling(CtaTemplate):
    """展期策略"""
    
    className = 'Reprofiling'
    author = u'leiming'
    
    # 策略参数
    spreadThreshold = 50  # 展期时，两个合约之间价差阈值
    w.start()

    
    # 策略变量
    bar = None

    vtSymbol1 = 'IF1703'
    vtSymbol2 = 'IF1704'

    price1 = EMPTY_FLOAT  # 合约1实时价格
    price2 = EMPTY_FLOAT  # 合约2实时价格
    
    
    
    #  参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol1',
                 'vtSymbol2',
                 'spreadThreshold']
                 
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'price1',
               'price2']
 
    #---------------------------------------------------------------------- 
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(Reprofiling, self).__init__(ctaEngine, setting)
        
    
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'展期策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
            
        self.putEvent()
        
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'展期策略启动')
        self.putEvent()
        
        
    #----------------------------------------------------------------------    
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'展期策略停止')
        self.putEvent()

            
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        #　把最新的收盘价缓存到列表中
        codeStr = self.vtSymbol1 + '.CFE,' + self.vtSymbol2 + '.CFE'

        data = w.wsq(codeStr, "rt_latest", func=DemoWSQCallback)

        [self.price1,self.price2] = data.Data

        while self.price1 - self.price2 < self.spreadThreshold
            self.buy(self.price1, 1)
            self.short(self.price2, 1)

                
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
            
            
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    