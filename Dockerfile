FROM python:3.7-slim

RUN pip install requests==2.27.1 pytz==2021.3 avanza-api==4.0.1 Flask==2.0.3
RUN pip list

ADD AvanzaHandler.py MainBroker.py Logger.py RestServer.py /

ENTRYPOINT ["python3","/RestServer.py"]

#tckage            Version
#------------------ ---------
#avanza-api         3.0.1
#certifi            2021.10.8
#charset-normalizer 2.0.12
#click              8.0.4
#Flask              2.0.3
#idna               3.3
#importlib-metadata 4.11.1
#itsdangerous       2.1.0
#Jinja2             3.0.3
#MarkupSafe         2.1.0
#pip                21.1.3
#pyotp              2.6.0
#pytz               2021.3
#requests           2.27.1
#setuptools         57.0.0
#typing-extensions  4.1.1
#urllib3            1.26.8
#websockets         10.1
#Werkzeug           2.0.3
#wheel              0.36.2
#zipp               3.7.0


