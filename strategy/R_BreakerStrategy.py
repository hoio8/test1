# encoding: UTF-8

"""
R-breaker 策略
类型：日内趋势追踪+反转策略
周期：1分钟、5分钟
根据前一个交易日的收盘价、最高价和最低价数据通过一定方式计算出六个价位，
从大到小依次为：
突破买入价（buy_break)、观察卖出价(sell_setup)、
反转卖出价(sell_enter)、反转买入价(buy_enter)、
观察买入价(buy_setup)、突破卖出价(sell_break)
以此来形成当前交易日盘中交易的触发条件。

交易规则：
反转:
持多单，当日内最高价超过观察卖出价后，盘中价格出现回落，且进一步跌破反转卖出价构成的支撑线时，采取反转策略，即在该点位反手做空；
持空单，当日内最低价低于观察买入价后，盘中价格出现反弹，且进一步超过反转买入价构成的阻力线时，采取反转策略，即在该点位反手做多；
突破:
在空仓的情况下，如果盘中价格超过突破买入价，则采取趋势策略，即在该点位开仓做多；
在空仓的情况下，如果盘中价格跌破突破卖出价，则采取趋势策略，即在该点位开仓做空；


注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
"""

from __future__ import division
from ctaBase import *
from ctaTemplate import *
import talib
import datetime



