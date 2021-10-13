import time, datetime, json, requests, AvanzaHandler, sys
from avanza import OrderType

BASEURL = "http://localhost:5000/tradingpal/"
BUY_PATH = "getStocksToBuy"
SELL_PATH = "getStocksToSell"

# If price quota differs more than this the higher/lower bid will not be used.
MAX_DEVIATE_PRICE = 1.03
MAX_SANITY_QUOTA_SELL_BUY = 1.12

class MainBroker:

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def __init__(self):

        self.avanzaErrors = 0
        self.avanzaHandler = None

        self.buySellHash = {
            BUY_PATH: 0,
            SELL_PATH: 0
        }

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def handleBuyStocks(self, stocks):
        self.refreshAvanzaHandler()

        for stock in stocks:
            lockKey = None
            try:
                yahooTicker = stock['tickerName']

                lockKey = self.lockStock(yahooTicker)
                print(f"---------- BUYING STOCKS ----------- {stock['currentStock']['name']}/{yahooTicker} -------")
                tickerId = self.avanzaHandler.tickerToId(yahooTicker)

                avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)

                if avanzaDetails is None:
                    print(f"WARN: could not find ticker in avanza: {yahooTicker}")
                    continue

                self.sanityCheckStock(avanzaDetails, stock)
                countAtStart = avanzaDetails['currentCount']
                numberToBuy = stock["numberToBuy"]
                expectedCountWhenDone = countAtStart - numberToBuy
                buyPrice = self.getStockBuyPrice(avanzaDetails['sellPrice'], avanzaDetails['buyPrice'])
                newTotalCount = self.buyOneStockUntilDone(countAtStart, expectedCountWhenDone, yahooTicker, avanzaDetails['accountId'], tickerId, buyPrice, numberToBuy)

            except Exception as ex:
                print(f"Could not buy stock {stock['currentStock']['name']}/{yahooTicker}, {ex}")
            finally:
                self.unlockStock(yahooTicker, lockKey)


            #orderDetails = stocksBuyer.getOrderDetails("")

    # ##############################################################################################################
    # Performs a buy order. Returns the new number of stocks owned.
    # ##############################################################################################################
    def buyOneStockUntilDone(self, countAtStart: int, expectedWhenDone: int, yahooTicker: str, accountId: str, tickerId: str, price: float, volume: int):

        WAIT_SEC_FOR_COMPLETION = 5

        retVal = self.avanzaHandler.placeOrder(yahooTicker, accountId, tickerId, OrderType.BUY, price, volume)

        if retVal['status'] != "OK":
            raise RuntimeError(f"{yahooTicker}: Could not place order towards avanza, {retVal}, accountId {accountId}, price: {price}, volume {volume}")

        for a in range(WAIT_SEC_FOR_COMPLETION):
            time.sleep(1)
            avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)
            if avanzaDetails['currentCount'] == expectedWhenDone:
                print(f"Stock successfully bought {yahooTicker}, volume {volume}")
                return avanzaDetails['currentCount']

        print(f"{yahooTicker} Failed to buy stock in {WAIT_SEC_FOR_COMPLETION} seconds. deleting order")

        try:
            self.avanzaHandler.deleteOrder(accountId, retVal['orderId'])
        except:
            print("Could not delete order... Ignoring")
            pass

        time.sleep(2)
        avanzaDetails = self.avanzaHandler.getTickerDetails(tickerId)

        if avanzaDetails['currentCount'] == expectedWhenDone:
            print(f"{yahooTicker} Successfully bought, volume {volume}")
        elif avanzaDetails['currentCount'] == countAtStart:
            print(f"{yahooTicker} No stocks were bought")
        else:
            print(f"{yahooTicker} partly bought. Got: {avanzaDetails['currentCount'] - countAtStart} out of {volume}")

        return avanzaDetails['currentCount']

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getStockBuyPrice(self, sellPrice: float, buyPrice: float):
        if sellPrice / buyPrice > MAX_DEVIATE_PRICE:
            print("using buyPrice when buying, due to to large difference")
            return buyPrice
        else:
            print("using sellPrice when buying")
            return sellPrice

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def checkIfMarketIsOpen(self):
        pass

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
            raise RuntimeError(f"{sellPrice}/{buyPrice} > {MAX_SANITY_QUOTA_SELL_BUY}. Not reasonable...")

        # ToDo: ENABLE!!
        #if avanzaDetails['currentCount'] != tradingPalDetails['currentStock']['count']:
        #    raise RuntimeError(f"Stock count in avanza does not match count from tradingPal. Abort")

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def handleSellStocks(self, stocks):
        self.refreshAvanzaHandler()
        pass

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def refreshAvanzaHandler(self):

        self.avanzaErrors += 1

        try:
            self.avanzaHandler.testAvanzaConnection()
        except Exception as ex:
            print("Need to refresh AvanzaHandler...")
            self.avanzaHandler = AvanzaHandler.AvanzaHandler()
            self.avanzaHandler.testAvanzaConnection()

        self.avanzaErrors = 0

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def run(self):
        while True:
            try:
                stocksToBuy = self.fetchTickers(BUY_PATH)
                if stocksToBuy is not None and len(stocksToBuy['list']) > 0:
                    self.handleBuyStocks(stocksToBuy['list'])
            except Exception as ex:
                print(f"Exception during buy, {ex}")


            try:
                stocksToSell = self.fetchTickers(SELL_PATH)
                if stocksToSell is not None and len(stocksToSell['list']) > 0:
                    self.handleSellStocks(stocksToSell['list'])
            except Exception as ex:
                print(f"Exception during sell, {ex}")

            if self.avanzaErrors > 0:
                print(f"WARNING: Avanza errors: {self.avanzaErrors}")
            if self.avanzaErrors > 20:
                print("To many avanza errors. exiting!!!")
                exit(27)
                return

            time.sleep(5 * (self.avanzaErrors + 1))

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
                self.buySellHash[path] = newHash
                return dataAsJson

        except Exception as ex:
            print(f"{datetime.datetime.utcnow()} Failed to fetch tickers: {ex}")
            return None

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def lockStock(self, ticker: str):
        try:
            retData = requests.post(BASEURL + "lock", json= {"ticker": ticker})
            if retData.status_code != 200:
                raise RuntimeError(f"Failed to lock stock {ticker}, {retData}")
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
                raise RuntimeError(f"Failed to unlock stock {ticker}, {retData}")
        except Exception as ex:
            print(f"Failed to unlock stock {ticker}, {ex}")
            raise ex

# ##############################################################################################################
# ...
# ##############################################################################################################
if __name__ == "__main__":
    MainBroker().run()