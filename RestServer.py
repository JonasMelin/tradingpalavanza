
from flask import Flask, request
import threading
import MainBroker

app = Flask(__name__)
mainBroker = MainBroker.MainBroker()

@app.route("/tradingpalavanza/getfunds", methods=['GET'])
def getFunds():

    funds = mainBroker.getCurrentFunds()
    return {"funds": funds}

if __name__ == "__main__":

    threading.Thread(target=mainBroker.run).start()
    app.run(host='0.0.0.0', port=5002)