import time, datetime, json, requests, sys, pytz, enum
from AvanzaHandler import AvanzaHandler, TransactionType
from Logger import Log, LogType

BASEURL = "http://192.168.1.50:5000/tradingpal/"
BUY_PATH = "getStocksToBuy"
SELL_PATH = "getStocksToSell"

# If buy/sell price quota differs more than this, a buy bid will use buy price, sell bid use sell price.
MAX_DEVIATE_PRICE = 1.03

# If buy/sell price quota differs more than this, the entire transaction will be cancelled
MAX_SANITY_QUOTA_SELL_BUY = 1.12

# will not go through with transaction if stock price was not updated last sec
# Note that we get delayed prices 15 minutes. ToDo: Fix this depending upon market...
MAX_TIME_SINCE_STOCK_PRICE_UPDATED_SEC = 3600

MAX_ALLOWED_TRANSACTION_SIZE_SEK = 9000

# Define during what hours transactions shall be attempted.
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 23

log = Log()

class EventType(enum.Enum):
    AvanzaTransaction = 1,
    AvanzaErrors = 2,
    Exception = 3

class MainBroker:

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def __init__(self):

        self.terminate = False
        self.blockPurchases = False
        self.blockTransactions = False
        self.resetEventCounters()
        self.refreshAvanzaHandler()

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def doStocksTransaction(self, stocks, transactionType: TransactionType):
        self.refreshAvanzaHandler()

        for stock in stocks:
            lockKey = None
            yahooTicker = None
            try:
                yahooTicker = stock['tickerName']
                lockKey = self.lockStock(yahooTicker)
                tickerId = self.avanzaHandler.tickerToId(yahooTicker)
                avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)

                if avanzaDetails is None:
                    raise RuntimeWarning(f"WARN: could not find ticker in avanza: {yahooTicker}")

                sanityStatus = self.sanityCheckStock(avanzaDetails, stock, transactionType)

                if sanityStatus != None:
                    log.log(LogType.Trace, f"Sanity check failed: {stock['currentStock']['name']} / {sanityStatus}")
                    continue

                self.doOneTransactionWithRetries(avanzaDetails, transactionType, stock, yahooTicker, tickerId, lockKey)
                    
            except Exception as ex:
                self.addEvent(EventType.Exception)
                log.log(LogType.Trace, f"Could not buy stock {stock['currentStock']['name']}/{yahooTicker}, {ex}")
            finally:
                self.unlockStock(yahooTicker, lockKey)

    def doOneTransactionWithRetries(self, avanzaDetails, transactionType, stock, yahooTicker, tickerId, lockKey):

        log.log(LogType.Trace, f"---------- TRANSACTING STOCK ----------- {stock['currentStock']['name']}/{yahooTicker} -------")

        self.addEvent(EventType.AvanzaTransaction)
        countAtStart = avanzaDetails['currentCount']

        if transactionType == TransactionType.Sell:
            price = avanzaDetails["buyPrice"]
        else:
            price = avanzaDetails["sellPrice"]

        for a in range(3):

            if transactionType == TransactionType.Buy:
                numberToTransact = stock["numberToBuy"]
                expectedCountWhenDone = countAtStart + numberToTransact
                price = self.getNewStockPrice(TransactionType.Buy, avanzaDetails, price)
            else:
                numberToTransact = stock["numberToSell"]
                expectedCountWhenDone = countAtStart - numberToTransact
                price = self.getNewStockPrice(TransactionType.Sell, avanzaDetails, price)

            newTotalCount = self.doOneTransactionAndCheckResult(transactionType, countAtStart,
                                                                expectedCountWhenDone, yahooTicker,
                                                                avanzaDetails['accountId'], tickerId,
                                                                price, numberToTransact)

            if newTotalCount != countAtStart:
                amountTransacted = newTotalCount - countAtStart
                spentSek = stock['singleStockPriceSek'] * amountTransacted
                newTotalInvestedSek = int(stock['currentStock']['totalInvestedSek'] + spentSek)

                self.updateStock(
                    yahooTicker,
                    stock['priceOrigCurrancy'] if transactionType == TransactionType.Buy else None,
                    stock['priceOrigCurrancy'] if transactionType == TransactionType.Sell else None,
                    countAtStart, newTotalCount, spentSek, lockKey, stock['currentStock']['name'],
                    newTotalInvestedSek, tickerId)

                break

    # ##############################################################################################################
    # Performs a buy order. Returns the new number of stocks owned.
    # ##############################################################################################################
    def doOneTransactionAndCheckResult(self, transactionType: TransactionType, countAtStart: int, expectedWhenDone: int, yahooTicker: str, accountId: str, tickerId: str, price: float, volume: int):

        WAIT_SEC_FOR_COMPLETION = 3

        infoString = f"{yahooTicker}: tickerId: {tickerId}, transaction: {transactionType}, accountId {accountId}, price: {price}, volume {volume}, expectedWhenDone: {expectedWhenDone}, countAtStart: {countAtStart}"
        log.log(LogType.Audit, f"Placing Avanza order: {infoString}")

        retVal = self.avanzaHandler.placeOrder(yahooTicker, accountId, tickerId, transactionType, price, volume)

        if "blockPurchase" in retVal and retVal["blockPurchase"] is True:
            print("Blocking all purchases due to message from Avanza!")
            self.doBlockPurchases()
            raise RuntimeError()

        if "blockTransactions" in retVal and retVal["blockTransactions"] is True:
            print("Blocking all transactions due to message from Avanza!")
            self.blockTransactions = True
            raise RuntimeError()

        if retVal is None or 'orderRequestStatus' not in retVal or retVal['orderRequestStatus'] != "SUCCESS":
            log.log(LogType.Audit, f"Could not place Avanza order: {retVal}, {infoString}")
            self.avanzaHandler.deleteOrder(accountId, retVal['orderId'])
            raise RuntimeError()

        for a in range(WAIT_SEC_FOR_COMPLETION):
            avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)
            if avanzaDetails['currentCount'] == expectedWhenDone:
                log.log(LogType.Audit, f"(1) Avanza order succesfull: {infoString}")
                return avanzaDetails['currentCount']

            log.log(LogType.Trace, f"{yahooTicker} {transactionType} order is on market.. Waiting...")
            time.sleep(1)

        log.log(LogType.Trace, f"{yahooTicker} {transactionType} Failed to transact stock in {WAIT_SEC_FOR_COMPLETION} seconds. deleting order")

        try:
            self.avanzaHandler.deleteOrder(accountId, retVal['orderId'])
        except Exception:
            log.log(LogType.Trace, "Could not delete order... Ignoring")

        time.sleep(1)
        avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)

        if avanzaDetails['currentCount'] == expectedWhenDone:
            log.log(LogType.Audit, f"(2) Avanza order succesfull: {infoString}")
        elif avanzaDetails['currentCount'] == countAtStart:
            log.log(LogType.Audit, f"No stocks transacted: {infoString}")
        else:
            log.log(LogType.Audit, f"Avanza order partly transacted. Current: {avanzaDetails['currentCount']}: {infoString}")

        return avanzaDetails['currentCount']

    # ##############################################################################################################
    # get sell price from best price (priceLevel == 1) to worst price (priceLevel == ~4)
    # ##############################################################################################################

    def getNewStockPrice(self, transactionType :TransactionType, avanzaDetails, lastPrice: int):

        if avanzaDetails['tick1Percent'] <= 0:
            raise RuntimeError("tick1Percent not calculated for stock")

        if transactionType == TransactionType.Buy:
            newVal = float("%.4f" % (lastPrice + avanzaDetails['tick1Percent']))
        else:
            newVal = float("%.4f" % (lastPrice - avanzaDetails['tick1Percent']))

        log.log(LogType.Trace, f"Changing bidValue: {transactionType} / from {lastPrice} to {newVal}")
        return newVal


    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def sanityCheckStock(self, avanzaDetails, tradingPalDetails, transactionType):

        sellPrice = avanzaDetails['sellPrice']
        buyPrice = avanzaDetails['buyPrice']
        avgPriceAvanza = (sellPrice + buyPrice) / 2
        priceFromTradingPal = tradingPalDetails['priceOrigCurrancy']

        if transactionType == TransactionType.Buy:
            numberToTransact = tradingPalDetails["numberToBuy"]
        else:
            numberToTransact = tradingPalDetails["numberToSell"]

        if sellPrice is None or buyPrice is None:
            raise RuntimeError(f"buy/sell price is None")

        if avanzaDetails['secondsSinceUpdated'] > MAX_TIME_SINCE_STOCK_PRICE_UPDATED_SEC:
            return f"stockdata not updated within {MAX_TIME_SINCE_STOCK_PRICE_UPDATED_SEC} sec"
        if sellPrice == -1 or buyPrice == -1:
            return f"buy / sell data missing for stock. Market probably closed"
        if sellPrice < 0.01 or sellPrice > 5000.0 or buyPrice < 0.01 or buyPrice > 5000.0:
            raise RuntimeError(f"Stock sell / buy price is not reasonable {sellPrice} / {buyPrice}")
        if priceFromTradingPal < (0.9 * avgPriceAvanza) or priceFromTradingPal > (1.1 * avgPriceAvanza):
            raise RuntimeError(f"Stock price from tradingpal differs to much from avanza price. avanza: {avgPriceAvanza}, tradingPal: {priceFromTradingPal}")
        if (tradingPalDetails['singleStockPriceSek'] * numberToTransact) > MAX_ALLOWED_TRANSACTION_SIZE_SEK:
            raise RuntimeError(f"Transaction to big!! single stock price SEK: {tradingPalDetails['singleStockPriceSek']}, numberToTransact: {numberToTransact}")
        if buyPrice > sellPrice:
            raise RuntimeError(f"buyPrice {buyPrice} is less than sellPrice {sellPrice}")
        if (sellPrice / buyPrice) > MAX_SANITY_QUOTA_SELL_BUY:
            raise RuntimeError(f"sell/buy price: {sellPrice}/{buyPrice} > {MAX_SANITY_QUOTA_SELL_BUY}. Not reasonable...")
        if avanzaDetails['currentCount'] != tradingPalDetails['currentStock']['count']:
            raise RuntimeError(f"Stock count in avanza does not match count from tradingPal. Abort")

        return None

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def refreshAvanzaHandler(self):

        self.addEvent(EventType.AvanzaErrors)

        try:
            self.avanzaHandler.testAvanzaConnection()
        except Exception:
            log.log(LogType.Trace, "Need to refresh AvanzaHandler...")
            self.avanzaHandler = AvanzaHandler(log).init()
            self.avanzaHandler.testAvanzaConnection()

        self.resetEvent(EventType.AvanzaErrors)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def run(self):

        log.log(LogType.Audit, "Starting up, test connections to trading pal algorithm...")

        self.waitForConnectonToTradingPal()

        while not self.terminate:

            time.sleep(60)
            print("Trading disabled waiting for code fix after new domain model from avanza api")
            continue

            if not self.marketsOpenDaytime():
                log.log(LogType.Trace, "Markets closed...")
                time.sleep(120)
                continue

            if not self.areAllEventsOk():
                log.log(LogType.Audit, f"To many events in one day. Stepping back... {self.events}")
                time.sleep(3600)
                continue

            try:
                stocksToBuy = self.fetchTickers(BUY_PATH)
                if self.blockTransactions is False and self.blockPurchases is False and stocksToBuy is not None and len(stocksToBuy['list']) > 0:
                    self.doStocksTransaction(stocksToBuy['list'], TransactionType.Buy)
                    time.sleep(120)
            except Exception as ex:
                self.addEvent(EventType.Exception)
                log.log(LogType.Trace, f"Exception during buy, {ex}")

            try:
                stocksToSell = self.fetchTickers(SELL_PATH)
                if self.blockTransactions is False and stocksToSell is not None and len(stocksToSell['list']) > 0:
                    self.doStocksTransaction(stocksToSell['list'], TransactionType.Sell)
                    time.sleep(120)
            except Exception as ex:
                self.addEvent(EventType.Exception)
                log.log(LogType.Trace, f"Exception during sell, {ex}")

            time.sleep(60)

        print("Terminating!!!")
        sys.exit()

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def waitForConnectonToTradingPal(self):
        while True:
            if self.fetchTickers(BUY_PATH) is not None:
                log.log(LogType.Trace, "Connection to trading pal algorithm OK!")
                break
            else:
                log.log(LogType.Trace, f"Connection to tradingpal is still not OK. Retrying...")
                time.sleep(15)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def fetchTickers(self, path: str):

        try:
            retData = requests.get(BASEURL + path)

            if retData.status_code != 200:
                log.log(LogType.Trace, f"{datetime.datetime.utcnow()} Failed to fetch stocks... retrying")
                time.sleep(20)

            return json.loads(retData.content)
        except Exception as ex:
            log.log(LogType.Trace, f"{datetime.datetime.utcnow()} Failed to fetch tickers: {ex}")
            return None

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def updateStock(self, tickerName: str, boughtAt: float, soldAt: float, countAtStart: int, count: int, spent: int, lockKey: int, name: str, totalInvestedSek: int, tickerId):

        body = {
            'ticker': tickerName,
            'boughtAt': boughtAt,
            'soldAt': soldAt,
            'count': count,
            'lockKey': lockKey,
            'name': name,
            'totalInvestedSek': totalInvestedSek,
            'tradedByBot': True
        }

        try:
            retData = requests.post(BASEURL + "updateStock", json=body)
            if retData.status_code != 200:
                raise RuntimeError(f"Failed to update stock {tickerName}, {retData.content}")
        except Exception as ex:
            log.log(LogType.Trace, f"Failed to update stock {tickerName}, {ex}")
            raise ex
        finally:
            body['countAtStart'] = countAtStart
            body['spent'] = spent
            body['avanzaTickerId'] = tickerId
            log.log(LogType.Register, body)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def lockStock(self, ticker: str):

        try:
            retData = requests.post(BASEURL + "lock", json= {"ticker": ticker})
            if retData.status_code != 200:
                raise RuntimeError(f"Failed to lock stock {ticker}, {retData.content}")
            return json.loads(retData.content)['lockKey']
        except Exception as ex:
            log.log(LogType.Trace, f"Failed to lock stock {ticker}, {ex}")
            raise ex

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def unlockStock(self, ticker: str, lockKey: int):

        if lockKey is None:
            return

        try:
            retData = requests.post(BASEURL + "unlock", json= {"ticker": ticker, "lockKey": lockKey})
            if retData.status_code != 200:
                raise RuntimeError(f"Failed to unlock stock {ticker}, {retData.content}")
        except Exception as ex:
            log.log(LogType.Trace, f"Failed to unlock stock {ticker}, {ex}")
            raise ex

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def marketsOpenDaytime(self):

        hour = datetime.datetime.now(pytz.timezone('Europe/Stockholm')).hour
        weekday = datetime.datetime.now(pytz.timezone('Europe/Stockholm')).weekday()

        return (hour >= MARKET_OPEN_HOUR and hour < MARKET_CLOSE_HOUR) and (weekday >= 0 and weekday <= 4)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def resetEventCounters(self):

        self.events = {
            "day": datetime.datetime.now(pytz.timezone('Europe/Stockholm')).day,
            EventType.AvanzaTransaction: {"count": 0, "maxAllowed": 10},
            EventType.AvanzaErrors: {"count": 0, "maxAllowed": 10},
            EventType.Exception: {"count": 0, "maxAllowed": 20}
        }

        self.blockTransactions = False

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def refreshEventCounter(self):

        if self.events is None:
            self.resetEventCounters()
            return

        if self.events['day'] != datetime.datetime.now(pytz.timezone('Europe/Stockholm')).day:
            self.resetEventCounters()

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def addEvent(self, event: EventType):

        self.refreshEventCounter()
        self.events[event]["count"] += 1

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def resetEvent(self, event: EventType):
        self.refreshEventCounter()
        self.events[event]['count'] = 0

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def isEventAllowed(self, event: EventType):

        self.refreshEventCounter()
        return self.events[event]['count'] <= self.events[event]['maxAllowed']

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def areAllEventsOk(self):
        for event, data in self.events.items():

            if event in EventType:
                if not self.isEventAllowed(event):
                    return False

        return True

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getCurrentFunds(self):
        self.refreshAvanzaHandler()
        return self.avanzaHandler.getCurrentFunds()

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getYieldByDate(self, date: str):
        self.refreshAvanzaHandler()
        return self.avanzaHandler.getYield(date)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getTaxByDate(self, date: str):
        self.refreshAvanzaHandler()
        return self.avanzaHandler.getTax(date)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def doBlockPurchases(self):
        log.log(LogType.Trace, "BLOCKING ALL PURCHASES!")
        self.blockPurchases = True

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def doUnblockPurchases(self):
        log.log(LogType.Trace, "UN-BLOCKING ALL PURCHASES!")
        self.resetEventCounters()
        self.blockPurchases = False
        self.blockTransactions = False

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def doTerminate(self):
        log.log(LogType.Trace, "KILLSWITCH PULLED: TERMINATING!")
        self.terminate = True

# ##############################################################################################################
# ...
# ##############################################################################################################
if __name__ == "__main__":

    MainBroker().run()


