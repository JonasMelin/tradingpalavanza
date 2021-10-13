

import passwords
import hashlib
import pyotp
import datetime
from avanza import Avanza, OrderType


totp = pyotp.TOTP(passwords.Passwords.totpSecret, digest=hashlib.sha1)
print("totp: " + totp.now())

class BuyStocks:

    allowedAcconts = ['Jonas KF', 'Jonas ISK']

    def __init__(self):
        self.login()

    def login(self):
        self.avanza = Avanza({
            'username': passwords.Passwords.username,
            'password': passwords.Passwords.password,
            'totpSecret': passwords.Passwords.totpSecret
        })

    def printOverview(self):
        print(self.avanza.get_overview())

    def tickerToId(self, ticker: str):

        tickerPart = ticker
        flagCode = 'US'

        if ticker is None:
            print("WARN: Provided None as ticker in tickerToId")
            return None

        if '.' in ticker:
            tickerPart = ticker.split('.')[0]
            flagCode = ticker.split('.')[1]

        retval = self.avanza.search_for_stock(tickerPart)

        if retval['totalNumberOfHits'] == 0:
            print(f"WARN: Could not lookup tickerId for ticker: {ticker}")
            return None

        for allHitTypes in retval['hits']:
            if 'topHits' not in allHitTypes:
                print(f"WARN: topHits missing in reply from avanza: {ticker}")
                return None

            for topHit in allHitTypes['topHits']:

                if 'tickerSymbol' not in topHit or 'flagCode' not in topHit or 'id' not in topHit or 'name' not in topHit:
                    print(f"WARN: 'tickerSymbol', 'flagCode', 'id' or 'name' missing in reply from avanza: ticker: {ticker}, topHit: {topHit}")
                    return None

                if tickerPart == topHit['tickerSymbol'] and flagCode == topHit['flagCode']:
                    print(f"Translating {ticker} -> {topHit['name']} (id: {topHit['id']})")
                    return topHit['id']

        print(f"WARN: Failed to lookup ticker {ticker}")
        return None

    def getTickerDetails(self, id: int):

        if id is None:
            return None

        retData = {
            'buyPrice': float,
            'sellPrice': float,
            'accountId': str
        }
        try:
            data = self.avanza.get_stock_info(id)
        except Exception as ex:
            print(f"Could not get stock info, id {id}, {ex}")
            raise ex

        try:
            retData['buyPrice'] = data['buyPrice']
            retData['sellPrice'] = data['sellPrice']

            positions = data['positions']

            if len(positions) == 0:
                raise RuntimeError(f"stock {id} does not exist in any of my accounts")

            for position in positions:
                if position['accountName'] in self.allowedAcconts:
                    retData['accountId'] = position['accountId']

            return retData

        except Exception as ex:
            print(f"Could not extract stock info, id {id}, {ex}")
            raise ex

    def placeOrder(self, accountId: str, tickerId: str, orderType: OrderType, price: float, volume: int):
        print(f"placing order...")

        result = self.avanza.place_order(
            account_id=accountId,
            order_book_id=tickerId,
            order_type=orderType,
            price=price,
            valid_until=datetime.date.fromisoformat('2021-10-14'),
            volume = volume)

        print(result)


if __name__ == "__main__":

    stocksBuyer = BuyStocks()
    stocksBuyer.printOverview()

    id = stocksBuyer.tickerToId("TUI1d.DE")
    details = stocksBuyer.getTickerDetails(id)
    id = stocksBuyer.tickerToId("TIETOS.SE")
    id = stocksBuyer.tickerToId("T")
    id = stocksBuyer.tickerToId("RWE.DE")
    id = stocksBuyer.tickerToId("SHI")

    #stocksBuyer.placeOrder()