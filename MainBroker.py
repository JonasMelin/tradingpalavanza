import time, datetime, json, requests, AvanzaHandler, sys, pytz, enum
from avanza import OrderType

#
# ToDo:
# Proper log function to file
#

BASEURL = "http://192.168.1.50:5000/tradingpal/"
BUY_PATH = "getStocksToBuy"
SELL_PATH = "getStocksToSell"

# If buy/sell price quota differs more than this, a buy bid will use buy price, sell bid use sell price.
MAX_DEVIATE_PRICE = 1.03

# If buy/sell price quota differs more than this, the entire transaction will be cancelled
MAX_SANITY_QUOTA_SELL_BUY = 1.12

# will not go through with transaction if stock price was not updated last sec
# Note that we get delayed prices 15 minutes. ToDo: Fix this depending upon market...
MAX_TIME_SINCE_STOCK_PRICE_UPDATED_SEC = 1200

# Define during what hours transactions shall be attempted.
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 23

class TransactionType(enum.Enum):
   Buy = 1
   Sell = 2

class EventType(enum.Enum):
    AvanzaTransaction = 1,
    AvanzaErrors = 2

class MainBroker:

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def __init__(self):

        self.resetEventCounters()
        self.avanzaHandler = self.refreshAvanzaHandler()

        self.buySellHash = {
            BUY_PATH: 0,
            SELL_PATH: 0
        }

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

                print(f"---------- TRANSACTING STOCK ----------- {stock['currentStock']['name']}/{yahooTicker} -------")
                tickerId = self.avanzaHandler.tickerToId(yahooTicker)
                avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)

                if avanzaDetails is None:
                    print(f"WARN: could not find ticker in avanza: {yahooTicker}")
                    continue

                self.sanityCheckStock(avanzaDetails, stock)
                self.addEvent(EventType.AvanzaTransaction)

                countAtStart = avanzaDetails['currentCount']

                if transactionType == TransactionType.Sell:
                    price = avanzaDetails["buyPrice"]
                    startPrice = avanzaDetails["buyPrice"]
                else:
                    price = avanzaDetails["sellPrice"]
                    startPrice = avanzaDetails["sellPrice"]

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
                        newTotalInvestedSek = int(stock['currentStock']['totalInvestedSek'] + (newTotalCount - countAtStart) * startPrice)
                        self.updateStock(
                            yahooTicker,
                            price if transactionType == TransactionType.Buy else None,
                            price if transactionType == TransactionType.Sell else None,
                            newTotalCount, lockKey, stock['currentStock']['name'], newTotalInvestedSek)

                        break
                    
            except Exception as ex:
                print(f"Could not buy stock {stock['currentStock']['name']}/{yahooTicker}, {ex}")
            finally:
                self.unlockStock(yahooTicker, lockKey)

    # ##############################################################################################################
    # Performs a buy order. Returns the new number of stocks owned.
    # ##############################################################################################################
    def doOneTransactionAndCheckResult(self, transactionType: TransactionType, countAtStart: int, expectedWhenDone: int, yahooTicker: str, accountId: str, tickerId: str, price: float, volume: int):

        WAIT_SEC_FOR_COMPLETION = 3

        if transactionType == TransactionType.Buy:
            orderType = OrderType.BUY
        else:
            orderType = OrderType.SELL

        retVal = self.avanzaHandler.placeOrder(yahooTicker, accountId, tickerId, orderType, price, volume)
        time.sleep(1)

        if retVal['status'] != "SUCCESS":
            self.avanzaHandler.deleteOrder(accountId, retVal['orderId'])
            raise RuntimeError(f"{yahooTicker}: Could not place order {orderType} towards avanza, {retVal}, accountId {accountId}, price: {price}, volume {volume}")

        for a in range(WAIT_SEC_FOR_COMPLETION):
            avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)
            if avanzaDetails['currentCount'] == expectedWhenDone:
                print(f"{yahooTicker} Stock successfully transacted {orderType}, volume {volume}")
                return avanzaDetails['currentCount']

            print(f"{yahooTicker} {orderType} order is on market.. Waiting...")
            sys.stdout.flush()
            time.sleep(1)

        print(f"{yahooTicker} {orderType} Failed to transact stock in {WAIT_SEC_FOR_COMPLETION} seconds. deleting order")

        try:
            self.avanzaHandler.deleteOrder(accountId, retVal['orderId'])
        except Exception:
            print("Could not delete order... Ignoring")

        sys.stdout.flush()
        time.sleep(1)
        avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)

        if avanzaDetails['currentCount'] == expectedWhenDone:
            print(f"{yahooTicker} {orderType} Successfully transacted, volume {volume}")
        elif avanzaDetails['currentCount'] == countAtStart:
            print(f"{yahooTicker} {orderType} No stocks transacted")
        else:
            print(f"{yahooTicker} {orderType} partly transacted. Current: {avanzaDetails['currentCount']}, before: {countAtStart} out of {volume}")

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

        print(f"Changing bidValue: {transactionType} / from {lastPrice} to {newVal}")
        return newVal


    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def sanityCheckStock(self, avanzaDetails, tradingPalDetails):

        sellPrice = avanzaDetails['sellPrice']
        buyPrice = avanzaDetails['buyPrice']

        if sellPrice is None or sellPrice < 0.01 or sellPrice > 5000.0:
            raise RuntimeError(f"Stock sell price is not reasonable {sellPrice}")
        if buyPrice is None or buyPrice < 0.01 or buyPrice > 5000.0:
            raise RuntimeError(f"Stock buy price is not reasonable {buyPrice}")
        if buyPrice > sellPrice:
            raise RuntimeError(f"buyPrice {buyPrice} is less than sellPrice {sellPrice}")

        if (sellPrice / buyPrice) > MAX_SANITY_QUOTA_SELL_BUY:
            raise RuntimeError(f"sell/buy price: {sellPrice}/{buyPrice} > {MAX_SANITY_QUOTA_SELL_BUY}. Not reasonable...")

        if avanzaDetails['secondsSinceUpdated'] > MAX_TIME_SINCE_STOCK_PRICE_UPDATED_SEC:
            raise RuntimeError(f"Stock price was not updated. So, the market is probably closed... seconds since updated {avanzaDetails['secondsSinceUpdated']}")

        if avanzaDetails['currentCount'] != tradingPalDetails['currentStock']['count']:
            raise RuntimeError(f"Stock count in avanza does not match count from tradingPal. Abort")

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def refreshAvanzaHandler(self):

        self.addEvent(EventType.AvanzaErrors)

        try:
            self.avanzaHandler.testAvanzaConnection()
        except Exception:
            print("Need to refresh AvanzaHandler...")
            self.avanzaHandler = AvanzaHandler.AvanzaHandler()
            self.avanzaHandler.testAvanzaConnection()

        self.resetEvent(EventType.AvanzaErrors)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def run(self):

        print("Starting up, test connections to trading pal algorithm...")

        self.waitForConnectonToTradingPal()

        while True:
            if not self.marketsOpenDaytime():
                print("Markets closed...")
                sys.stdout.flush()
                time.sleep(120)
                continue

            if not self.isEventAllowed(EventType.AvanzaTransaction) or not self.isEventAllowed(EventType.AvanzaErrors):
                print(f"To many events in one day. Stepping back... {self.events}")
                sys.stdout.flush()
                time.sleep(3600)
                continue

            try:
                stocksToBuy = self.fetchTickers(BUY_PATH)
                if stocksToBuy is not None and len(stocksToBuy['list']) > 0:
                    self.doStocksTransaction(stocksToBuy['list'], TransactionType.Buy)
                    sys.stdout.flush()
                    time.sleep(120)
            except Exception as ex:
                print(f"Exception during buy, {ex}")

            try:
                stocksToSell = self.fetchTickers(SELL_PATH)
                if stocksToSell is not None and len(stocksToSell['list']) > 0:
                    self.doStocksTransaction(stocksToSell['list'], TransactionType.Sell)
                    sys.stdout.flush()
                    time.sleep(120)
            except Exception as ex:
                print(f"Exception during sell, {ex}")

            sys.stdout.flush()
            time.sleep(60)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def waitForConnectonToTradingPal(self):
        while True:
            if self.fetchTickers(BUY_PATH) is not None:
                print("Connection to trading pal algorithm OK!")
                break
            else:
                print(f"Connection to tradingpal is still no OK. Retrying...")
                sys.stdout.flush()
                time.sleep(5)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def fetchTickers(self, path: str):

        try:
            retData = requests.get(BASEURL + path)
            if retData.status_code != 200:
                print(f"{datetime.datetime.utcnow()} Failed to fetch stocks... retrying")
                sys.stdout.flush()
                time.sleep(60)

            dataAsJson = json.loads(retData.content)
            newHash = hash(str(dataAsJson["list"]))

            if self.buySellHash[path] == newHash:
                return None
            else:
                print("Updated prices!!")
                self.buySellHash[path] = newHash
                return dataAsJson

        except Exception as ex:
            print(f"{datetime.datetime.utcnow()} Failed to fetch tickers: {ex}")
            return None

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def updateStock(self, tickerName: str, boughtAt, soldAt, count: int, lockKey: int, name: str, totalInvestedSek: int):

        body = {
            'ticker': tickerName,
            'boughtAt': boughtAt,
            'soldAt': soldAt,
            'count': count,
            'lockKey': lockKey,
            'name': name,
            'totalInvestedSek': totalInvestedSek,
        }

        print(f"Saving stock data: {body}")

        try:
            retData = requests.post(BASEURL + "updateStock", json=body)
            if retData.status_code != 200:
                raise RuntimeError(f"Failed to update stock {tickerName}, {retData.content}")
        except Exception as ex:
            print(f"Failed to update stock {tickerName}, {ex}")
            raise ex

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
            print(f"Failed to lock stock {ticker}, {ex}")
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
            print(f"Failed to unlock stock {ticker}, {ex}")
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
            EventType.AvanzaErrors: {"count": 0, "maxAllowed": 10}
        }

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
if __name__ == "__main__":

    MainBroker().run()


