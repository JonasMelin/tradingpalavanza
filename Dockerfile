FROM python:3.7-slim

RUN pip install requests pytz avanza-api Flask
RUN pip list

ADD AvanzaHandler.py MainBroker.py Logger.py RestServer.py /

ENTRYPOINT ["python3","/RestServer.py"]




