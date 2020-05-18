# encoding: UTF-8

"""
超过价格发单

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
"""

from __future__ import division
from ctaBase import *
from ctaTemplate import *


########################################################################
class DEMOStrategy(CtaTemplate):
    """超过价格发单"""
    vtSymbol = 'rb1801'
    exchange = 'SHFE'
    className = 'DEMOStrategy'
    author = u'binbinwei'
    name = EMPTY_UNICODE                # 策略实例名称

    # 参数列表，保存了参数的名称
    paramList = ['P',
                 'V']

    # 变量列表，保存了变量的名称
    varList = ['trading',
               'pos']

    # 参数映射表
    paramMap = {'P'   :u'买触发价',
                'V'   :u'下单手数',
                'exchange':u'交易所',
                'vtSymbol':u'合约'}

    # 变量映射表
    varMap   = {'trading' :u'交易中',
                'pos'     :u'仓位'}


    #----------------------------------------------------------------------
    def __init__(self,ctaEngine=None,setting={}):
        """Constructor"""
        super(DEMOStrategy, self).__init__(ctaEngine,setting)

        self.P = 100                            # 买入触发价
        self.V = 1                               # 下单手数
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        super(DEMOStrategy, self).onTick(tick)
        # 过滤涨跌停和集合竞价
        if tick.lastPrice == 0 or tick.askPrice1==0 or tick.bidPrice1==0:
            return
        if tick.lastPrice > self.P:
            self.orderID = self.buy_fak(tick.lowerLimit, self.V)

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        super(DEMOStrategy, self).onTrade(trade,log=True)

    #----------------------------------------------------------------------
    def onStart(self):
        super(DEMOStrategy, self).onStart()
