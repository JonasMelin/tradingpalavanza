FROM python:3.7-slim

RUN pip install requests==2.27.1 pytz==2021.3 avanza-api==6.0.0 Flask==2.0.3
RUN pip list

ADD AvanzaHandler.py MainBroker.py Logger.py RestServer.py /

ENTRYPOINT ["python3","/RestServer.py"]

Package            Version
------------------ ---------
avanza-api         6.0.0
certifi            2022.12.7
charset-normalizer 2.0.12
click              8.1.3
Flask              2.0.3
idna               3.4
importlib-metadata 5.2.0
itsdangerous       2.1.2
Jinja2             3.1.2
MarkupSafe         2.1.1
pip                21.2.4
pyotp              2.8.0
pytz               2021.3
requests           2.27.1
setuptools         57.5.0
typing_extensions  4.4.0
urllib3            1.26.13
websockets         10.4
Werkzeug           2.2.2
wheel              0.37.1
zipp               3.11.0



