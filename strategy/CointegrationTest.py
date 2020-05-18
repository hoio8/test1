# encoding: UTF-8

"""
协整检验价差日内趋势策略
类型：日内趋势追踪
周期：1分钟

先计算出价差判断是否协整
在协整的情况下，以下情况进行发单：

价差超过n倍标准差的上沿，做空价差，即做空合约1，做多合约2
价差回到均线则反向平仓

价差超过n倍标准差的下沿，做多价差，即做空合约1，做多合约2
价差回到均线则反向平仓

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
"""

from __future__ import division
from ctaBase import *
from ctaTemplate import *
import talib
import datetime
import pandas as pd
import numpy as np
import statsmodels.api as sm

########################################################################
class CointegrationTest(CtaTemplate):
    """协整检验价差日内趋势策略"""

    className = 'CointegrationTest'

    # 策略参数

    price_tick = 5        # 合约1 最小变动单位
    price_tick1 = 1       # 合约2 最小变动单位
    W=3                   # 止盈多少个最小变动单位
    A=2                   # 止损多少个最小变动单位
    V = 1                 # 每次下单的手数
    K=2                   # 标准差宽度
    opPos = 10000         # 操作的总手数
    mPrice = 0.01         # 一跳的价格
    nMin = 1              # 操作级别分钟数
    initDays = 10         # 初始化数据所用的天数
    overprice=0.01        # 合约成交超价百分比
    vtSymbol=u'zn1712;ag1712'   # 合约

    n=300
    # 策略变量

    # 参数列表，保存了参数的名称
    paramList = ['opPos',
                 'V',
                 'K',
                 'price_tick',
                 'price_tick1',
                 'vtSymbol',
                 'W',
                 'n',
                 'A',
                 'overprice',
                 'nMin']

    # 变量列表，保存了变量的名称
    varList = [ 'position',
                'position1',
                'first_Ctest',
                'close'
               ]


    # 参数映射表，用于PythonGo的界面展示
    paramMap = {'K': u'标准差倍数',
                'V': u'下单手数',
                'price_tick':u'最小价1',
                'price_tick1':u'最小价2',
                'W':u'止盈（跳）',
                'A':u'止损（跳）',
                'overprice':u'超价百分比',
                'opPos': u'交易仓位',
                'n':u'协整检验样本数',
                'nMin': u'K线分钟',
                'exchange': u'交易所',
                'vtSymbol': u'合约'}

    # 变量映射表，用于PythonGo的界面展示

    varMap = {'trading': u'运行中',
              'first_Ctest': u'协整检验',
              'close': u'价差',
              'position': u'合约1仓位',
              'position1':u'合约2仓位'}

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine=None, setting={}):
        """Constructor"""
        super(CointegrationTest, self).__init__(ctaEngine, setting)
        self.bm = BarManager(self.onBar, self.nMin)     # 创建合约1 K线合成器对象
        self.bm1 = BarManager(self.onBar, self.nMin)    # 创建合约2 K线合成器对象
        self.orderID=None                               # 初始化合约1 交易时的指令
        self.orderID1=None                              # 初始化合约2 交易时的指令
        self.cost = EMPTY_FLOAT                         # 初始化合约1 成交价
        self.cost1=EMPTY_FLOAT                          # 初始化合约2 成交价
        self.data_num=0                                 # 初始化bar个数的计数
        self.barTime=None                               # 初始化成交时间
        self.bar0=VtBarData()                           # 初始化合约1 bar
        self.bar1=VtBarData()                           # 初始化合约2 bar
        self.close_std=None                             # 价差的标准差
        self.close_mean=None                            # 价差的均价
        self.close=EMPTY_FLOAT                          # 价差
        self.limitmove=False                            # 初始化合约1 涨跌停判断
        self.limitmove1=False                           # 初始化合约2 涨跌停判断
        self.first_Ctest=False                          # 初始化协整检验判断
        self.endOfDay=False                             # 初始化 尾盘状态
        self.openofDay=False                            # 初始化 开盘
        self.first_Ctest = False                        # 初始化协整检验
        self.first_update=False                         # 初始化更新状态
        self.am=ArrayManager(size=self.n)               # 初始化做协整检验样本
        self.position= EMPTY_FLOAT                      # 初始化合约1 仓位
        self.position1=EMPTY_FLOAT                      # 初始化合约2 仓位




        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        super(CointegrationTest, self).onTick(tick)
        self.vtSymbol1 = self.vtSymbol.split(';')[0]  # 合约1 代码
        self.vtSymbol2 = self.vtSymbol.split(';')[1]  # 合约2 代码
        # 过滤涨跌停和集合竞价
        if tick.lastPrice == 0 or tick.askPrice1 == 0 or tick.bidPrice1 == 0:
            return
        #如果涨跌停则停止交易
        if tick.vtSymbol == self.vtSymbol1:
            self.bm.updateTick(tick)

            self.limitmove= tick.lastPrice == 0 or tick.askPrice1 == tick.upperLimit or tick.bidPrice1 == tick.lowerLimit

        elif tick.vtSymbol == self.vtSymbol2:
            self.bm1.updateTick(tick)
            self.limitmove1= tick.lastPrice == 0 or tick.askPrice1 == tick.upperLimit or tick.bidPrice1 == tick.lowerLimit

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        #统一两个合约的时间轴，并计算更新价差
        self.vtSymbol1 = self.vtSymbol.split(';')[0]  # 合约1 代码
        self.vtSymbol2 = self.vtSymbol.split(';')[1]  # 合约2 代码

        if bar.vtSymbol == self.vtSymbol1:
            self.bar0 = bar
            self.bar0.datetime = bar.datetime.replace(second=0, microsecond=0)
            # self.output(self.bar0.close)
            if self.bar1.datetime == bar.datetime.replace(second=0, microsecond=0):
                dBar = VtBarData()
                dBar.datetime = bar.datetime.replace(second=0, microsecond=0)
                dBar.close = bar.close - self.bar1.close
                dBar.open = bar.open - self.bar1.open
                self.first_update=self.am.updateBar(dBar)
            else:
                return

        elif bar.vtSymbol == self.vtSymbol2:
            self.bar1 = bar
            self.bar1.datetime = bar.datetime.replace(second=0, microsecond=0)
            if self.bar0.datetime == bar.datetime.replace(second=0, microsecond=0):
                dBar = VtBarData()
                dBar.datetime = bar.datetime.replace(second=0, microsecond=0)
                dBar.close = self.bar0.close-bar.close
                dBar.open =  self.bar0.open-bar.open
                self.first_update = self.am.updateBar(dBar)
            else:
                return

        #每n个bar 数据重新进行协整检验，通过则更新数据
        if self.first_update:#判断更新的样本是否存满

            if self.data_num % self.n == 0:
                self.first_Ctest=False
                result = sm.tsa.stattools.adfuller(self.am.close)   #协整检验结果

                if result[4]['5%'] > result[0] and result[4]['10%'] > result[0] and result[4]['1%'] > result[0] and abs(result[1]) < 0.05:
                    self.close_std = np.std(self.am.close, ddof=1)  # 标准差
                    self.close_mean=np.mean(self.am.close)          # 平均值
                    self.first_Ctest=True                           # 通过检验判断
            self.data_num = self.data_num + 1  # 进行bar 的计数

        self.close = self.am.close[-1]  # 获取最新价差

        # --------------------------------------------------------------------
        '''如果通过检验，计算交易信号'''
        if self.first_Ctest:

            # 定义尾盘，尾盘不交易并且空仓
            hour = bar.datetime.hour
            minute = bar.datetime.minute
            self.endOfDay = hour == 14 and minute >= 40
            if self.endOfDay:
                self.openofDay=False

            #定义开盘
            if hour == 9 and minute == 0 or hour==21 and minute==0:
                self.openofDay=True

            self.position = self.pos.get(self.vtSymbol1)   #第一个合约仓位
            self.position1= self.pos.get(self.vtSymbol2)  #第二个合约仓位

            #最小变动单位设置
            self.sellsig_stop=False
            self.coversig_stop=False

            if self.price_tick== self.price_tick1:             #如果最小变动单位一样，则选其中一个
                tick_change=self.price_tick
            else:
                tick_change=self.price_tick-self.price_tick1   #两合约的最小变动单位价差

            # 止盈止损判断
            if self.position>0 and self.position1<0:
                self.sellsig_stop= self.close >= (self.cost-self.cost1)+self.W*tick_change or self.close <= (self.cost-self.cost1)-self.A*tick_change

            if self.position<0 and self.position1>0:
                self.coversig_stop =self.close <= (self.cost-self.cost1)-self.W*tick_change or self.close >= (self.cost-self.cost1)+self.A*tick_change

            #交易信号判断

            # 开仓做多合约1，做空合约2；
            self.buySig = self.close_mean-self.close>self.close_std*self.K and self.position==0 and self.position1==0
            # 开仓做空合约1，做多合约2；
            self.shortSig = self.close-self.close_mean>self.close_std*self.K and self.position==0 and self.position1==0
            #持合约1空单和合约2多单，到均线平仓；
            self.coverSig = self.close<self.close_mean and self.position<0 and self.position1>0 or self.coversig_stop
            #持合约1多单和合约2空单，到均线平仓；
            self.sellSig = self.close>self.close_mean and self.position>0 and self.position1<0 or self.sellsig_stop

            # 交易价格,以超价进行交易
            self.longPrice =self.bar0.close*(1 + self.overprice)
            self.longPrice1=self.bar1.close*(1 + self.overprice)
            self.shortPrice = self.bar0.close*(1-self.overprice)
            self.shortPrice1= self.bar1.close*(1-self.overprice)


            #---------------------------------------------------------------

            '''挂单交易'''
            volume=self.V #合约手数

            # 空仓的同时没有在执行的委托单以及没有涨跌停
            if self.position == 0 and self.position1==0 and not self.endOfDay  and self.openofDay and self.orderID == None and self.orderID1 == None \
                    and not self.limitmove and not self.limitmove1:
                # 买开，卖开
                if self.shortSig:
                    self.orderID = self.short_fok(self.shortPrice, volume, self.vtSymbol1)
                    self.orderID1 = self.buy_fok(self.longPrice1, volume, self.vtSymbol2)

                elif self.buySig:
                    self.orderID = self.buy_fok(self.longPrice, volume, self.vtSymbol1)
                    self.orderID1 = self.short_fok(self.shortPrice1, volume, self.vtSymbol2)

            # 尾盘清空仓位
            elif self.position > 0 and self.position1 < 0  and self.endOfDay and self.orderID == None and self.orderID1 == None \
                    and not self.limitmove and not self.limitmove1 :
                self.orderID = self.sell_fok(self.shortPrice, self.position, self.vtSymbol1)
                self.orderID1 = self.cover_fok(self.longPrice1, -self.position1, self.vtSymbol2)
                return

            # 反转做空价差
            elif self.position > 0 and self.position1 < 0  and self.sellSig and self.orderID == None and self.orderID1 == None \
                    and not self.limitmove and not self.limitmove1 :
                self.orderID = self.sell_fok(self.shortPrice, self.position, self.vtSymbol1)
                self.orderID1 = self.cover_fok(self.longPrice1, -self.position1, self.vtSymbol2)

            # 尾盘清空仓位
            elif self.position < 0 and self.position1 > 0  and self.endOfDay  and self.orderID == None and self.orderID1 == None \
                    and not self.limitmove and not self.limitmove1 :
                self.orderID = self.cover_fok(self.longPrice, -self.position, self.vtSymbol1)
                self.orderID1 = self.sell_fok(self.shortPrice1, self.position1, self.vtSymbol2)
                return

            # 反转做多价差
            elif self.position < 0 and self.position1 > 0  and self.coverSig  and self.orderID == None and self.orderID1 == None \
                    and not self.limitmove and not self.limitmove1 :
                self.orderID = self.cover_fok(self.longPrice, -self.position, self.vtSymbol1)
                self.orderID1 = self.sell_fok(self.shortPrice1, self.position1, self.vtSymbol2)

        self.putEvent()


    # # ----------------------------------------------------------------------
    def loadBar(self, days, symbol='',exchange=''):
        """载入K线"""
        super(CointegrationTest, self).loadBar(days)
        l_symbol = len(self.vtSymbol.split(';'))#合约个数
        l_list = []
        try:
            for i in range(l_symbol):
                symbol1 = self.vtSymbol.split(';')[i] if symbol == '' else symbol
                exchange1 = self.exchange.split(';')[i] if exchange == '' else exchange
                #载入历史合约数据
                url = 'http://122.144.129.233:60007/hismin?instrumentid={}&datatype=0&exchangeid={}&startday={}&secretkey=1&daynum={}&rtnnum=20'.format(
                    symbol1, exchange1, datetime.datetime.now().strftime('%Y%m%d'), days)
                r = requests.post(url)
                l = json.loads(r.text)
                l.reverse()
                #合约相间排列
                for j in range(len(l)):
                    l_list.insert(2 * j, l[j])

            for d in l_list:
                #制作BAR 数据
                bar = VtBarData()
                bar.vtSymbol = d['InstrumentID']
                bar.symbol = d['InstrumentID']
                for i in range(l_symbol):
                    if d['InstrumentID']==self.vtSymbol.split(';')[i]:
                        bar.exchange = self.exchange.split(';')[i]
                bar.open = d['OpenPrice']
                bar.high = d['HighestPrice']
                bar.low = d['LowestPrice']
                bar.close = d['ClosePrice']
                bar.volume = d['Volume']
                bar.turnover = d['Turnover']
                bar.datetime = datetime.datetime.strptime(d['ActionDay'] + d['UpdateTime'], '%Y%m%d%H:%M:%S')
                self.onBar(bar)
        except:
            self.output(u'历史数据获取失败，使用实盘数据初始化')


    #----------------------------------------------------------------------
    def onTrade(self, trade):
        '''交易日志'''
        super(CointegrationTest, self).onTrade(trade, log=True)
        #记录合约成交价
        if self.vtSymbol1 == trade.vtSymbol:
            self.cost=trade.price
        if self.vtSymbol2==trade.vtSymbol:
            self.cost1=trade.price

    #----------------------------------------------------------------------
    def onOrderCancel(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        if order.orderID == self.orderID:
            self.orderID = None
        if order.orderID==self.orderID1:
            self.orderID1=None

    #----------------------------------------------------------------------
    def onOrderTrade(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        if order.orderID == self.orderID:
            self.orderID = None
        if order.orderID==self.orderID1:
            self.orderID1=None


    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.loadBar(3)

        super(CointegrationTest, self).onStart()
