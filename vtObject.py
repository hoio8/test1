# encoding: UTF-8

from imp import reload
import os
import sys
import datetime

reload(sys)
if not sys.version_info.major == 3:
    sys.setdefaultencoding('utf-8')
else:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = sys.base_prefix + '\\Library\\plugins'
allStrategy = []
sys.path.append('.\\pyStrategy\\')
sys.path.append(os.path.split(os.path.realpath(__file__))[0])
from vtConstant import *
import time
import traceback
import imp

product_cls = {'1': '期货',
               '2': '期权',
               '3': '组合',
               '4': '即期',
               '5': '期转现',
               '6': '未知类型',
               '7': '证券',
               '8': '股票期权',
               '9': '金交所现货',
               'a': '金交所递延',
               'b': '金交所远期',
               'h': '现货期权'}

option_type = {'0': '非期权',
               '1': '看涨',
               '2': '看跌'}


########################################################################
class VtBaseData(object):
    """回调函数推送数据的基础类，其他数据类继承于此"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.gatewayName = EMPTY_STRING  # Gateway名称
        self.rawData = None  # 原始数据


########################################################################
class VtTickData(VtBaseData):
    """
    Tick行情数据类,来源为交易所推送的行情切片
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtTickData, self).__init__()

        # 代码相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约代码.交易所代码

        # 成交数据
        self.lastPrice = EMPTY_FLOAT  # 最新成交价
        self.lastVolume = EMPTY_INT  # 最新成交量
        self.volume = EMPTY_INT  # 今天总成交量
        self.openInterest = EMPTY_INT  # 持仓量
        self.time = EMPTY_STRING  # 时间 11:20:56.5
        self.date = EMPTY_STRING  # 日期 20151009
        self.datetime = None  # 合约时间

        # 常规行情
        self.openPrice = EMPTY_FLOAT  # 今日开盘价
        self.highPrice = EMPTY_FLOAT  # 今日最高价
        self.lowPrice = EMPTY_FLOAT  # 今日最低价
        self.preClosePrice = EMPTY_FLOAT  # 昨收盘价
        self.PreSettlementPrice = EMPTY_FLOAT  # 昨结算价

        self.upperLimit = EMPTY_FLOAT  # 涨停价
        self.lowerLimit = EMPTY_FLOAT  # 跌停价

        self.turnover = EMPTY_FLOAT  # 成交额

        # 五档行情
        self.bidPrice1 = EMPTY_FLOAT
        self.bidPrice2 = EMPTY_FLOAT
        self.bidPrice3 = EMPTY_FLOAT
        self.bidPrice4 = EMPTY_FLOAT
        self.bidPrice5 = EMPTY_FLOAT

        self.askPrice1 = EMPTY_FLOAT
        self.askPrice2 = EMPTY_FLOAT
        self.askPrice3 = EMPTY_FLOAT
        self.askPrice4 = EMPTY_FLOAT
        self.askPrice5 = EMPTY_FLOAT

        self.bidVolume1 = EMPTY_INT
        self.bidVolume2 = EMPTY_INT
        self.bidVolume3 = EMPTY_INT
        self.bidVolume4 = EMPTY_INT
        self.bidVolume5 = EMPTY_INT

        self.askVolume1 = EMPTY_INT
        self.askVolume2 = EMPTY_INT
        self.askVolume3 = EMPTY_INT
        self.askVolume4 = EMPTY_INT
        self.askVolume5 = EMPTY_INT

    ########################################################################


class VtTradeData(VtBaseData):
    """
    成交数据类,来源为交易所推送的成交回报
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtTradeData, self).__init__()

        # 代码编号相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约代码.交易所代码

        self.tradeID = EMPTY_STRING  # 成交编号
        self.vtTradeID = EMPTY_STRING  # 成交编号

        self.orderID = EMPTY_STRING  # 订单编号
        self.vtOrderID = EMPTY_STRING  # 订单编号

        # 成交相关
        self.direction = EMPTY_UNICODE  # 成交方向
        self.offset = EMPTY_UNICODE  # 成交开平仓
        self.price = EMPTY_FLOAT  # 成交价格
        self.volume = EMPTY_INT  # 成交数量
        self.tradeTime = EMPTY_STRING  # 成交时间

        self.commission = EMPTY_FLOAT  # 手续费


########################################################################
class VtOrderData(VtBaseData):
    """
    订单数据类,来源为交易所推送的委托回报
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtOrderData, self).__init__()

        # 代码编号相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 交易所代码

        self.orderID = EMPTY_STRING  # 订单编号
        self.vtOrderID = EMPTY_STRING  # 订单编号

        # 报单相关
        self.direction = EMPTY_UNICODE  # 报单方向
        self.offset = EMPTY_UNICODE  # 报单开平仓
        self.price = EMPTY_FLOAT  # 报单价格
        self.priceType = EMPTY_UNICODE  # 报单价格
        self.totalVolume = EMPTY_INT  # 报单总数量
        self.tradedVolume = EMPTY_INT  # 报单成交数量
        self.status = EMPTY_UNICODE  # 报单状态

        self.orderTime = EMPTY_STRING  # 发单时间
        self.cancelTime = EMPTY_STRING  # 撤单时间

        # CTP/LTS相关
        self.frontID = EMPTY_INT  # 前置机编号
        self.sessionID = EMPTY_INT  # 连接编号


