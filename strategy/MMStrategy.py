# encoding: UTF-8

"""
期货做市策略

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 本策略需要用到talib，没有安装的用户请先参考www.vnpy.org上的教程安装
"""
from __future__ import division
import os
import sys
import datetime
from ctaBase import *
from ctaTemplate import *
from qtpy.QtCore import Qt
from qtpy.QtWidgets import *
from qtpy import QtGui, QtCore

ORDER_LONGOPEN = 0
ORDER_LONGCLOSE = 1
ORDER_SHORTOPEN = 2
ORDER_SHORTCLOSE = 3

ORDER_LONG = 0
ORDER_SHORT = 1
ORDER_LONGSHORT = 2

# 字符串转换
# ---------------------------------------------------------------------------------------
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


########################################################################
class MMStrategy(CtaTemplate):
    """期货做市策略"""
    # vtSymbol = 'rb1801'
    # exchange = 'SHFE'
    className = 'MMStrategy'
    author = u'rock'
    # name = EMPTY_UNICODE  # 策略实例名称

    # 参数列表，保存了参数的名称
    paramList = ['vtSymbol',
                 'exchange',
                 'investors',
                 'pOffset',
                 'pSpread',
                 'stopOnTrade',
                 'stopOnSpread',
                 'volume',
                 'mPrice']

    # 变量列表，保存了变量的名称
    varList = ['trading',
               'pos']

    # 参数映射表
    paramMap = {'vtSymbol': u'合约',
                'exchange': u'交易所',
                'investors': u'投资者账户',
                'pOffset': u'价格偏移',
                'pSpread': u'报价宽度',
                'stopOnTrade': u'成交后停止',
                'stopOnSpread': u'价差阈值',
                'volume': u'报价数量',
                'mPrice': u'最小价格变动'}

    # 变量映射表
    varMap = {'trading': u'交易中'}

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine=None, setting={}):
        """Constructor"""
        self.widgetClass = TradingWidget
        self.widget = None
        self.vtSymbol = ''
        self.exchange = ''
        self.excSymbol = ''  # 做市合约
        self.hedgeSymbol = ''  # 对冲合约
        self.pOffset = 0  # 价格偏移
        self.volume = 1  # 报价数量
        # 撤单的最大次数
        self.pLimit = 2  # 撤单阈值
        self.pSpread = 2  # 报价宽度
        self.mPrice = 1  # 最小价格变动
        self.upPrice = {}  # 涨停价
        self.lowPrice = {}  # 跌停价
        self.askPrice1 = {}  # 卖盘价1
        self.bidPrice1 = {}  # 买盘价1
        self.midPrice = {}  # 盘口中价
        self.askVolume1 = {}  # 卖盘量1
        self.bidVolume1 = {}  # 买盘量1
        self.tickers = {}  # 所有切片
        self.strFormula = '0'  # 做市公式
        self.sList = []  # 做市公式中的所有合约
        self.mmPrice = 0  # 做市中间价
        self.orderDir = ORDER_LONGSHORT  # 报单方向
        self.dt = {}  # 最新时间
        self.cancel = False  # 撤单停止
        self.started = False  # 启动
        self.investors = ''  # 所有投资者
        self.investorMap = {}  # 合约投资者映射
        self.mode = 'passive'  # 报单模式
        self.headge = False  # 对冲模式
        self.autoOffset = False  # 自动开平
        self.stopOnTrade = False  # 成交后停止
        self.stopOnSpread = 100  # spread大于多少停止做市

        # 订单和成本管理
        self.costL = 0  # 买开成本
        self.costS = 0  # 卖开成本
        self.posL = 0  # 多头持仓
        self.posS = 0  # 空头持仓
        self.posLLock = 0  # 多头持仓冻结
        self.posSLock = 0  # 空头持仓冻结
        self.posLOpen = 0  # 多头持仓开仓量
        self.posSOpen = 0  # 空头持仓开仓量
        self.costhL = 0  # 对冲卖开成本
        self.costhS = 0  # 对冲卖开成本
        self.poshL = 0  # 对冲多头持仓
        self.poshS = 0  # 对冲空头持仓
        self.poshLLock = 0  # 对冲多头持仓冻结
        self.poshSLock = 0  # 对冲空头持仓冻结
        self.poshLOpen = 0  # 对冲多头持仓开仓量
        self.poshSOpen = 0  # 对冲空头持仓开仓量
        self.posPNL = 0  # 持仓盈亏
        self.posHPNL = 0  # 对冲持仓盈亏
        self.closePNL = 0  # 平仓盈亏
        self.closeHPNL = 0  # 对冲平仓盈亏
        self.openOrderInfo = {}  # 开仓委托信息
        self.closeOrderInfo = {}  # 平仓委托信息
        self.openPos = {}  # 开仓持仓
        self.dTime = datetime.timedelta(seconds=30)  # 对冲超时时间
        self.cancelOrders = {}  # 撤单信息
        super(MMStrategy, self).__init__(ctaEngine, setting)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        super(MMStrategy, self).onStart()
        self.investorMap.clear()
        self.symExMap.clear()
        invList = self.investors.split(';')
        for s, i in zip(self.symbolList, invList):
            self.investorMap[s] = i
        self.symExMap = dict([(s, e) for s, e in zip(self.symbolList, self.exchangeList)])
        self.output(str(self.investorMap))
        self.output(self.symExMap)
        self.getGui()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        # 订单和成本管理
        self.costL = 0
        self.costS = 0
        self.posL = 0
        self.posS = 0
        self.posLLock = 0
        self.posSLock = 0
        self.posLOpen = 0
        self.posSOpen = 0
        self.costhL = 0
        self.costhS = 0
        self.poshL = 0
        self.poshS = 0
        self.posPNL = 0
        self.posHPNL = 0
        self.closePNL = 0
        self.closeHPNL = 0
        self.poshLLock = 0
        self.poshSLock = 0
        self.poshLOpen = 0
        self.poshSOpen = 0
        self.openOrderInfo = {}
        self.closeOrderInfo = {}
        self.openPos = {}
        super(MMStrategy, self).onStop()
        self.closeGui()

    # ----------------------------------------------------------------------
    def evalFormula(self):
        """收到行情TICK推送（必须由用户继承实现）"""
        excStr = self.strFormula.format(*tuple([self.midPrice.get(s) for s in self.sList]))
        return eval(excStr)

    # ----------------------------------------------------------------------
    def onErr(self, error):
        """收到错误推送（必须由用户继承实现）"""
        if 'orderID' in error:
            oid = error['orderID']
            if oid is not None:
                self.onOrderCancel(error, oid)
        else:
            self.output(str(error))

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        super(MMStrategy, self).onTick(tick)
        # 过滤涨跌停和集合竞价
        if tick.lastPrice == 0 or tick.askPrice1 == 0 or tick.bidPrice1 == 0:
            return
        if not self.trading:
            return
        s = self
        symbol = tick.vtSymbol
        askP1 = tick.askPrice1
        bidP1 = tick.bidPrice1
        upperP = tick.upperLimit
        lowerP = tick.lowerLimit
        self.tickers[symbol] = tick
        self.askPrice1[symbol] = askP1
        self.bidPrice1[symbol] = bidP1
        self.upPrice[symbol] = upperP
        self.lowPrice[symbol] = lowerP
        self.midPrice[symbol] = (bidP1 + askP1) / 2.0
        # 计算挂单价
        self.mmPrice = self.evalFormula()
        askP0 = self.askPrice1.get(self.excSymbol, None)
        bidP0 = self.bidPrice1.get(self.excSymbol, None)
        lwP0 = self.lowPrice.get(self.excSymbol, None)
        upP0 = self.upPrice.get(self.excSymbol, None)
        nOrder = len(self.openOrderInfo.keys()) + len(self.closeOrderInfo.keys())
        askP1 = round((self.mmPrice + self.pOffset + self.pSpread / 2.0) / self.mPrice) * self.mPrice
        bidP1 = round((self.mmPrice + self.pOffset - self.pSpread / 2.0) / self.mPrice) * self.mPrice
        if not self.started:
            return
        if askP1 <= lwP0 or bidP1 <= lwP0 or askP1 >= upP0 or bidP1 >= upP0:
            return
        if (askP0 - bidP0) >= self.stopOnSpread:
            self.output(u'spread过大，全部撤单')
            self.cancelAll()
            return
        # 合约的盘口中价
        midp0 = (askP0 + bidP0) / 2
        # 对冲合约的盘口中价
        midp1 = (self.askPrice1.get(self.hedgeSymbol, 0) + self.bidPrice1.get(self.hedgeSymbol, 0)) / 2
        if self.posL > 0 or self.posS > 0:
            self.posPNL = (midp0 - self.costL) * self.posL + (self.costS - midp0) * self.posS
        if self.poshL > 0 or self.poshS > 0:
            self.posHPNL = (midp1 - self.costhL) * self.poshL + (self.costhS - midp1) * self.poshS
        # 消极模式检查时间同步
        if self.mode == 'passive':
            dt = self.dt[symbol] = tick.datetime
            for s in self.symbolList:
                if not self.dt.get(s) == dt:
                    return
        # 检查对冲订单是否超时
        for orderID in self.closeOrderInfo:
            oInfo = self.closeOrderInfo[orderID]
            dt = self.dt.get(self.excSymbol)
            if oInfo[4] and dt - oInfo[4] > self.dTime:
                self.cancelOrder(orderID)
                self.output(u'对冲单超时！！')
        # 开始执行
        if self.mode == 'positive':
            self.updateOrder2Market(askP0, bidP0, askP1, bidP1)
        else:
            self.updateOrder2Price(askP0, bidP0, askP1, bidP1)
        if (self.widget is not None) and (not self.excSymbol == ''):
            self.widget.signal.emit()

        self.putEvent()

    # ----------------------------------------------------------------------
    def cancelAll(self):
        s = self
        for oid, oinfo in self.openOrderInfo.items():
            s.cancelOrder(oid)
        for oid, oinfo in self.closeOrderInfo.items():
            s.cancelOrder(oid)

    # ----------------------------------------------------------------------
    # 积极做市，听市场的
    def updateOrder2Market(self, askP0, bidP0, askP1, bidP1):
        s = self
        if self.orderDir == ORDER_LONGSHORT:
            buy, sell = True, True
        elif self.orderDir == ORDER_LONG:
            buy, sell = True, False
        elif self.orderDir == ORDER_SHORT:
            buy, sell = False, True
        else:
            buy, sell = False, False
        # 是否刷新，True不用撤单
        sUpdate = bUpdate = False
        for oid, oinfo in self.openOrderInfo.items():
            if oinfo[0] == ORDER_LONGOPEN or oinfo[0] == ORDER_LONGCLOSE:
                if bidP1 != oinfo[1] or not buy:
                    s.cancelOrder(oid)
                # 意味着我还想以这个价格挂单，所以不撤单
                elif bidP1 == oinfo[1]:
                    bUpdate = True
            else:
                if askP1 != oinfo[1] or not sell:
                    s.cancelOrder(oid)
                elif askP1 == oinfo[1]:
                    sUpdate = True
        if buy and (not bUpdate) and bidP1 < askP0:
            s.buyS0(bidP1)
        if sell and (not sUpdate) and askP1 > bidP0:
            s.shortS0(askP1)

    # ----------------------------------------------------------------------
    # 消极做市，听价格的
    def updateOrder2Price(self, askP0, bidP0, askP1, bidP1):
        s = self
        if self.orderDir == ORDER_LONGSHORT:
            buy, sell = True, True
        elif self.orderDir == ORDER_LONG:
            buy, sell = True, False
        elif self.orderDir == ORDER_SHORT:
            buy, sell = False, True
        else:
            buy, sell = False, False
        sUpdate = bUpdate = False
        for oid, oinfo in self.openOrderInfo.items():
            if oinfo[0] == ORDER_LONGOPEN or oinfo[0] == ORDER_LONGCLOSE:
                if bidP1 != oinfo[1] or not buy:
                    s.cancelOrder(oid)
                elif bidP1 == oinfo[1]:
                    bUpdate = True
            else:
                if askP1 != oinfo[1] or not sell:
                    s.cancelOrder(oid)
                elif askP1 == oinfo[1]:
                    sUpdate = True
        if buy and (not bUpdate) and bidP1 < askP0 and bidP1 <= bidP0:
            s.buyS0(bidP1)
        if sell and (not sUpdate) and askP1 > bidP0 and askP1 >= askP0:
            s.shortS0(askP1)

    # ----------------------------------------------------------------------
    def findOpenPrice(self, price):
        """找开仓仓单，开仓委托中返回数量，没有返回0"""
        for oid in self.openOrderInfo:
            oinfo = self.openOrderInfo[oid]
            if round(oinfo[1] / self.mPrice) == round(price / self.mPrice):
                return oinfo[2]
        return 0

    # ----------------------------------------------------------------------
    def findCloseOrder(self, xid):
        """找平仓单，平仓委托中有为True，没有为False"""
        for oid, oinfo in self.closeOrderInfo.items():
            if oinfo[3] == xid:
                return True
        return False

    # ----------------------------------------------------------------------
    def buyS0(self, price, volume=0):
        """买合约0"""
        s = self
        v = s.volume if volume == 0 else volume
        posSAV = self.posS - self.posSLock
        if self.findOpenPrice(price) == 0:
            i = self.investorMap.get(str(self.excSymbol))
            if self.autoOffset and posSAV >= v:
                orderID = s.cover(price, v, symbol=self.excSymbol, investor=str(i))
            else:
                orderID = s.buy(price, v, symbol=self.excSymbol, investor=str(i))
            if orderID is not None:
                self.posLOpen += v
                self.openOrderInfo[orderID] = [ORDER_LONGOPEN, price, v]

    # ----------------------------------------------------------------------
    def shortS0(self, price, volume=0):
        """卖合约0"""
        s = self
        v = s.volume if volume == 0 else volume
        posLAV = self.posL - self.posLLock
        if self.findOpenPrice(price) == 0:
            i = self.investorMap.get(self.excSymbol)
            if self.autoOffset and posLAV >= v:
                orderID = s.sell(price, v, symbol=self.excSymbol, investor=str(i))
            else:
                orderID = s.short(price, v, symbol=self.excSymbol, investor=str(i))
            if orderID is not None:
                self.posSOpen += v
                self.openOrderInfo[orderID] = [ORDER_SHORTOPEN, price, v]

    # ----------------------------------------------------------------------
    def coverS0(self, price, xid, volume=0):
        """买合约0"""
        s = self
        v = s.volume if volume == 0 else volume
        dt = self.dt.get(self.excSymbol)
        posSAV = self.poshS - self.poshSLock
        orderID = None
        if not self.findCloseOrder(xid):
            i = self.investorMap.get(self.hedgeSymbol)
            if self.autoOffset and posSAV >= v:
                orderID = s.cover(price, v, symbol=self.hedgeSymbol, investor=str(i))
            else:
                orderID = s.buy(price, v, symbol=self.hedgeSymbol, investor=str(i))
            if orderID is not None:
                self.poshLOpen += v
                self.closeOrderInfo[orderID] = [ORDER_LONGOPEN, price, v, xid, dt]
        return orderID

    # ----------------------------------------------------------------------
    def sellS0(self, price, xid, volume=0):
        """卖合约0"""
        s = self
        v = s.volume if volume == 0 else volume
        dt = self.dt.get(self.excSymbol)
        posLAV = self.poshL - self.poshLLock
        orderID = None
        if not self.findCloseOrder(xid):
            i = self.investorMap.get(self.hedgeSymbol)
            if self.autoOffset and posLAV >= v:
                orderID = s.sell(price, v, symbol=self.hedgeSymbol, investor=str(i))
            else:
                orderID = s.short(price, v, symbol=self.hedgeSymbol, investor=str(i))
            if orderID is not None:
                self.poshSOpen += v
                self.closeOrderInfo[orderID] = [ORDER_SHORTOPEN, price, v, xid, dt]
        return orderID

    # ----------------------------------------------------------------------
    def onEnter(self, data={}):
        """进入该状态"""
        pass

    # ----------------------------------------------------------------------
    # 没用到，不知道什么意思
    def inStopTime(self, tick):
        """是否处于不发单状态"""
        hour, minute = tick.datetime.hour, tick.datetime.minute
        if hour == 14 and minute >= 59:
            return True
        elif hour == 22 and minute >= 59:
            return True
        return False

    # ----------------------------------------------------------------------
    # 没用到，不知道什么意思
    def inStartTime(self, tick):
        """是否处于开始状态"""
        hour = tick.datetime.hour
        if hour == 9 or hour == 21:
            return True
        return False

    # ----------------------------------------------------------------------
    def onOrderTrade(self, order):
        """委托推送"""
        orderID = order.orderID
        if orderID in self.closeOrderInfo:
            oInfo = self.closeOrderInfo[orderID]
            if oInfo[0] == ORDER_LONGCLOSE:
                self.poshSLock -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTCLOSE:
                self.poshLLock -= oInfo[2]
            elif oInfo[0] == ORDER_LONGOPEN:
                self.poshLOpen -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTOPEN:
                self.poshSOpen -= oInfo[2]
            if not oInfo[3] is None:
                # 已经挂入,冲掉挂单仓位
                if oInfo[3] in self.openPos:
                    del self.openPos[oInfo[3]]
            del self.closeOrderInfo[orderID]
        elif orderID in self.openOrderInfo:
            oInfo = self.openOrderInfo[orderID]
            if oInfo[0] == ORDER_LONGOPEN:
                self.posLOpen -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTOPEN:
                self.posSOpen -= oInfo[2]
            elif oInfo[0] == ORDER_LONGCLOSE:
                self.posSLock -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTCLOSE:
                self.posLLock -= oInfo[2]
            self.openPos[orderID] = oInfo
            if (not self.hedgeSymbol == '') and self.headge:
                askP0 = self.upPrice.get(self.hedgeSymbol)
                bidP0 = self.lowPrice.get(self.hedgeSymbol)
                # self.output(str(self.openOrderInfo))
                if oInfo[0] == ORDER_LONGOPEN or oInfo[0] == ORDER_LONGCLOSE:
                    self.sellS0(bidP0, orderID, order.tradedVolume)
                else:
                    self.coverS0(askP0, orderID, order.tradedVolume)
                self.output(u'对冲 : ' + str(order.tradedVolume) + '|' + str(askP0) + '|' + str(bidP0))
            del self.openOrderInfo[orderID]
        if (not self.widget is None) and (not self.excSymbol == ''):
            self.widget.signal.emit()

    # ----------------------------------------------------------------------
    def onOrderCancel(self, order, oid=None):
        """撤单超限->等待状态"""
        orderID = oid if oid else order.orderID
        if orderID in self.closeOrderInfo:
            oInfo = self.closeOrderInfo[orderID]
            if oInfo[0] == ORDER_LONGCLOSE:
                self.poshSLock -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTCLOSE:
                self.poshLLock -= oInfo[2]
            elif oInfo[0] == ORDER_LONGOPEN:
                self.poshLOpen -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTOPEN:
                self.poshSOpen -= oInfo[2]
            del self.closeOrderInfo[orderID]
        elif orderID in self.openOrderInfo:
            oInfo = self.openOrderInfo[orderID]
            if oInfo[0] == ORDER_LONGOPEN:
                self.posLOpen -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTOPEN:
                self.posSOpen -= oInfo[2]
            elif oInfo[0] == ORDER_LONGCLOSE:
                self.posSLock -= oInfo[2]
            elif oInfo[0] == ORDER_SHORTCLOSE:
                self.posLLock -= oInfo[2]
            del self.openOrderInfo[orderID]
        if (not self.widget is None) and (not self.excSymbol == ''):
            self.widget.signal.emit()

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """成交推送"""
        super(MMStrategy, self).onTrade(trade)
        s = self
        volume = trade.volume
        price = trade.price
        if trade.vtSymbol == self.excSymbol:
            if trade is not None and trade.direction == u'多':
                if trade.offset == u'开仓':
                    if (self.posL + volume) != 0:
                        self.costL = (price * volume + self.costL * self.posL) / (self.posL + volume)
                    else:
                        self.costL = 0
                    self.posL += volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|买开成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
                else:
                    if (self.posS - volume) > 0:
                        self.costS = (-price * volume + self.costS * self.posS) / (self.posS - volume)
                    else:
                        self.costS = 0
                        self.closePNL += price * volume - self.costS * self.posS
                    self.posS -= volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|买平成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
            elif trade is not None and trade.direction == u'空':
                if trade.offset == u'开仓':
                    if (self.posS + volume) != 0:
                        self.costS = (price * volume + self.costS * self.posS) / (self.posS + volume)
                    else:
                        self.costS = 0
                    self.posS += volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|卖开成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
                else:
                    if (self.posL - volume) > 0:
                        self.costL = (-price * volume + self.costL * self.posL) / (self.posL - volume)
                    else:
                        self.costL = 0
                        self.closePNL += -price * volume + self.costL * self.posL
                    self.posL -= volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|卖平成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
        elif trade.vtSymbol == self.hedgeSymbol:
            if trade is not None and trade.direction == u'多':
                if trade.offset == u'开仓':
                    self.costhL = (price * volume + self.costhL * self.poshL) / (self.poshL + volume)
                    self.poshL += volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|买开成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
                else:
                    if (self.poshS - volume) > 0:
                        self.costhS = (-price * volume + self.costS * self.poshS) / (self.poshS - volume)
                    else:
                        self.costhS = 0
                        self.closeHPNL += price * volume - self.costhS * self.poshS
                    self.poshS -= volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|买平成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
            elif trade is not None and trade.direction == u'空':
                if trade.offset == u'开仓':
                    self.costhS = (price * volume + self.costhS * self.poshS) / (self.poshS + volume)
                    self.poshS += volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|卖开成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
                else:
                    if (self.poshL - volume) > 0:
                        self.costhL = (-price * volume + self.costL * self.poshL) / (self.poshL - volume)
                    else:
                        self.costhL = 0
                        self.closeHPNL += -price * volume + self.costhL * self.poshL
                    self.poshL -= volume
                    s.output(trade.tradeTime
                             + u' 合约|' + str(trade.vtSymbol)
                             + u'|卖平成交|' + str(price)
                             + u'|手数|' + str(trade.volume))
        if self.stopOnTrade:
            self.output(u'发生成交，策略停止！')
            self.cancelAll()
            # self.onStop()
            # self.onStart()
            self.stop_on_trade()

    def onOrder(self, order, log=True):
        super(MMStrategy, self).onOrder(order, log)
        self.output(u'委托：' + str(order.orderID) + '|' + order.exchange + '|' + order.vtSymbol)

    def stop_on_trade(self):
        self.trading = False
        self.putEvent()

    # ----------------------------------------------------------------------
    def onExit(self, data={}):
        """退出该状态"""
        pass


