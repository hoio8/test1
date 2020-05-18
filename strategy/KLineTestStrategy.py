from ctaTemplate import *


class KLineTestStrategy(CtaTemplate):
    author = 'rock'
    className = 'KLineTestStrategy'

    # 参数列表
    paramList = ['exchange',
                 'vtSymbol']

    # 变量列表
    varList = ['trading',
               'pos']

    # 参数映射表
    paramMap = {'exchange': '交易所',
                'vtSymbol': '合约'}

    # 变量映射表
    varMap = {'trading': '交易中',
              'pos': '当前持仓'}

    def __init__(self, ctaEngine=None, setting={}):
        super(KLineTestStrategy, self).__init__(ctaEngine, setting)

        self.period = 15  # 15分钟周期

        self.bm = BarManager(self.onBar, self.period, self.on_xmin_bar)  # 分钟线
        self.am1 = ArrayManager(size=100)  # 分钟线
        self.am2 = ArrayManager(size=100)  # 日线

    def onTick(self, tick):
        super(KLineTestStrategy, self).onTick(tick)

    def onBar(self, bar):
        self.bm.updateBar(bar)

    def on_xmin_bar(self, bar):
        self.am1.updateBar(bar)

    def on_day_bar(self, bar):
        self.am2.updateBar(bar)

    def onStart(self):
        self.loadBar(2, func=self.onBar)
        self.loadDay(1, func=self.on_day_bar)
        super(KLineTestStrategy, self).onStart()
        self.manage_position()

    def onStop(self):
        super(KLineTestStrategy, self).onStop()
        self.output(self.am1.highArray)
        self.output(self.am2.highArray)
