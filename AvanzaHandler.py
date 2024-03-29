import datetime, pytz, os, json, enum
from avanza import Avanza, OrderType
from Logger import LogType, Log

passwordPaths = ["./passwords.json", "/passwords/passwords.json", "/home/jonas/Documents/tradingpal/tradingpalavanza/passwords.json"]

class TransactionType(enum.Enum):
   Buy = 1
   Sell = 2

class AvanzaHandler:

    allowedAcconts = ['9288043', '4397855']

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def __init__(self, log):
        self.tickerIdCache = {}
        self.log = log
        self.avanzaTestedOk = False
        self.credentials = {}
        self.avanza = None

        self.PRODUCTION = os.getenv('TP_PROD')

        if self.PRODUCTION is not None and self.PRODUCTION == "true":
            print("RUNNING IN PRODUCTION MODE!!")
        else:
            print("Running in dev mode cause environment variable \"TP_PROD=true\" was not set...")
            self.PRODUCTION = None

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def init(self):
        self.readPasswordsFromFile()
        self.login()
        return self

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def readPasswordsFromFile(self):
        for path in passwordPaths:
            try:
                if os.path.isfile(path):
                    with open(path, "r") as jsonFile:
                        self.credentials = json.load(jsonFile)
                        break

            except Exception:
                pass

        if self.credentials is None or "username" not in self.credentials or\
                "password" not in self.credentials or "totpSecret" not in self.credentials:
            raise RuntimeError(f"Please provide a json file in some of the paths ({passwordPaths}) \
            with keys: \'username\', \'password\' and \'totpSecret\'")

        self.log.log(LogType.Trace, "Successfully read credentials from file...")

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def login(self):
        self.avanza = Avanza({
            'username': self.credentials['username'],
            'password': self.credentials['password'],
            'totpSecret': self.credentials['totpSecret']
        })

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def testAvanzaConnection(self):
        self.avanza.get_overview()

        if not self.avanzaTestedOk:
            self.log.log(LogType.Trace, "Connection to Avanza is OK!")
            self.avanzaTestedOk = True

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def tickerToId(self, yahooTicker: str):

        if yahooTicker in self.tickerIdCache:
            return self.tickerIdCache[yahooTicker]

        tickerPart, flagCode = self.yahooTickerToAvanzaTicker(yahooTicker)
        retval = self.avanza.search_for_stock(tickerPart)

        if retval['totalNumberOfHits'] == 0:
            self.log.log(LogType.Trace, f"WARN: Could not lookup tickerId for ticker: {yahooTicker}")
            return None

        for allHitTypes in retval['hits']:
            if 'topHits' not in allHitTypes:
                self.log.log(LogType.Trace, f"WARN: topHits missing in reply from avanza: {yahooTicker}")
                return None

            for topHit in allHitTypes['topHits']:

                if 'tickerSymbol' not in topHit or 'flagCode' not in topHit or 'id' not in topHit or 'name' not in topHit:
                    self.log.log(LogType.Trace, f"WARN: 'tickerSymbol', 'flagCode', 'id' or 'name' missing in reply from avanza: ticker: {yahooTicker}, topHit: {topHit}")
                    return None

                if tickerPart.lower() == topHit['tickerSymbol'].lower() and flagCode.lower() == topHit['flagCode'].lower():
                    self.log.log(LogType.Trace, f"Translating {yahooTicker} -> {topHit['tickerSymbol']} / {topHit['flagCode']} / {topHit['name']} (id: {topHit['id']})")
                    self.tickerIdCache[yahooTicker] = topHit['id']
                    return topHit['id']

        self.log.log(LogType.Trace, f"WARN: Failed to lookup ticker {yahooTicker}")
        return None

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def secondsSinceDate(self, date: str):
        now = datetime.datetime.now(pytz.timezone('Europe/Stockholm'))
        if ':' not in date:
            raise RuntimeError(f"mal formatted date {date}")
        date = date[:-2] + ":00"
        dateAsDateTime = datetime.datetime.strptime(''.join(date.rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S.%f%z')
        diff = now - dateAsDateTime
        return diff.seconds

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def getTickerDetails(self, tickerId: str):

        if tickerId is None:
            return None

        retData = {
            'buyPrice': float,
            'sellPrice': float,
            'accountId': str,
            'currentCount': int,
            'secondsSinceUpdated': int,
            'tickSize': float,
            'tick1Percent': float
        }
        try:
            data = self.avanza.get_stock_info(tickerId)
        except Exception as ex:
            self.log.log(LogType.Trace, f"Could not get stock info, id {tickerId}, {ex}")
            raise ex

        try:
            retData['secondsSinceUpdated'] = self.secondsSinceDate(data['lastPriceUpdated'])
            retData['buyPrice'] = data['buyPrice'] if 'buyPrice' in data else -1
            retData['sellPrice'] = data['sellPrice'] if 'sellPrice' in data else -1
            retData['tickSize'] = self.guessTickSize(data)
            retData['tick1Percent'] = -1

            if retData['buyPrice'] > 0 and retData['sellPrice'] > 0 and retData['tickSize'] > 0:
                price = (retData['buyPrice'] + retData['sellPrice']) / 2
                onePctPrice = 0.01 * price
                ticks = int(onePctPrice / retData['tickSize'])
                retData['tick1Percent'] = (ticks if ticks > 0 else 1) * retData['tickSize']
                retData['tick1Percent'] = float("%.4f" % (retData['tick1Percent']))

            positions = data['positions']

            if len(positions) == 0:
                raise RuntimeError(f"stock {tickerId} does not exist in any of my accounts")

            for position in positions:
                if position['accountId'] in self.allowedAcconts:
                    retData['accountId'] = position['accountId']
                    retData['currentCount'] = position['volume']
                    retData['currentValueSEK'] = position['value']

            return retData

        except Exception as ex:
            self.log.log(LogType.Trace, f"Could not extract stock info, id {tickerId}, {ex}")
            raise ex

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def guessTickSize(self, data):

        prices = {}

        if 'lastPrice' in data:
            prices[data['lastPrice']] = 0
        if 'lowestPrice' in data:
            prices[data['lowestPrice']] = 0
        if 'highestPrice' in data:
            prices[data['highestPrice']] = 0
        if 'buyPrice' in data:
            prices[data['buyPrice']] = 0
        if 'sellPrice' in data:
            prices[data['sellPrice']] = 0

        if 'orderDepthLevels' in data:
            for nextDepth in data['orderDepthLevels']:
                try:
                    prices[nextDepth['sell']['price']] = 0
                    prices[nextDepth['buy']['price']] = 0
                except Exception:
                    pass

        if 'latestTrades' in data:
            for nextTrade in data['latestTrades']:
                if 'price' in nextTrade:
                    prices[nextTrade['price']] = 0

        prices = sorted(prices)

        if len(prices) < 2:
            self.log.log(LogType.Trace, "Could not get tick size")
            return -1

        tickSize = 100000.0
        prior = None
        for p in prices:
            if prior is not None:
                diff = p - prior
                if diff < tickSize:
                    tickSize = diff
            prior = p

        return float("%.4f" % (tickSize * 2))

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def placeOrder(self, yahooTicker: str, accountId: str, tickerId: str, transactionType: TransactionType, price: float, volume: int):

        if transactionType == TransactionType.Buy:
            orderType = OrderType.BUY
        else:
            orderType = OrderType.SELL

        self.log.log(LogType.Trace, f"placing order... {yahooTicker}/{self.yahooTickerToAvanzaTicker(yahooTicker)}, accountId: {accountId}, tickerId: {tickerId}, {orderType}, price: {price}, volume: {volume}")

        if self.PRODUCTION is None:
            self.log.log(LogType.Trace, "DEV mode. Not placing order towards avanza...")
            return {
                "messages": [],
                "orderId": "1234",
                "requestId": "3241",
                "status": "SUCCESS"
            }

        # Returns: {'orderRequestStatus': 'SUCCESS', 'message': '', 'orderId': '420807539'}
        result = self.avanza.place_order(
            account_id=accountId,
            order_book_id=tickerId,
            order_type=orderType,
            price=price,
            valid_until=datetime.date.fromisoformat(self.generateOrderValidDate()),
            volume = volume)

        # Could not place Avanza order: {'orderRequestStatus': 'ERROR', 'message': 'Du har tyvärr inte tillräcklig täckning på din depå för att genomföra ordern. Kontakta vår kundservice för mer information.'}, TEO: tickerId: 347455, transaction: TransactionType.Buy, accountId 9288043, price: 5.05, volume 40, expectedWhenDone: 123, countAtStart: 83
        if result is not None and 'message' in result and "Du har tyvärr inte tillräcklig täckning" in result['message']:
            print("Out of funds...")
            result["blockPurchase"] = True

        if result is not None and 'message' in result and "Orderläggningen är tillfälligt stängd" in result['message']:
            print("System temporarily closed...")
            result["blockTransactions"] = True


        return result

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getYield(self, date: str):
        return self.getTransactionsByDateAndType(date, "DIVIDEND")

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getTax(self, date: str):
        return self.getTransactionsByDateAndType(date, "FOREIGN_TAX")

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getTransactionsByDateAndType(self, date: str, type: str):

        retData = []

        try:
            transactions = self.getTransactions(date)

            for transaction in transactions:
                if transaction['transactionType'] == type:
                    retData.append(transaction)

        except Exception as ex:
            print(f"Could not get transaction {type} for date {date}: {ex}")

        return retData

    # ##############################################################################################################
    # Tested!
    # ##############################################################################################################
    def getTransactions(self, filterByDate:str = None):

        finalResult = []
        rawTransactions = self.avanza.get_transactions()

        if rawTransactions is None or 'transactions' not in rawTransactions:
            self.log.log(LogType.Trace, "got no transactions from Avanza or malforrmatted...")
            return []

        for transaction in rawTransactions['transactions']:
            if 'account' not in transaction or 'name' not in transaction['account']:
                continue

            if filterByDate is not None and 'verificationDate' in transaction and filterByDate != transaction['verificationDate']:
                continue

            if transaction['account']['id'] in self.allowedAcconts:
                finalResult.append(transaction)

        return finalResult

    # ##############################################################################################################
    # Tested!
    # ##############################################################################################################
    def getOverview(self):

        finalResult = []
        rawOverview = self.avanza.get_overview()

        if rawOverview is None or 'accounts' not in rawOverview:
            self.log.log(LogType.Trace, "got no overview from Avanza or malforrmatted...")
            return []

        for account in rawOverview['accounts']:
            if account['accountId'] in self.allowedAcconts:
                finalResult.append(account)

        return finalResult

    # ##############################################################################################################
    # Tested!
    # ##############################################################################################################
    def getCurrentFunds(self):

        accounts = self.getOverview()
        totFunds = 0

        for account in accounts:
            totFunds += account['totalBalance']

        return totFunds

    # ##############################################################################################################
    # ToDo: Implement
    # ##############################################################################################################
    def getOrderDetails(self, orderId: str):
        result = self.avanza.get_deals_and_orders()

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def deleteOrder(self, accountId: str, orderId: str):
        result = self.avanza.delete_order(accountId, orderId)
        return result

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def generateOrderValidDate(self):
        now = datetime.datetime.now(pytz.timezone('Europe/Stockholm'))
        return f"{now.year}-{now.month:02}-{now.day:02}"

    # ##############################################################################################################
    # Tested
    # ##############################################################################################################
    def yahooTickerToAvanzaTicker(self, yahooTicker):
        tickerPart = yahooTicker
        flagCode = 'US'

        if yahooTicker is None:
            self.log.log(LogType.Trace, "WARN: Provided None as ticker in tickerToId")
            return None

        if '.' in yahooTicker:
            tickerPart = yahooTicker.split('.')[0]
            flagCode = yahooTicker.split('.')[1]

        if flagCode.lower() == 'de':
            tickerPart += "d"

        if flagCode.lower() == 'to':
            flagCode = 'CA'

        if flagCode.lower() == 'ol':
            flagCode = 'NO'

        if flagCode.lower() == 'he':
            flagCode = 'FI'

        if flagCode.lower() == 'st':
            flagCode = 'SE'

        if flagCode.lower() == 'co':
            flagCode = 'DK'

        if flagCode == 'SE':
            tickerPart = tickerPart.replace('-', ' ')
        else:
            tickerPart = tickerPart.replace('-', '.')

        return tickerPart, flagCode

# ##############################################################################################################
# ...
# ##############################################################################################################
if __name__ == "__main__":
    stocksBuyer = AvanzaHandler(Log()).init()
    stocksBuyer.testAvanzaConnection()

    id = stocksBuyer.tickerToId("BBD-B.TO")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    stocksBuyer.getTransactions()
    stocksBuyer.getOverview()
    stocksBuyer.getCurrentFunds()

"""
    id = stocksBuyer.tickerToId("CAPMAN.HE")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("TELIA.ST")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("HAV-B.ST")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("AR4.DE")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("AKSO.OL")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("CAPMAN.HE")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("DANSKE.CO")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

"""
    #stocksBuyer.placeOrder("DANSKE.CO", tickerDetails['accountId'], id, OrderType.BUY, 109.71, 1)
