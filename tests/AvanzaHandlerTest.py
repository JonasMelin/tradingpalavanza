from AvanzaHandler import AvanzaHandler, TransactionType
from Logger import Log
from unittest.mock import MagicMock

getTransactionsReply = {'transactions': [{'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': -54.99, 'currency': 'USD', 'description': 'Sålt 1', 'orderbook': {'isin': 'US0886061086', 'currency': 'USD', 'name': 'BHP Group Ltd', 'flagCode': 'US', 'id': '35068', 'type': 'STOCK'}, 'price': 54.99, 'volume': -1, 'transactionType': 'SELL', 'verificationDate': '2021-11-11', 'id': 'DEAL-9288043-391275580'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': -40.88, 'currency': 'CAD', 'description': 'Sålt 8', 'orderbook': {'isin': 'CA47009M8896', 'currency': 'CAD', 'name': 'Jaguar Mining Inc', 'flagCode': 'CA', 'id': '85697', 'type': 'STOCK'}, 'price': 5.11, 'volume': -8, 'transactionType': 'SELL', 'verificationDate': '2021-11-11', 'id': 'DEAL-9288043-391275524'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': -47.55, 'currency': 'CAD', 'description': 'Sålt 3', 'orderbook': {'isin': 'CA8910546032', 'currency': 'CAD', 'name': 'Torex Gold Resources Inc', 'flagCode': 'CA', 'id': '282537', 'type': 'STOCK'}, 'price': 15.85, 'volume': -3, 'transactionType': 'SELL', 'verificationDate': '2021-11-11', 'id': 'DEAL-9288043-391115211'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': 174.46, 'currency': 'SEK', 'description': 'Sålt 11 st till kurs 15,86000 CAD Rättelse BOSTON PIZZA ROYALTIES INCOME FUND', 'amount': -1712.0, 'orderbook': {'isin': 'CA1010841015', 'currency': 'CAD', 'name': 'Boston Pizza Royalties Income Fund', 'flagCode': 'CA', 'id': '194368', 'type': 'STOCK'}, 'currencyRate': 9.87121, 'price': 15.86, 'volume': 11.0, 'commission': -10.0, 'noteId': 'RBBDWMDJ', 'transactionType': 'SELL', 'verificationDate': '2021-11-10', 'id': '2926528986RBBDWMDJ4'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': -174.46, 'currency': 'SEK', 'description': 'Sålt 11 st till kurs 15,86000 CAD BOSTON PIZZA ROYALTIES INCOME FUND', 'amount': 1193.0, 'orderbook': {'isin': 'CA1010841015', 'currency': 'CAD', 'name': 'Boston Pizza Royalties Income Fund', 'flagCode': 'CA', 'id': '194368', 'type': 'STOCK'}, 'currencyRate': 6.877364, 'price': 15.86, 'volume': -11.0, 'commission': 7.0, 'noteId': 'GRGSJQFM', 'transactionType': 'SELL', 'verificationDate': '2021-11-10', 'id': '2924450929GRGSJQFM4'}, {'account': {'type': 'Investeringssparkonto', 'name': 'Sophia ISK', 'id': '9950862'}, 'sum': 12.0, 'currency': 'SEK', 'description': 'Utdelning 12 st à 1,00 INVESTOR B', 'amount': 12.0, 'orderbook': {'isin': 'SE0015811963', 'currency': 'SEK', 'name': 'Investor B', 'flagCode': 'SE', 'id': '5247', 'type': 'STOCK'}, 'price': 1.0, 'volume': 12.0, 'transactionType': 'DIVIDEND', 'verificationDate': '2021-11-10', 'id': '2924121972ABBBPNPT79827'}, {'account': {'type': 'Investeringssparkonto', 'name': 'Theodor ISK', 'id': '9920769'}, 'sum': 12.0, 'currency': 'SEK', 'description': 'Utdelning 12 st à 1,00 INVESTOR B', 'amount': 12.0, 'orderbook': {'isin': 'SE0015811963', 'currency': 'SEK', 'name': 'Investor B', 'flagCode': 'SE', 'id': '5247', 'type': 'STOCK'}, 'price': 1.0, 'volume': 12.0, 'transactionType': 'DIVIDEND', 'verificationDate': '2021-11-10', 'id': '2924121107ABBBPNPT78963'}, {'account': {'type': 'Investeringssparkonto', 'name': 'Alexander ISK', 'id': '9920025'}, 'sum': 12.0, 'currency': 'SEK', 'description': 'Utdelning 12 st à 1,00 INVESTOR B', 'amount': 12.0, 'orderbook': {'isin': 'SE0015811963', 'currency': 'SEK', 'name': 'Investor B', 'flagCode': 'SE', 'id': '5247', 'type': 'STOCK'}, 'price': 1.0, 'volume': 12.0, 'transactionType': 'DIVIDEND', 'verificationDate': '2021-11-10', 'id': '2924121077ABBBPNPT78933'}, {'account': {'type': 'Investeringssparkonto', 'name': 'Jonas ISK', 'id': '4397855'}, 'sum': 27.0, 'currency': 'SEK', 'description': 'Utdelning 27 st à 1,00 INVESTOR B', 'amount': 27.0, 'orderbook': {'isin': 'SE0015811963', 'currency': 'SEK', 'name': 'Investor B', 'flagCode': 'SE', 'id': '5247', 'type': 'STOCK'}, 'price': 1.0, 'volume': 27.0, 'transactionType': 'DIVIDEND', 'verificationDate': '2021-11-10', 'id': '2923959680ABBBPNPS17711'}, {'account': {'type': 'AktieFondkonto', 'name': 'Jonas buffertkonto', 'id': '4397847'}, 'currency': 'SEK', 'description': 'Överföring från Collector 6700698', 'amount': 49.0, 'transactionType': 'DEPOSIT', 'verificationDate': '2021-11-10', 'id': '2923736182ECQKDLQK1'}, {'account': {'type': 'SparkontoPlus', 'name': 'AlexanderVeckopeng', 'id': '6700698'}, 'currency': 'SEK', 'description': 'Överföring till Avanzakonto 4397847', 'amount': -49.0, 'transactionType': 'WITHDRAW', 'verificationDate': '2021-11-10', 'id': '2923736166ECQKDLPN1'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': -174.46, 'currency': 'SEK', 'description': 'Sålt 11 st till kurs 15,86000 CAD BOSTON PIZZA ROYALTIES INCOME FUND', 'amount': 1712.0, 'orderbook': {'isin': 'CA1010841015', 'currency': 'CAD', 'name': 'Boston Pizza Royalties Income Fund', 'flagCode': 'CA', 'id': '194368', 'type': 'STOCK'}, 'currencyRate': 9.87121, 'price': 15.86, 'volume': -11.0, 'commission': 10.0, 'noteId': 'GRGRLKHK', 'transactionType': 'SELL', 'verificationDate': '2021-11-09', 'id': '2923445394GRGRLKHK4'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': -99.97, 'currency': 'SEK', 'description': 'Sålt 1 st till kurs 99,97000 USD AMERESCO INC', 'amount': 846.0, 'orderbook': {'isin': 'US02361E1082', 'currency': 'USD', 'name': 'Ameresco Inc', 'flagCode': 'US', 'id': '326657', 'type': 'STOCK'}, 'currencyRate': 8.555059, 'price': 99.97, 'volume': -1.0, 'commission': 9.0, 'noteId': 'GRGJKXNJ', 'transactionType': 'SELL', 'verificationDate': '2021-11-08', 'id': '2920499791GRGJKXNJ4'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'currency': 'SEK', 'description': 'Utländsk källskatt DNB BANK ASA 25%', 'amount': -56.48, 'orderbook': {'isin': 'NO0010161896', 'currency': 'NOK', 'name': 'DNB Bank', 'flagCode': 'NO', 'id': '52628', 'type': 'STOCK'}, 'volume': 25.0, 'transactionType': 'FOREIGN_TAX', 'verificationDate': '2021-11-08', 'id': '2917854474ABBBPNNL2553'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': 225.93, 'currency': 'SEK', 'description': 'Utdelning 25 st à 9,03 DNB BANK ASA', 'amount': 225.93, 'orderbook': {'isin': 'NO0010161896', 'currency': 'NOK', 'name': 'DNB Bank', 'flagCode': 'NO', 'id': '52628', 'type': 'STOCK'}, 'price': 9.037323, 'volume': 25.0, 'transactionType': 'DIVIDEND', 'verificationDate': '2021-11-08', 'id': '2917854473ABBBPNNL2552'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'currency': 'SEK', 'description': 'Riskpremie', 'amount': -0.49, 'transactionType': 'UNKNOWN', 'verificationDate': '2021-11-08', 'id': '2917529679LBGPBZKK1'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': 135.42, 'currency': 'SEK', 'description': 'Köpt 6 st till kurs 22,57000 USD SINOPEC SHANGHI PETROCHEM ADR', 'amount': -1175.0, 'orderbook': {'isin': 'US82935M1099', 'currency': 'USD', 'name': 'Sinopec Shanghai Petrochemical Co Ltd', 'flagCode': 'US', 'id': '496178', 'type': 'STOCK'}, 'currencyRate': 8.610473, 'price': 22.57, 'volume': 6.0, 'commission': 9.0, 'noteId': 'GRFRJDPL', 'transactionType': 'BUY', 'verificationDate': '2021-11-04', 'id': '2915137462GRFRJDPL4'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'sum': 49.34, 'currency': 'SEK', 'description': 'Köpt 2 st till kurs 24,67000 USD AT&T INC', 'amount': -434.0, 'orderbook': {'isin': 'US00206R1023', 'currency': 'USD', 'name': 'AT&T Inc', 'flagCode': 'US', 'id': '3507', 'type': 'STOCK'}, 'currencyRate': 8.610473, 'price': 24.67, 'volume': 2.0, 'commission': 9.0, 'noteId': 'GRFRJDNQ', 'transactionType': 'BUY', 'verificationDate': '2021-11-04', 'id': '2915137388GRFRJDNQ4'}, {'account': {'type': 'Kapitalforsakring', 'name': 'Jonas KF', 'id': '9288043'}, 'currency': 'SEK', 'description': 'Överföring från Avanzakonto 4397855', 'amount': 2900.0, 'transactionType': 'DEPOSIT', 'verificationDate': '2021-11-04', 'id': '2914903191ECQGXTGP1'}, {'account': {'type': 'Investeringssparkonto', 'name': 'Jonas ISK', 'id': '4397855'}, 'currency': 'SEK', 'description': 'Överföring till Avanzakonto 9288043', 'amount': -2900.0, 'transactionType': 'WITHDRAW', 'verificationDate': '2021-11-04', 'id': '2914903190ECQGXTGN1'}], 'totalNumberOfTransactions': 20}
getStockInfoReply= {'priceThreeMonthsAgo': 1.54, 'priceOneWeekAgo': 1.99, 'priceOneMonthAgo': 2.04, 'priceSixMonthsAgo': 0.9, 'priceAtStartOfYear': 0.48, 'priceOneYearAgo': 0.3, 'priceThreeYearsAgo': 1.68, 'priceFiveYearsAgo': 1.95, 'marketPlace': 'Toronto Stock Exchange', 'flagCode': 'CA', 'loanFactor': 60.0, 'hasInvestmentFees': False, 'quoteUpdated': '2021-11-17T15:31:24.000+0100', 'currency': 'CAD', 'lowestPrice': 1.77, 'highestPrice': 1.79, 'totalVolumeTraded': 805834, 'buyPrice': 1.78, 'sellPrice': 1.79, 'shortSellable': False, 'isin': 'CA0977512007', 'lastPrice': 1.78, 'lastPriceUpdated': '2021-11-17T15:31:24.000+0100', 'change': -0.06, 'changePercent': -3.26, 'totalValueTraded': 0.0, 'tradable': True, 'tickerSymbol': 'BBD.B', 'name': 'Bombardier Inc B', 'id': '76426', 'country': 'Kanada', 'keyRatios': {'volatility': 32.53, 'priceEarningsRatio': 0.65, 'directYield': 0.0}, 'numberOfOwners': 219, 'superLoan': False, 'numberOfPriceAlerts': 0, 'pushPermitted': False, 'dividends': [], 'relatedStocks': [{'flagCode': 'FR', 'priceOneYearAgo': 41.28, 'lastPrice': 33.56, 'name': 'Alstom SA', 'id': '745784'}, {'flagCode': 'DE', 'priceOneYearAgo': 5.082, 'lastPrice': 10.34, 'name': 'thyssenkrupp AG', 'id': '732329'}, {'flagCode': 'US', 'priceOneYearAgo': 77.52, 'lastPrice': 103.37, 'name': 'General Electric Co', 'id': '4438'}, {'flagCode': 'FR', 'priceOneYearAgo': 90.01, 'lastPrice': 114.64, 'name': 'Airbus SE', 'id': '745811'}, {'flagCode': 'FI', 'priceOneYearAgo': 8.02, 'lastPrice': 13.28, 'name': 'W�rtsil� Oyj Abp', 'id': '52849'}], 'company': {'sector': 'Industri', 'stocks': [{'totalNumberOfShares': 2132698299, 'name': 'Bombardier Inc B'}, {'totalNumberOfShares': 308734929, 'name': 'Bombardier Inc A'}, {'totalNumberOfShares': 9400000, 'name': 'Bombardier Inc Pref'}], 'totalNumberOfShares': 2450833228, 'chairman': 'Pierre Beaudoin', 'description': 'Bombardier �r ett tillverkande f�retag som konstruerar, utvecklar, producerar och s�ljer transportutrustning �ver hela v�rlden. F�retaget tillverkar kommersiella aff�rsjetplan och ger service efter leverans. Bombardier �r ocks� verksamt inom j�rnv�gsindustrin vilket omfattar t�g, delsystem, systemintegration och signall�sningar. Bolaget grundades 1942 och har sitt huvudkontor i Montreal, Kanada.', 'marketCapital': 4504586536, 'marketCapitalCurrency': 'CAD', 'name': 'Bombardier', 'id': '100213', 'CEO': 'Eric Martel'}, 'orderDepthLevels': [{'buy': {'percent': 8.70265914585012, 'price': 1.78, 'volume': 10800}, 'sell': {'percent': 100.0, 'price': 1.79, 'volume': 124100}}], 'marketMakerExpected': False, 'orderDepthReceivedTime': '2021-11-17T15:31:24.000+0100', 'latestTrades': [], 'marketTrades': False, 'positions': [{'accountName': 'Jonas KF', 'accountType': 'Kapitalforsakring', 'profit': 3437.27, 'accountId': '9288043', 'volume': 381, 'averageAcquiredPrice': 3.520703, 'profitPercent': 256.25, 'acquiredValue': 1341.387843, 'value': 4778.66}], 'positionsTotalValue': 4778.66, 'annualMeetings': [{'extra': False, 'eventDate': '2021-05-06'}], 'companyReports': [{'reportType': 'INTERIM', 'eventDate': '2021-08-05'}, {'reportType': 'INTERIM', 'eventDate': '2021-10-28'}, {'reportType': 'ANNUAL', 'eventDate': '2022-02-10'}], 'brokerTradeSummary': {'orderbookId': '76426', 'items': [{'netBuyVolume': 0, 'buyVolume': 778609, 'sellVolume': 778609, 'brokerCode': 'ANON'}]}}
placeOrderReply = {'status': 'SUCCESS', 'messages': [''], 'orderId': '385663370', 'requestId': '-1'}
deleteOrderReply = {'status': 'SUCCESS', 'messages': [''], 'orderId': '385663370', 'requestId': '-1'}
searchForStockReply = {'totalNumberOfHits': 2, 'hits': [{'instrumentType': 'STOCK', 'numberOfHits': 2, 'topHits': [{'currency': 'USD', 'lastPrice': 157.29, 'changePercent': -2.05, 'flagCode': 'US', 'tradable': True, 'tickerSymbol': 'TXG', 'name': '10X Genomics Inc', 'id': '996635'}, {'currency': 'CAD', 'lastPrice': 16.32, 'changePercent': 1.68, 'flagCode': 'CA', 'tradable': True, 'tickerSymbol': 'TXG', 'name': 'Torex Gold Resources Inc', 'id': '282537'}]}]}


