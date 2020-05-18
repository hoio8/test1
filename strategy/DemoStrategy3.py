# encoding: UTF-8
"""
监控龙头一行情，在某段时间如5分钟、10分钟、15分价格突破预先设置好的涨跌幅时买入龙二
通过对目标仓位的控制停止继续发单
"""

from __future__ import division
from ctaTemplate import *
import datetime


class DemoStrategy3(CtaTemplate):
    """龙一龙二策略"""
    className = u'DemoStrategy3'
    author = u'rock'

    # 参数列表
    # 填写合约列表和交易所时，使用“;”分开，如
    # ag1812;a1809
    # SHFE;DCE
    paramList = ['vtSymbol',
                 'exchange',
                 'preset_rise',
                 'nmin',
                 'volume',
                 'max_pos']

    # 变量列表
    varList = ['trading',
               'time',
               'pos']

    # 参数映射表
    paramMap = {'vtSymbol': u'合约列表',
                'exchange': u'交易所',
                'preset_rise': u'预设涨幅（%）',
                'nmin': u'校验分钟间隔',
                'volume': u'下单手数',
                'max_pos': u'最大持仓'}

    # 变量映射表
    varMap = {'trading': u'交易中',
              'time': u'当前时间',
              'pos': u'当前持仓'}

    def __init__(self, ctaEngine=None, setting={}):
        """Constructor"""
        super(DemoStrategy3, self).__init__(ctaEngine, setting)
        self.preset_rise = 1  # 涨百分之一
        self.nmin = 5
        self.volume = 1
        self.max_pos = 10
        self.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.tick_symbol_1 = VtTickData()
        self.tick_symbol_2 = VtTickData()
        # 标注上一个报单是否已被撤单
        self.has_canceled = False
        # 计算龙二购买信号触发条件的起始价位
        self.trigger_open = 0
        self.trigger_price = 0
        # 龙一前（nmin - 1）分钟的最低价缓存对象
        self.queue = None

        self.bar = VtBarData()
        self.bm = BarManager(self.onBar)
        self.am = ArrayManager(size=100)

    def onTick(self, tick):
        super(DemoStrategy3, self).onTick(tick)
        # 过滤涨跌停和集合竞价
        if tick.lastPrice == 0 or tick.askPrice1 == 0 or tick.bidPrice1 == 0:
            return

        # 更新时间，推送状态
        self.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.putEvent()

        # 分别缓存不同合约的上一个tick
        if tick.vtSymbol == self.symbolList[0]:
            self.tick_symbol_1 = tick
            # 更新龙一K线数据
            self.bm.updateTick(tick)
        if tick.vtSymbol == self.symbolList[1]:
            self.tick_symbol_2 = tick

        # 计算交易指标
        self.get_indicator()

        # 计算交易信号
        self.get_signal(self.tick_symbol_1)

        # 执行交易信号
        self.exec_signal(self.tick_symbol_2)

    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # super(DemoStrategy3, self).onBar(bar)
        if bar.vtSymbol == self.symbolList[0]:
            self.bar = bar
            if not self.am.updateBar(self.bar):
                return None
        # 记录龙一前（nmin - 1）分钟的最低价
        if self.nmin > 1:
            self.queue = self.am.lowArray[int('-{}'.format(self.nmin)):-1]
            self.trigger_open = self.queue.min()
        if self.nmin == 1:
            self.trigger_open = self.bar.low

    def get_indicator(self):
        self.trigger_price = self.trigger_open * (1 + self.preset_rise / 100.0)

    def get_signal(self, tick):
        if tick.lastPrice >= self.trigger_price:
            self.buySig = True

    def exec_signal(self, tick):
        if self.buySig:
            # 按涨停价第一时间发单，不成交立即撤单
            # 当龙二仓位小于预设最大持仓的时候，才可以发单
            if self.pos.get(self.symbolList[1]) >= self.max_pos:
                if self.orderID is not None:
                    self.cancelOrder(self.orderID)
                self.output(u'已到达最大持仓上限，无法继续下单')
                return None
            # 第一个tick推过来肯定是龙一的tick，所以此时需要确保缓存的龙二的tick数据不为空
            if tick.upperLimit > 0:
                self.orderID = self.buy(tick.upperLimit, self.volume, symbol=self.symbolList[1])
            self.has_canceled = False

    def onTrade(self, trade, log=True):
        super(DemoStrategy3, self).onTrade(trade, log)

    def onOrder(self, order, log=False):
        super(DemoStrategy3, self).onOrder(order, log)
        if order is None:
            return None
        if order.status == u'未成交' and self.orderID is not None and self.has_canceled is False:
            self.cancelOrder(self.orderID)
            self.has_canceled = True
        # 当前持仓到达最大持仓时，撤单
        if self.pos.get(self.symbolList[1]) >= self.max_pos:
            if self.orderID is not None:
                self.cancelOrder(self.orderID)

    def onStart(self):
        self.loadBar(1, symbol=self.symbolList[0])
        super(DemoStrategy3, self).onStart()
        self.manage_position()

    def onStop(self):
        super(DemoStrategy3, self).onStop()
