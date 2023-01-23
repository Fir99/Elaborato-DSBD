FROM python:3.9
ADD Data_Storage.py /
RUN pip install --upgrade pip
RUN pip install confluent_kafka mysql.connector
CMD [ "python", "./Data_Storage.py" ]