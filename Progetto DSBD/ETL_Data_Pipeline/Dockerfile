FROM python:3.9
ADD ETL_Data_Pipeline.py /
RUN pip install --upgrade pip
RUN pip install prometheus_api_client datetime statsmodels confluent_kafka flask numpy
CMD [ "python", "./ETL_Data_Pipeline.py" ]
EXPOSE 50000