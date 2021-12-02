FROM python:3.7-slim

RUN pip install requests==2.25.1
RUN pip install pytz==2020.5
RUN pip install avanza-api==2.8.0
RUN pip install Flask==1.1.1
RUN pip list

ADD AvanzaHandler.py MainBroker.py Logger.py RestServer.py /

ENTRYPOINT ["python3","/RestServer.py"]




