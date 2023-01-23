FROM python:3.9
ADD Data_Retrieval.py /
RUN pip install --upgrade pip
RUN pip install flask mysql.connector
CMD [ "python", "./Data_Retrieval.py" ]
EXPOSE 40000