########################################################################
class TradingWidget(QWidget):
    """简单交易组件"""

    directionList = [u'双向报价',
                     u'多方报价',
                     u'空方报价']

    signal = QtCore.Signal()
    signalLoad = QtCore.Signal()

    # ----------------------------------------------------------------------
    def __init__(self, strategy, parent=None):
        """Constructor"""
        super(TradingWidget, self).__init__(parent)
        self.strategy = strategy
        self.symbol = ''
        self.strFormula = None
        self.started = False
        # 添加交易接口
        self.initUi()
        self.signal.connect(self.updateTick)

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'做市策略-' + self.strategy.name)
        self.setMaximumWidth(400)

        # 左边部分
        labelPFormula = QLabel(u'中间价公式')
        labelPFormula.setObjectName(_fromUtf8('whiteLabel'))
        labelName = QLabel(u'做市合约')
        labelName.setObjectName(_fromUtf8('whiteLabel'))
        labelHedge = QLabel(u'对冲合约')
        labelHedge.setObjectName(_fromUtf8('whiteLabel'))
        labelDirection = QLabel(u'报价方向')
        labelDirection.setObjectName(_fromUtf8('whiteLabel'))
        labelPrice = QLabel(u'中间调整')
        labelPrice.setObjectName(_fromUtf8('whiteLabel'))
        labelSpread = QLabel(u'报价宽度')
        labelSpread.setObjectName(_fromUtf8('whiteLabel'))
        labelSSpread = QLabel(u'宽度限制')
        labelSSpread.setObjectName(_fromUtf8('whiteLabel'))
        labelVolume = QLabel(u'报价数量')
        labelVolume.setObjectName(_fromUtf8('whiteLabel'))

        self.linePFormula = QLineEdit()
        self.lineName = QLineEdit()
        self.lineHedge = QLineEdit()

        self.comboDirection = QComboBox()
        self.comboDirection.addItems(self.directionList)
        self.comboDirection.currentIndexChanged.connect(self.dirChg)

        self.spinPrice = QDoubleSpinBox()
        self.spinPrice.setDecimals(4)
        self.spinPrice.setMinimum(0)
        self.spinPrice.setMaximum(100000000)
        self.spinPrice.setValue(self.strategy.mmPrice)
        self.spinPrice.valueChanged.connect(self.priceChg)

        self.spinSpread = QDoubleSpinBox()
        self.spinSpread.setDecimals(4)
        self.spinSpread.setMinimum(0)
        self.spinSpread.setMaximum(100000000)
        self.spinSpread.setValue(self.strategy.pSpread)
        self.spinSpread.valueChanged.connect(self.spreadChg)

        self.spinSSpread = QDoubleSpinBox()
        self.spinSSpread.setDecimals(4)
        self.spinSSpread.setMinimum(0)
        self.spinSSpread.setMaximum(100000000)
        self.spinSSpread.setValue(self.strategy.stopOnSpread)
        self.spinSSpread.valueChanged.connect(self.sspreadChg)

        self.spinVolume = QSpinBox()
        self.spinVolume.setMinimum(0)
        self.spinVolume.setMaximum(100000000)
        self.spinVolume.setValue(self.strategy.volume)
        self.spinVolume.valueChanged.connect(self.volumeChg)

        gridleft = QGridLayout()
        gridleft.addWidget(labelPFormula, 0, 0)
        gridleft.addWidget(labelName, 1, 0)
        gridleft.addWidget(labelHedge, 2, 0)
        gridleft.addWidget(labelDirection, 3, 0)
        gridleft.addWidget(labelPrice, 4, 0)
        gridleft.addWidget(labelSpread, 5, 0)
        gridleft.addWidget(labelSSpread, 6, 0)
        gridleft.addWidget(labelVolume, 7, 0)

        gridleft.addWidget(self.linePFormula, 0, 1)
        gridleft.addWidget(self.lineName, 1, 1)
        gridleft.addWidget(self.lineHedge, 2, 1)
        gridleft.addWidget(self.comboDirection, 3, 1)
        gridleft.addWidget(self.spinPrice, 4, 1)
        gridleft.addWidget(self.spinSpread, 5, 1)
        gridleft.addWidget(self.spinSSpread, 6, 1)
        gridleft.addWidget(self.spinVolume, 7, 1)

        # 右边部分
        self.labelBid = []
        self.labelAsk = []
        self.labelBidP = []
        self.labelAskP = []
        self.labelBidV = []
        self.labelAskV = []

        for i in range(5):
            lbidp = QLabel()
            lbidp.setObjectName(_fromUtf8('redBackLabel'))
            self.labelBidP.append(lbidp)
            laskp = QLabel()
            laskp.setObjectName(_fromUtf8('greenBackLabel'))
            self.labelAskP.append(laskp)
            lbidv = QLabel()
            lbidv.setObjectName(_fromUtf8('darkBlueBackLabel'))
            self.labelBidV.append(lbidv)
            laskv = QLabel()
            laskv.setObjectName(_fromUtf8('darkBlueBackLabel'))
            self.labelAskV.append(laskv)
            lbid = QLabel(u'买{}'.format(i + 1))
            lbid.setObjectName(_fromUtf8('redLabel'))
            self.labelBid.append(lbid)
            lask = QLabel(u'卖{}'.format(i + 1))
            lask.setObjectName(_fromUtf8('greenLabel'))
            self.labelAsk.append(lask)

        labelLast = QLabel(u'最新')
        labelLast.setObjectName(_fromUtf8('blueLabel'))
        self.labelLastPrice = QLabel()
        self.labelLastPrice.setObjectName(_fromUtf8('blueBackLabel'))
        self.labelReturn = QLabel()
        self.labelReturn.setObjectName(_fromUtf8('darkBlueBackLabel'))

        self.labelLastPrice.setMinimumWidth(60)
        self.labelReturn.setMinimumWidth(60)

        gridRight = QGridLayout()
        for i in range(5):
            gridRight.addWidget(self.labelAsk[5 - i - 1], i, 0)
            gridRight.addWidget(self.labelBid[i], 5 + i + 1, 0)
            gridRight.addWidget(self.labelAskP[5 - i - 1], i, 1)
            gridRight.addWidget(self.labelBidP[i], 5 + i + 1, 1)
            gridRight.addWidget(self.labelAskV[5 - i - 1], i, 2)
            gridRight.addWidget(self.labelBidV[i], 5 + i + 1, 2)
        gridRight.addWidget(labelLast, 5, 0)
        gridRight.addWidget(self.labelLastPrice, 5, 1)
        gridRight.addWidget(self.labelReturn, 5, 2)
        labelPNLM = QLabel(u'做市盈亏:')
        labelPNLH = QLabel(u'对冲盈亏:')
        labelLM = QLabel(u'做市多单:')
        labelSM = QLabel(u'做市空单:')
        labelLH = QLabel(u'对冲多单:')
        labelSH = QLabel(u'对冲空单:')
        labelLM.setObjectName(_fromUtf8('redLabel'))
        labelSM.setObjectName(_fromUtf8('greenLabel'))
        labelLH.setObjectName(_fromUtf8('redLabel'))
        labelSH.setObjectName(_fromUtf8('greenLabel'))
        labelLM.setAlignment(Qt.AlignRight)
        labelSM.setAlignment(Qt.AlignRight)
        labelLH.setAlignment(Qt.AlignRight)
        labelSH.setAlignment(Qt.AlignRight)
        labelPNLM.setAlignment(Qt.AlignRight)
        labelPNLH.setAlignment(Qt.AlignRight)
        self.labelLMV = QLabel(u'')
        self.labelSMV = QLabel(u'')
        self.labelLHV = QLabel(u'')
        self.labelSHV = QLabel(u'')
        self.labelPNLMV = QLabel(u'')
        self.labelPNLHV = QLabel(u'')
        self.labelLMV.setObjectName(_fromUtf8('darkBlueBackLabel'))
        self.labelSMV.setObjectName(_fromUtf8('darkBlueBackLabel'))
        self.labelLHV.setObjectName(_fromUtf8('darkBlueBackLabel'))
        self.labelSHV.setObjectName(_fromUtf8('darkBlueBackLabel'))
        gridDown = QGridLayout()
        gridDown.addWidget(labelPNLM, 0, 0)
        gridDown.addWidget(labelLM, 1, 0)
        gridDown.addWidget(labelSM, 2, 0)
        gridDown.addWidget(labelPNLH, 0, 2)
        gridDown.addWidget(labelLH, 1, 2)
        gridDown.addWidget(labelSH, 2, 2)
        gridDown.addWidget(self.labelPNLMV, 0, 1)
        gridDown.addWidget(self.labelPNLHV, 0, 3)
        gridDown.addWidget(self.labelLMV, 1, 1)
        gridDown.addWidget(self.labelSMV, 2, 1)
        gridDown.addWidget(self.labelLHV, 1, 3)
        gridDown.addWidget(self.labelSHV, 2, 3)

        # 发单按钮
        self.buttonSendOrder = QPushButton(u'暂停中(点击-运行)')
        self.buttonChgMode = QPushButton(u'消极做市(点击-积极做市)')
        self.buttonHeadgeMode = QPushButton(u'不做对冲(点击-立即对冲)')
        self.buttonCancelAll = QPushButton(u'一律开仓(点击-优先平仓)')

        size = self.buttonSendOrder.sizeHint()
        self.buttonSendOrder.setMinimumHeight(size.height() * 2)  # 把按钮高度设为默认两倍
        self.buttonChgMode.setMinimumHeight(size.height() * 2)  # 把按钮高度设为默认两倍
        self.buttonHeadgeMode.setMinimumHeight(size.height() * 2)  # 把按钮高度设为默认两倍
        self.buttonCancelAll.setMinimumHeight(size.height() * 2)
        self.buttonSendOrder.setObjectName(_fromUtf8('greenButton'))
        self.buttonChgMode.setObjectName(_fromUtf8('greenButton'))
        self.buttonHeadgeMode.setObjectName(_fromUtf8('greenButton'))
        self.buttonCancelAll.setObjectName(_fromUtf8('greenButton'))

        # 整合布局
        hbox = QHBoxLayout()
        hbox.addLayout(gridleft)
        hbox.addLayout(gridRight)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addLayout(gridDown)
        vbox.addStretch()
        hbox0 = QHBoxLayout()
        hbox0.addWidget(self.buttonSendOrder)
        hbox0.addWidget(self.buttonCancelAll)
        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.buttonChgMode)
        hbox1.addWidget(self.buttonHeadgeMode)
        vbox.addLayout(hbox0)
        vbox.addLayout(hbox1)
        self.setLayout(vbox)

        # 关联更新
        self.buttonSendOrder.clicked.connect(self.startOrder)
        self.buttonCancelAll.clicked.connect(self.chgOffset)
        self.buttonChgMode.clicked.connect(self.chgMode)
        self.buttonHeadgeMode.clicked.connect(self.chgHeadge)
        self.lineHedge.returnPressed.connect(self.updateSymbol)

    # ----------------------------------------------------------------------
    def updateSymbol(self):
        """合约变化"""
        # 读取组件数据
        try:
            hedgeSymbol = str(self.lineHedge.text())
            if not hedgeSymbol in self.strategy.symbolList:
                self.strategy.output(u'对冲合约不在订阅列表中')
                return
            self.strategy.hedgeSymbol = hedgeSymbol
        except:
            pass

    # ----------------------------------------------------------------------
    def dirChg(self, index):
        """报单方向变化"""
        # 读取组件数据
        try:
            orderDir = self.directionList[index]
            if orderDir == u'双向报价':
                self.strategy.orderDir = ORDER_LONGSHORT
            elif orderDir == u'多方报价':
                self.strategy.orderDir = ORDER_LONG
            elif orderDir == u'空方报价':
                self.strategy.orderDir = ORDER_SHORT
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def spreadChg(self, value):
        """宽度变化"""
        # 读取组件数据
        try:
            self.strategy.pSpread = value
            self.updateTick()
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def volumeChg(self, value):
        """报单量变化"""
        # 读取组件数据
        try:
            self.strategy.output(orderdir)
            self.updateTick()
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def spreadChg(self, value):
        """宽度变化"""
        # 读取组件数据
        try:
            self.strategy.pSpread = value
            self.updateTick()
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def sspreadChg(self, value):
        """宽度变化"""
        # 读取组件数据
        try:
            self.strategy.stopOnSpread = value
            self.updateTick()
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def volumeChg(self, value):
        """报单量变化"""
        # 读取组件数据
        try:
            self.strategy.volume = value
            self.updateTick()
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def priceChg(self, value):
        """价格变化"""
        # 读取组件数据
        try:
            self.strategy.pOffset = value - self.strategy.mmPrice
            price = self.strategy.pOffset
            self.labelReturn.setText(str(price) if price < 0 else '+' + str(price))
            self.updateTick()
            self.strategy.putEvent()
        except:
            pass

    # ----------------------------------------------------------------------
    def updateTick(self):
        """更新行情"""
        s = self.strategy
        if not self.started:
            return
        # 清空价格数量
        try:
            mmPrice = round((s.mmPrice + s.pOffset) / s.mPrice) * s.mPrice
            tick = s.tickers.get(s.excSymbol)
            self.spinPrice.setValue(s.mmPrice + s.pOffset)
            askPL = [tick.askPrice1, tick.askPrice2, tick.askPrice3, tick.askPrice4, tick.askPrice5]
            bidPL = [tick.bidPrice1, tick.bidPrice2, tick.bidPrice3, tick.bidPrice4, tick.bidPrice5]
            askVL = [tick.askVolume1, tick.askVolume2, tick.askVolume3, tick.askVolume4, tick.askVolume5]
            bidVL = [tick.bidVolume1, tick.bidVolume2, tick.bidVolume3, tick.bidVolume4, tick.bidVolume5]
            avMap = dict([(ap, av) for av, ap in zip(askVL, askPL)])
            bvMap = dict([(bp, bv) for bv, bp in zip(bidVL, bidPL)])
            # 清空行情显示
            for i in range(5):
                askPL[i] = askPL[0] + i * s.mPrice
                bidPL[i] = bidPL[0] - i * s.mPrice
                askVL[i] = avMap.get(askPL[i], '*')
                bidVL[i] = bvMap.get(bidPL[i], '*')
                self.labelAskP[i].setText(str(askPL[i]))
                self.labelBidP[i].setText(str(bidPL[i]))
                self.labelAskV[i].setText(str(askVL[i]) + '|' + str(s.findOpenPrice(askPL[i])))
                self.labelBidV[i].setText(str(bidVL[i]) + '|' + str(s.findOpenPrice(bidPL[i])))
                if not s.findOpenPrice(askPL[i]) == 0:
                    self.labelAskV[i].setStyleSheet("color:green;")
                else:
                    self.labelAskV[i].setStyleSheet("color:white;")
                if not s.findOpenPrice(bidPL[i]) == 0:
                    self.labelBidV[i].setStyleSheet("color:red;")
                else:
                    self.labelBidV[i].setStyleSheet("color:white;")
                if mmPrice == bidPL[i]:
                    self.labelBidV[i].setStyleSheet("color:yellow;")
                elif mmPrice == askPL[i]:
                    self.labelAskV[i].setStyleSheet("color:yellow;")
            self.labelLastPrice.setText(str(tick.lastPrice))
            price = s.pOffset
            self.labelReturn.setText(str(price) if price < 0 else '+' + str(price))
            self.labelLMV.setText(str(s.posL))
            self.labelSMV.setText(str(s.posS))
            self.labelLHV.setText(str(s.poshL))
            self.labelSHV.setText(str(s.poshS))
            self.labelPNLMV.setText(str(s.posPNL + s.closePNL))
            self.labelPNLHV.setText(str(s.posHPNL + s.closeHPNL))
        except Exception as e:
            s.output(str(e))
            pass

    # ----------------------------------------------------------------------
    def startOrder(self):
        """开始报单"""
        if self.started:
            self.cancelAll()
            self.buttonSendOrder.setText(u'暂停中(点击-运行)')
            self.buttonSendOrder.setStyleSheet("background-color: rgb(87, 153, 61);")
            self.started = False
            return
        else:
            self.strategy.output(u'公式解析开始')
            strFormula = str(self.linePFormula.text())
            excSymbol = str(self.lineName.text())
            hedgeSymbol = str(self.lineHedge.text())
            try:
                i = 0
                sList = []
                for s in self.strategy.symbolList:
                    if s in strFormula:
                        strFormula = strFormula.replace(s, '{%d}' % i)
                        sList.append(s)
                        i += 1
                self.strategy.strFormula = strFormula
                self.strategy.sList = sList
                price = self.strategy.evalFormula()
                self.strategy.output(u'当前计算均价为：' + str(price))
            except Exception as e:
                self.strategy.output(u'公式计算出错,请检查表达式和行情连接')
                self.strategy.output(traceback.format_exc())
                self.strategy.output(str(e))
                return
            self.strategy.output(u'公式解析完成')
            self.strategy.excSymbol = excSymbol
            if excSymbol not in self.strategy.symbolList:
                self.strategy.output(u'做市合约不在订阅列表中')
                return
            self.strategy.hedgeSymbol = hedgeSymbol
            if hedgeSymbol not in self.strategy.symbolList:
                self.strategy.output(u'对冲合约不在订阅列表中')
                return
            self.strategy.pSpread = self.spinSpread.value()
            self.strategy.volume = self.spinVolume.value()
            self.spinSpread.setSingleStep(self.strategy.mPrice)
            self.spinPrice.setSingleStep(self.strategy.mPrice)
            self.strategy.output(u'做市启动完成' + str(self.strategy.pSpread))
            self.strategy.started = True
            self.strategy.trading = True
            self.strategy.putEvent()
            self.strategy.putEvent()
            self.started = True
            self.buttonSendOrder.setText(u'运行中(点击-暂停)')
            self.buttonSendOrder.setStyleSheet("background-color: rgb(153, 61, 61);")

    # ----------------------------------------------------------------------
    def clear(self):
        """清空数据"""
        pass

    # ----------------------------------------------------------------------
    def cancelAll(self):
        """一键撤销所有委托"""
        self.started = False
        self.strategy.started = False
        self.strategy.cancelAll()
        self.strategy.output(u'全撤')

    # ----------------------------------------------------------------------
    def chgMode(self):
        """切换模式"""
        mode = self.strategy.mode
        if mode == 'passive':
            self.strategy.mode = 'positive'
            self.buttonChgMode.setText(u'积极做市(点击-消极做市)')
            self.buttonChgMode.setStyleSheet("background-color: rgb(153, 61, 61);")
        else:
            self.strategy.mode = 'passive'
            self.buttonChgMode.setText(u'消极做市(点击-积极做市)')
            self.buttonChgMode.setStyleSheet("background-color: rgb(87, 153, 61);")

    # ----------------------------------------------------------------------
    def chgHeadge(self):
        """切换对冲模式"""
        headge = self.strategy.headge
        if headge:
            self.strategy.headge = False
            self.buttonHeadgeMode.setText(u'不做对冲(点击-立即对冲)')
            self.buttonHeadgeMode.setStyleSheet("background-color: rgb(87, 153, 61);")
        else:
            self.strategy.headge = True
            self.buttonHeadgeMode.setText(u'立即对冲(点击-不做对冲)')
            self.buttonHeadgeMode.setStyleSheet("background-color: rgb(153, 61, 61);")

    # ----------------------------------------------------------------------
    def chgOffset(self):
        """切换模式"""
        autoOffset = self.strategy.autoOffset
        if autoOffset:
            self.strategy.autoOffset = False
            self.buttonCancelAll.setText(u'一律开仓(点击-优先平仓)')
            self.buttonCancelAll.setStyleSheet("background-color: rgb(87, 153, 61);")
        else:
            self.strategy.autoOffset = True
            self.buttonCancelAll.setText(u'优先平仓(点击-一律开仓)')
            self.buttonCancelAll.setStyleSheet("background-color: rgb(153, 61, 61);")

    # ----------------------------------------------------------------------
    def closeEvent(self, evt):
        """关闭"""
        s = self.strategy
        if s.trading is False:
            evt.accept()
        else:
            s.output(u'只能在停止策略时自动关闭')
            evt.ignore()