########################################################################
class VtBarData(VtBaseData):
    """
    K线数据
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtBarData, self).__init__()

        self.vtSymbol = EMPTY_STRING  # vt系统代码
        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所

        self.open = EMPTY_FLOAT  # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT

        self.date = EMPTY_STRING  # bar开始的时间，日期
        self.time = EMPTY_STRING  # 时间
        self.datetime = None  # python的datetime时间对象

        self.volume = EMPTY_INT  # 成交量
        self.openInterest = EMPTY_INT  # 持仓量


########################################################################
class VtPositionData(VtBaseData):
    """持仓数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtPositionData, self).__init__()

        # 代码编号相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约在vt系统中的唯一代码，合约代码.交易所代码

        # 持仓相关
        self.direction = EMPTY_STRING  # 持仓方向
        self.position = EMPTY_INT  # 持仓量
        self.frozen = EMPTY_INT  # 冻结数量

        self.open_avg_price = EMPTY_INT  # 开仓均价
        self.position_avt_price = EMPTY_FLOAT  # 持仓均价
        self.postion_cost = EMPTY_INT  # 持仓成本

        self.vtPositionName = EMPTY_STRING  # 持仓在vt系统中的唯一代码，通常是vtSymbol.方向
        self.investorID = EMPTY_STRING  # 投资者
        self.investor = EMPTY_STRING  # 投资者
        self.positionProfit = EMPTY_FLOAT  # 平仓盈亏

        # 20151020添加
        self.ydPosition = EMPTY_INT  # 昨持仓


########################################################################
class VtAccountData(VtBaseData):
    """账户数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtAccountData, self).__init__()

        # 账号代码相关
        self.datetime = None
        self.accountID = EMPTY_STRING  # 账户代码
        self.vtAccountID = EMPTY_STRING  # 账户在vt中的唯一代码，通常是 Gateway名.账户代码

        # 数值相关
        self.preBalance = EMPTY_FLOAT  # 昨日账户结算净值
        self.balance = EMPTY_FLOAT  # 账户净值
        self.available = EMPTY_FLOAT  # 可用资金
        self.commission = EMPTY_FLOAT  # 今日手续费
        self.margin = EMPTY_FLOAT  # 保证金占用
        self.closeProfit = EMPTY_FLOAT  # 平仓盈亏
        self.positionProfit = EMPTY_FLOAT  # 持仓盈亏


########################################################################
class VtContractData(VtBaseData):
    """合约详细信息类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtContractData, self).__init__()

        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约代码.交易所代码
        self.name = EMPTY_UNICODE  # 合约中文名

        self.productClass = EMPTY_UNICODE  # 合约类型
        self.size = EMPTY_INT  # 合约大小（合约乘数）
        self.priceTick = EMPTY_FLOAT  # 合约最小价格TICK

        # 期权相关
        self.strikePrice = EMPTY_FLOAT  # 期权行权价
        self.underlyingSymbol = EMPTY_STRING  # 标的物合约代码
        self.optionType = EMPTY_UNICODE  # 期权类型


# ----------------------------------------------------------------------
def importStrategy(path):
    """导入python策略"""
    errCode = ''
    try:
        file_name = path.split("\\")[-1]
        model_name = file_name.split(".")[0]
        if not sys.version_info.major == 3:
            imp.load_source('ctaStrategies', path.encode('gbk'))
        else:
            imp.load_source('ctaStrategies', path)
        s_obj = getattr(sys.modules['ctaStrategies'], model_name)
        errCode = errCode.replace('\n', '\r\n')
        # with open('C:\Users\Administrator\Desktop\\testing.txt', 'w+') as f:
        #     f.write(str(s_obj.__dict__))
        return errCode, s_obj
    except Exception as e:
        errCode = traceback.format_exc()
        errCode = errCode.replace('\n', '\r\n')
        return errCode, None


# ----------------------------------------------------------------------
def safeDatetime(timeStr):
    """策略的时间"""
    # 如果行情没有返回date，手动拼接
    str_list = timeStr.split(' ')
    if str_list[0] == '0':
        timeStr = str(datetime.datetime.now().date()).replace('-', '') + ' ' + str_list[1]

    try:
        dt = datetime.datetime.strptime(timeStr, "%Y%m%d %H:%M:%S.%f")
        return dt
    except:
        dt = datetime.datetime.strptime(timeStr, "%Y%m%d %H%M%S.%f")
        return dt


# ----------------------------------------------------------------------
def safeCall(pyFunc, pyArgs=()):
    """创建策略实例"""
    # pyFunc: onStop, onInit等各种方法的对象
    # pyRes: 策略参数的对象
    # pyArgs: 一排() + tick对象
    try:
        pyRes = pyFunc(*pyArgs)
        return pyRes
    except Exception as e:
        import ctaEngine
        errCode = '\r\n'.join([str(pyFunc), traceback.format_exc()])
        errCode = errCode.replace('\n', '\r\n')
        ctaEngine.writeLog(errCode)
        return 'error'


# ----------------------------------------------------------------------
def onExit():
    """引擎退出"""
    CtaTemplate.t = None

# t=Thread(target=StartGui)
# t.setDaemon(False)
# t.start()
