import passwords
import datetime
import pytz
from avanza import Avanza, OrderType

class AvanzaHandler:

    STUB_BUY = False
    allowedAcconts = ['Jonas KF', 'Jonas ISK']

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def __init__(self):
        self.login()

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def login(self):
        self.avanza = Avanza({
            'username': passwords.Passwords.username,
            'password': passwords.Passwords.password,
            'totpSecret': passwords.Passwords.totpSecret
        })

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def testAvanzaConnection(self):
        self.avanza.get_overview()

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def tickerToId(self, yahooTicker: str):

        tickerPart, flagCode = self.yahooTickerToAvanzaTicker(yahooTicker)

        retval = self.avanza.search_for_stock(tickerPart)

        if retval['totalNumberOfHits'] == 0:
            print(f"WARN: Could not lookup tickerId for ticker: {yahooTicker}")
            return None

        for allHitTypes in retval['hits']:
            if 'topHits' not in allHitTypes:
                print(f"WARN: topHits missing in reply from avanza: {yahooTicker}")
                return None

            for topHit in allHitTypes['topHits']:

                if 'tickerSymbol' not in topHit or 'flagCode' not in topHit or 'id' not in topHit or 'name' not in topHit:
                    print(f"WARN: 'tickerSymbol', 'flagCode', 'id' or 'name' missing in reply from avanza: ticker: {yahooTicker}, topHit: {topHit}")
                    return None

                if tickerPart == topHit['tickerSymbol'] and flagCode == topHit['flagCode']:
                    print(f"Translating {yahooTicker} -> {topHit['tickerSymbol']} / {topHit['flagCode']} / {topHit['name']} (id: {topHit['id']})")
                    return topHit['id']

        print(f"WARN: Failed to lookup ticker {yahooTicker}")
        return None

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def secondsSinceDate(self, date: str):
        now = datetime.datetime.now(pytz.timezone('Europe/Stockholm'))
        date = date[:-2] + ":00"
        dateAsDateTime = datetime.datetime.strptime(''.join(date.rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S.%f%z')
        diff = now - dateAsDateTime
        return diff.seconds

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def getTickerDetails(self, tickerId: str):

        if tickerId is None:
            return None

        retData = {
            'buyPrice': float,
            'sellPrice': float,
            'accountId': str,
            'currentCount': int,
            'secondsSinceUpdated': int
        }
        try:
            data = self.avanza.get_stock_info(tickerId)
        except Exception as ex:
            print(f"Could not get stock info, id {tickerId}, {ex}")
            raise ex

        try:
            retData['secondsSinceUpdated'] = self.secondsSinceDate(data['lastPriceUpdated'])
            retData['buyPrice'] = data['buyPrice']
            retData['sellPrice'] = data['sellPrice']

            positions = data['positions']

            if len(positions) == 0:
                raise RuntimeError(f"stock {tickerId} does not exist in any of my accounts")

            for position in positions:
                if position['accountName'] in self.allowedAcconts:
                    retData['accountId'] = position['accountId']
                    retData['currentCount'] = position['volume']
                    retData['currentValueSEK'] = position['value']

            return retData

        except Exception as ex:
            print(f"Could not extract stock info, id {tickerId}, {ex}")
            raise ex

    # ##############################################################################################################
    # ToDo: Implement
    # ##############################################################################################################
    def placeOrder(self, yahooTicker: str, accountId: str, tickerId: str, orderType: OrderType, price: float, volume: int):
        print(f"placing order... {yahooTicker}/{self.yahooTickerToAvanzaTicker(yahooTicker)}, accountId: {accountId}, tickerId: {tickerId}, {orderType}, price: {price}, volume: {volume}")

        if self.STUB_BUY:
            return {
                "messages": [],
                "orderId": "1234",
                "requestId": "3241",
                "status": "OK"
            }

        result = self.avanza.place_order(
            account_id=accountId,
            order_book_id=tickerId,
            order_type=orderType,
            price=price,
            valid_until=datetime.date.fromisoformat(self.generateOrderValidDate()),
            volume = volume)

        return result

    # ##############################################################################################################
    # ToDo: Implement
    # ##############################################################################################################
    def getOrderDetails(self, orderId: str):
        result = self.avanza.get_deals_and_orders()

    # ##############################################################################################################
    # ToDo: Implement
    # ##############################################################################################################
    def deleteOrder(self, accountId: str, orderId: str):
        result = self.avanza.delete_order(accountId, orderId)

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def generateOrderValidDate(self):
        now = datetime.datetime.now(pytz.timezone('Europe/Stockholm'))
        return f"{now.year}-{now.month}-{now.day}"

    # ##############################################################################################################
    # ...
    # ##############################################################################################################
    def yahooTickerToAvanzaTicker(self, yahooTicker):
        tickerPart = yahooTicker
        flagCode = 'US'

        if yahooTicker is None:
            print("WARN: Provided None as ticker in tickerToId")
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
    stocksBuyer = AvanzaHandler()
    stocksBuyer.testAvanzaConnection()

    id = stocksBuyer.tickerToId("CAPMAN.HE")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("TELIA.ST")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("HAV-B.ST")
    tickerDetails = stocksBuyer.getTickerDetails(id)
    print(tickerDetails)

    id = stocksBuyer.tickerToId("BBD-B.TO")
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

    #stocksBuyer.placeOrder("TUI1.DE", tickerDetails['accountId'], id, OrderType.BUY, tickerDetails['buyPrice'], 1)
