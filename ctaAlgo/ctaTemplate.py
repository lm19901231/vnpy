# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''

from ctaBase import *
from vtConstant import *


########################################################################
class CtaTemplate(object):
    """CTA策略模板"""

    # 策略类的名称和作者
    className = 'CtaTemplate'
    author = EMPTY_UNICODE

    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME

    # 策略的基本参数
    name = EMPTY_UNICODE         # 策略实例名称
    vtSymbol = EMPTY_STRING      # 交易的合约vt系统代码
    vtSymbolList = []            # 合约列表
    productClass = EMPTY_STRING  # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING      # 货币（只有IB接口需要）

    # 策略的基本变量，由引擎管理
    inited = False       # 是否进行了初始化
    trading = False      # 是否启动交易，由引擎管理
    pos = {}             # 持仓情况，支持多合约，使用dict结构存储
    req = {}             # 策略需求，用于风控检查，提前锁定资金

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine

        # 设置策略的参数
        if setting:
            # d = self.__dict__
            # for key in self.paramList:
            #     if key in setting:
            #         d[key] = setting[key]
            #     if key == 'vtSymbol':
            self.vtSymbolList = setting['vtSymbol'].split(',')
            print self.vtSymbolList
                # print 'vtSymbol', self.vtSymbol

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def buy(self, price, volume, vtSymbol, stop=False):
        """买开"""
        return self.sendOrder(CTAORDER_BUY, price, volume, vtSymbol, stop)

    # ----------------------------------------------------------------------
    def sell(self, price, volume, vtSymbol, stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, vtSymbol, stop)

        # ----------------------------------------------------------------------

    def short(self, price, volume, vtSymbol, stop=False):
        """卖开"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, vtSymbol, stop)

        # ----------------------------------------------------------------------

    def cover(self, price, volume, vtSymbol, stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER, price, volume, vtSymbol, stop)

    # ----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, vtSymbol, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(vtSymbol, orderType, price, volume, self)
            return vtOrderID
        else:
            # 交易停止时发单返回空字符串
            return ''

            # ----------------------------------------------------------------------

    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return

        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)

    # ----------------------------------------------------------------------
    def requireCheck(self, req):
        """策略需求检查（必须由用户继承实现）"""
        if req:
            return self.ctaEngine.requireCheck(req)
        else:
            print u'没有提交需求检查'
            return False

    # ----------------------------------------------------------------------
    def insertTick(self, vtSymbol, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, vtSymbol, tick)

    # ----------------------------------------------------------------------
    def insertBar(self, vtSymbol, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, vtSymbol, bar)

    # ----------------------------------------------------------------------
    def loadTick(self, vtSymbol, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, vtSymbol, days)

    # ----------------------------------------------------------------------
    def loadBar(self, vtSymbol, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, vtSymbol, days)

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)

    # ----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)

    # ----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType



