FROM python:3.9
ADD SLA_Manager.py /
RUN pip install --upgrade pip
RUN pip install flask mysql.connector requests
CMD [ "python", "./SLA_Manager.py" ]
EXPOSE 45000