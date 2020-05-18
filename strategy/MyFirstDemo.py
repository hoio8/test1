# encoding: UTF-8

# 导入策略所需各种模块
from __future__ import division
import ctaBase
import ctaTemplate
# from language.chinese.text import *
# from language.chinese.constant import *



# 定义策略类
class MyFirstDemo(ctaTemplate.CtaTemplate):
    '''超价发单'''
    vtSymbol = 'IF2005'
    exchange = 'CFFEX'
    className = 'MyFirstDemo'
    author = 'zhb'
    name = ctaBase.EMPTY_UNICODE # 策略实例名称

    # 策略参数
    P = 5400.0  # 买入触发价格
    V = 1   # 下单数量

    # 参数列表
    paramList = ['P',
                 'V']


    # 变量列表
    varList = ['trading',
               'pos']

    # 参数映射表
    paramMap = {'P': u'买触发价',
                'V': u'下单手数',
                'exchange': u'交易所',
                'vtSymbol': u'合约'}

    # 变量映射表
    varMap = {'trading': u'交易中',
              'pos': u'仓位'}

    # 初始化
    def __init__(self,ctaEngine=None,setting={}):
        """Constructor"""
        super(MyFirstDemo, self).__init__(ctaEngine,setting)

        self.P = 1
        self.V = 1

    # 编写行情处理函数
    # def onTick(self: ctaTemplate.CtaTemplate, tick: ctaBase.CtaTickData):
    def onTick(self, tick: ctaBase.CtaTickData):
        super(MyFirstDemo, self).onTick(tick)
        # 过滤集合竞价和涨跌停
        if tick.lastPrice == 0 or tick.askPrice1 == 0 or tick.bidPrice1 ==0:
            return
        if tick.lastPrice > self.P:
            self.orderID = self.buy_fak(tick.lastPrice,self.V)

    # 完善策略结构，继承并实现onStart和onTrade
    def onTrade(self: ctaTemplate.CtaTemplate, trade):
        super(MyFirstDemo,self).onTrade(trade, log = True)

    def onStart(self):
        super(MyFirstDemo, self).onStart()
