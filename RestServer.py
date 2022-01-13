import sys

from flask import Flask, request, Response
import threading
import MainBroker
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
mainBroker = MainBroker.MainBroker()

@app.route("/tradingpalavanza/getfunds", methods=['GET'])
def getFunds():

    return {"funds": mainBroker.getCurrentFunds()}

@app.route("/tradingpalavanza/getyield", methods=['GET'])
def getYield():
    date = request.args.get("date")

    return {"yields": mainBroker.getYieldByDate(date)}

@app.route("/tradingpalavanza/gettax", methods=['GET'])
def getTax():
    date = request.args.get("date")

    return {"taxes": mainBroker.getTaxByDate(date)}

@app.route("/tradingpalavanza/blockpurchases", methods=['GET'])
def blockPurchases():
    mainBroker.doBlockPurchases()
    return {}

@app.route("/tradingpalavanza/unblockpurchases", methods=['GET'])
def unblockPurchases():
    mainBroker.doUnblockPurchases()
    return {}

@app.route("/tradingpalavanza/killswitch", methods=['GET'])
def killswitch():
    mainBroker.doTerminate()

    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()

    sys.exit()


if __name__ == "__main__":

    threading.Thread(target=mainBroker.run).start()
    app.run(host='0.0.0.0', port=5002)