########################################################################
class R_BreakerStrategy(CtaTemplate):
    """R-breaker 日内趋势反转策略"""
    className = 'R_BreakerStrategy'

    # 策略参数
    observe_size = 0.03   #观察值
    reversal_size = 0.02  #反转值
    break_size = 0.04     #突破值
    W = 101  # 止盈
    A = 99  # 止损
    V = 1  # 每次下单的手数
    opPos = 10000  # 操作的总手数
    mPrice = 0.01  # 一跳的价格
    nMin = 1  # 操作级别分钟数
    initDays = 10  # 初始化数据所用的天数

    # 策略变量

    posPre = 0  # 持有的昨仓

    # 参数列表，保存了参数的名称
    paramList = ['opPos',
                 'observe_size',
                 'reversal_size',
                 'break_size',
                 'V',
                 'W',
                 'A',
                 'nMin']

    # 变量列表，保存了变量的名称
    varList = ['sell_setup',
              'sell_enter',
               'buy_enter',
               'buy_setup',
               'buy_break',
               'sell_break',
               'pos']

    # 突破买入价（buy_break)、观察卖出价(sell_setup)、
    # 反转卖出价(sell_enter)、反转买入价(buy_enter)、
    # 观察买入价(buy_setup)、突破卖出价(sell_break)
    # 仓位数量（pos)


    # 参数映射表，用于PythonGo的界面展示
    paramMap = {'observe_size':u'观察值',
                'reversal_size': u'反转值',
                'break_size': u'突破值',
                'A': u'止损指标',
                'V': u'下单手数',
                'BUPTH': u'穿越上下轨阈值',
                'opPos': u'交易仓位',
                'nMin': u'K线分钟',
                'vtSymbol': u'股票代码'}

    # 变量映射表，用于PythonGo的界面展示
    varMap = {'trading': u'运行中',
              'pos': u'日内单边仓位'}

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine=None, setting={}):
        """Constructor"""
        super(R_BreakerStrategy, self).__init__(ctaEngine, setting)

        self.bm = BarManager(self.onBar, self.nMin) # 创建K线合成器对象
        self.sell_setup= EMPTY_FLOAT# 初始化观察卖出价
        self.sell_enter= EMPTY_FLOAT# 初始化反转卖出价
        self.buy_enter= EMPTY_FLOAT # 初始化反转买入价
        self.buy_setup= EMPTY_FLOAT # 初始化观察买入价
        self.buy_break= EMPTY_FLOAT # 初始化突破买入价
        self.sell_break = EMPTY_FLOAT#初始化突破卖出价
        self.xdayBar=None            #初始化每个时刻的BAR数据
        self.posPre = self.opPos     #可操作的昨仓
        self.barDate = None          #初始化记录BAR数据的日期
        self.wOrderID= None          #初始化反转交易时的指令
        self.cost = EMPTY_FLOAT      #初始化成交价格
        self.prev_close = None       #初始化前一天的收盘价
        self.prev_high = None        #初始化前一天的最高价
        self.prev_low = None         #初始化前一天的最低价
        self.n=0                     #初始化天数的计数

        # 更新股票昨持仓
        for symbol in self.symbolList:
            self.crossSize[symbol] = 100
            self.ypos0L[symbol] = self.opPos

            # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
            # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
            # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
            # 策略时方便（更多是个编程习惯的选择）

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        # 过滤涨跌停和集合竞价
        if tick.lastPrice == 0 or tick.askPrice1 == 0 or tick.bidPrice1 == 0:
            return
        self.bm.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        super(R_BreakerStrategy, self).onBar(bar)
        bar.time=bar.datetime.strftime('%H:%M:%S')
        newDay = False  #初始化用于判断是否为新的一天的BAR数据

        if not self.xdayBar:#创建第一天数据的储存位置
            self.xdayBar = VtBarData()
            newDay = True


        elif bar.time=='15:00:00':  # 如果储存的时间是15:00:00，说明将开始新的一天
            #存储前一天的最高，最低，收盘价，同时初始化当日数据
            self.n=self.n+1#储存运行的天数
            self.prev_high = max(self.xdayBar.high,self.bar.open) #比较15:00:00的价格和14:59:59的价格得到最大值
            self.prev_low = min(self.xdayBar.low,self.bar.open) #比较15:00:00的价格和14:59:59的价格得到最小值
            self.prev_close = self.bar.open# 15:00:00 bar 的开盘价是15:00:00时刻的收盘价
            self.xdayBar = VtBarData()
            newDay = True

        if newDay:#储存新的一天的数据
            self.xdayBar.vtSymbol = bar.vtSymbol
            self.xdayBar.symbol = bar.symbol
            self.xdayBar.exchange = bar.exchange
            self.xdayBar.open = bar.open
            self.xdayBar.high = bar.high
            self.xdayBar.low = bar.low

            # 累加老K线
        else:
            #更新最高价，最低价
            self.xdayBar.high = max(self.xdayBar.high, bar.high)
            self.xdayBar.low = min(self.xdayBar.low, bar.low)

        # 通用部分

        self.xdayBar.close = bar.close
        self.xdayBar.openInterest = bar.openInterest
        self.xdayBar.volume += int(bar.volume)


    # ----------------------------------------------------------------------
    def getCtaIndictor(self, bar):
        #初始化
        if self.prev_close==None:
            return
        #第一天不计算指标，因为指标需要前一天的最高，最低和收盘价计算
        if self.n==1 or self.n==2 :
            return
        # 计算指标数值

        # 观察卖出价
        self.sell_setup = self.prev_high + self.observe_size * (self.prev_close - self.prev_low)

        # 反转卖出价
        self.sell_enter = (1 + self.reversal_size) / 2 * (
            self.prev_high + self.prev_low) - self.reversal_size * self.prev_low

        # 反转买入价
        self.buy_enter = (1 + self.reversal_size) / 2 * (
            self.prev_high + self.prev_low) - self.reversal_size * self.prev_high

        # 观察买入价
        self.buy_setup = self.prev_low - self.observe_size * (self.prev_high - self.prev_close)

        # 突破买入价
        self.buy_break = self.sell_setup + self.break_size * (self.sell_setup - self.buy_setup)

        # 突破卖出价
        self.sell_break = self.buy_setup + self.break_size * (self.sell_setup - self.buy_setup)

    # ----------------------------------------------------------------------
    def getCtaSignal(self, bar):
        """计算交易信号"""
        #初始化同上
        if self.prev_close==None:
            return
        # 第一天不计算交易信号，原因同上
        if self.n==2 or self.n==1:
            return

        pos = self.pos.get(self.xdayBar.vtSymbol)#仓位
        #尾盘时间的格式
        self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')
        close = bar.close
        hour = bar.datetime.hour
        minute = bar.datetime.minute
        # 定义尾盘，尾盘不交易并且空仓
        self.endOfDay = hour == 14 and minute >= 40

        # 判断是否要进行交易

        # 在空仓的情况下，如果盘中价格超过突破买入价，则采取趋势策略，即在该点位开仓做多；
        self.buySig = self.xdayBar.close > self.buy_break and pos==0
        # 在空仓的情况下，如果盘中价格跌破突破卖出价，则采取趋势策略，即在该点位开仓做空；
        self.shortSig = self.xdayBar.close < self.sell_break and pos==0
        #持空单，当日内最低价低于观察买入价后，盘中价格出现反弹，且进一步超过反转买入价构成的阻力线时，采取反转策略，即在该点位反手做多；
        self.coverSig = self.xdayBar.low < self.buy_setup and self.xdayBar.close > self.buy_enter and pos<0 or close <= self.cost-self.W*close or close >= self.cost+self.A*close
        #持多单，当日内最高价超过观察卖出价后，盘中价格出现回落，且进一步跌破反转卖出价构成的支撑线时，采取反转策略，即在该点位反手做空；
        self.sellSig = self.xdayBar.high > self.sell_setup and self.xdayBar.close < self.sell_enter and pos>0 or close >= self.cost+self.W*close or close <= self.cost-self.A*close

        # 交易价格
        self.longPrice = bar.close
        self.shortPrice = bar.close

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        super(R_BreakerStrategy, self).onTrade(trade, log=True)
        self.cost = trade.price
        # 更新昨仓
        if trade.direction == u'空':
            self.posPre -= trade.volume

    # 每次更新参数需要修改昨仓
    # ----------------------------------------------------------------------
    def setParam(self, setting):
        """刷新参数"""
        # 每次刷新参数需要修改，可操作的昨仓
        if 'opPos' in setting and not setting['opPos'] == self.opPos:
            self.posPre = self.opPos
        super(R_BreakerStrategy, self).setParam(setting)
        self.vtSymbol = str(self.vtSymbol)

    # ----------------------------------------------------------------------
    def onUpdate(self, setting):
        """刷新参数"""
        # 每次刷新参数需要修改，可操作的昨仓
        if 'opPos' in setting and not setting['opPos'] == self.opPos:
            self.posPre = self.opPos
        super(R_BreakerStrategy, self).onUpdate(setting)
        self.vtSymbol = str(self.vtSymbol)

    #----------------------------------------------------------------------
    def execSignal(self,volume):
        """简易交易信号执行"""
        pos = self.pos.get(self.xdayBar.vtSymbol)#c仓位
        endOfDay = self.endOfDay

        # 挂单未成交则撤销挂单
        if not self.orderID is None:
            self.cancelOrder(self.orderID)
        if not self.wOrderID is None:
            self.cancelOrder(self.wOrderID)
        # 当前无仓位同时没有在执行的委托单
        if pos == 0 and not self.endOfDay and self.orderID==None and self.wOrderID==None :
            # 买开，卖开
            if self.shortSig:
                self.orderID = self.short(self.shortPrice, volume)
            elif self.buySig:
                self.orderID = self.buy(self.longPrice, volume)
        #在尾盘时刻，持有多头仓位同时没有在执行的委托单，则平多单，保持尾盘没有任何仓位
        elif pos > 0 and self.endOfDay and self.orderID==None and self.wOrderID==None:
            self.orderID = self.sell(self.shortPrice, pos)
            return
        # 持有多头仓位同时没有在执行的委托单，接收到反转信号后，平多单，并反手做空
        elif pos > 0 and self.sellSig and self.orderID==None and self.wOrderID==None :
                self.orderID = self.sell(self.shortPrice, pos)
                self.wOrderID = self.short(self.shortPrice, volume)

        # 在尾盘时刻，持有空头仓位同时没有在执行的委托单，则平空单，保持尾盘没有任何仓位
        elif pos<0 and self.endOfDay and self.orderID==None and self.wOrderID==None:
            self.orderID = self.cover(self.longPrice, -pos)
            return
        # 持有空头仓位同时没有委托单，接收到反转信号后，平空单，并反手做多
        elif pos < 0 and self.coverSig and self.orderID==None and self.wOrderID==None :
                self.orderID = self.cover(self.longPrice, -pos)
                self.wOrderID = self.buy(self.longPrice, volume)


    #----------------------------------------------------------------------
    def onOrderCancel(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        if order.orderID == self.orderID:
            self.orderID = None
        if order.orderID == self.wOrderID:
            self.wOrderID = None

    #----------------------------------------------------------------------
    def onOrderTrade(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        if order.orderID == self.orderID:
            self.orderID = None
        if order.orderID == self.wOrderID:
            self.wOrderID = None
