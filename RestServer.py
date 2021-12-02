
from flask import Flask, request, Response
import threading
import MainBroker

app = Flask(__name__)
mainBroker = MainBroker.MainBroker()

@app.route("/tradingpalavanza/getfunds", methods=['GET'])
def getFunds():

    return {"funds": mainBroker.getCurrentFunds()}

@app.route("/tradingpalavanza/getyield", methods=['GET'])
def getYieldByDate():
    date = request.args.get("date")

    if date is None:
        return Response("Missing param date", status=400)

    return {"yields": mainBroker.getYieldByDate(date)}


@app.route("/tradingpalavanza/gettax", methods=['GET'])
def getTaxByDate():
    date = request.args.get("date")

    if date is None:
        return Response("Missing param date", status=400)

    return {"taxes": mainBroker.getTaxByDate(date)}

if __name__ == "__main__":

    threading.Thread(target=mainBroker.run).start()
    app.run(host='0.0.0.0', port=5002)