def testGetTransactions():
    objUnderTest = AvanzaHandler(Log())
    objUnderTest.avanza = MagicMock()
    objUnderTest.avanza.get_transactions.return_value = getTransactionsReply

    retVal = objUnderTest.getTransactions()

    assert retVal is not None
    assert len(retVal) == 15

    retVal = objUnderTest.getTransactions(filterByDate='2021-11-11')
    assert retVal is not None
    assert len(retVal) == 3

def testplaceOrder():
    objUnderTest = AvanzaHandler(Log())
    objUnderTest.PRODUCTION = "true" # OK cause we mock the avanza
    objUnderTest.avanza = MagicMock()
    objUnderTest.avanza.place_order.return_value = placeOrderReply

    retVal = objUnderTest.placeOrder("AKSO.ST", "1234", "4532", TransactionType.Buy, 2.6, 2)

    assert retVal is not None

def testGenerateOrderValidDate():
    objUnderTest = AvanzaHandler(Log())

    retVal = objUnderTest.generateOrderValidDate()

    assert retVal is not None

def testGuessTickSize():
    objUnderTest = AvanzaHandler(Log())

    retData = objUnderTest.guessTickSize(getStockInfoReply)

    assert retData is not None

def testGetTickerDetails():
    objUnderTest = AvanzaHandler(Log())
    objUnderTest.avanza = MagicMock()
    objUnderTest.avanza.get_stock_info.return_value = getStockInfoReply

    retVal = objUnderTest.getTickerDetails("AKSO.ST")

    assert retVal is not None

