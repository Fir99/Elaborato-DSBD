from confluent_kafka import Consumer, KafkaException
import json, mysql.connector, time, sys

while True:
    try:
        mydb = mysql.connector.connect(
          host="db",
          user="user",
          password="pass",
          port=3306,
          database="monitoring"
        )
        mycursor = mydb.cursor()
        break
    except mysql.connector.Error as err:
        sys.stderr.write("Errore: {}\n".format(err))
        sys.stderr.write("Ritento connessione\n")
        time.sleep(5)


c = Consumer({
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'group1',
    'auto.offset.reset': 'earliest' 
})
while True:
    try:
        c.subscribe(['prometheusdata'])
        break
    except KafkaException as e:
        sys.stderr.write("Errore nella comunicazione con Kafka\n")
        if not(e.args[0].retriable()):
            exit(1)
        time.sleep(1)

while True:
    msg = c.poll(1.0)

    if msg is None:
        sys.stderr.write("In attesa di messaggi\n")
        continue
    if msg.error():
        sys.stderr.write("Consumer error: {}\n".format(msg.error()))
        continue
    dati = dict()
    dati = json.loads(msg.value())
    sys.stderr.write("Messaggio ricevuto per la metrica %s dalla partizione %s\n" %(str(dati["name"]), str(msg.partition()) ))
    try:
        if dati["tipo"] == "metadati":
            sql = "INSERT INTO METRICHE (metrica, autocorrelazione, stazionarieta, stagionalita, timestamp) VALUES (%s,%s,%s,%s,%s);"
            val = (dati["name"], dati["autoc"], dati["staz"], dati["stag"], dati["timestamp"])
            mycursor.execute(sql, val)
            mydb.commit()
        elif dati["tipo"] == "valori":
            #Massimo timestamp presente in METRICHE per la metrica da salvare
            subquery = "SELECT max(timestamp) FROM METRICHE WHERE metrica = '" + dati["name"] + "'"
            #Id della riga piu' recente relativa a quella metrica
            sql = "SELECT id FROM METRICHE WHERE metrica = '" + dati["name"] + "' AND timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            riga = mycursor.fetchone()
            if riga == None:
                continue
            id = riga[0]
            for var in range(3):
                sql2 = "INSERT INTO STAT_METRICHE (metrica, max, min, avg, dev_std, tempo, timestamp) VALUES (%s,%s,%s,%s,%s,%s,%s);"
                val2 = (id, dati["max" + str(var)], dati["min" + str(var)], dati["avg" + str(var)], dati["std" + str(var)], dati["range" + str(var)], dati["timestamp"])
                mycursor.execute(sql2, val2)
                if ("predicted_max" + str(var)) in dati:
                    id_stat_metriche = mycursor.lastrowid
                    sql3 = "INSERT INTO PREDIZIONI (metrica, max_predetto, min_predetto, avg_predetta, violazione) VALUES (%s,%s,%s,%s,%s);"
                    val3 = (id_stat_metriche, dati["predicted_max" + str(var)], dati["predicted_min" + str(var)], dati["predicted_avg" + str(var)], dati["violazione_futura" + str(var)])
                    mycursor.execute(sql3, val3)
                    sql4 = "INSERT INTO SLO (num_violazioni, SLO_min, SLO_max, stat_metrica) VALUES (%s,%s,%s,%s);"
                    val4 = (dati["num_violazioni_passate" + str(var)], dati["SLO_min"], dati["SLO_max"], id_stat_metriche)
                    mycursor.execute(sql4, val4)
            mydb.commit()
    except mysql.connector.Error as error:
        sys.stderr.write("Failed to update record to database. Rollback: {}\n".format(error))
        mydb.rollback()


if mydb.is_connected():
    mydb.close()
    sys.stderr.write("Connection is closed\n")
c.close()