def testTickerToId():
    objUnderTest = AvanzaHandler(Log())
    objUnderTest.avanza = MagicMock()
    objUnderTest.avanza.search_for_stock.return_value = searchForStockReply

    retVal = objUnderTest.tickerToId("TXG")

    assert retVal is not None

def testSecondsSinceDate():
    objUnderTest = AvanzaHandler(Log())

    retVal = objUnderTest.secondsSinceDate('2021-11-17T15:31:24.000+0100')

    assert retVal > 0

def testYhooTickerToAvanzaTicker():
    objUnderTest = AvanzaHandler(Log())

    tickerPart, flagCode = objUnderTest.yahooTickerToAvanzaTicker('AKSO.ST')

    assert tickerPart == "AKSO"
    assert flagCode == "SE"

def testDeleteOrder():
    objUnderTest = AvanzaHandler(Log())
    objUnderTest.avanza = MagicMock()
    objUnderTest.avanza.delete_order.return_value = deleteOrderReply

    retVal = objUnderTest.deleteOrder("1234", "347268")

    assert retVal is not None
    assert 'status' in retVal and retVal['status'] == 'SUCCESS'

if __name__ == "__main__":
    testGetTransactions()
    testplaceOrder()
    testGenerateOrderValidDate()
    testGuessTickSize()
    testGetTickerDetails()
    testTickerToId()
    testSecondsSinceDate()
    testYhooTickerToAvanzaTicker()
    testDeleteOrder()