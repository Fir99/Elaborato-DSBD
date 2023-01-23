from flask import Flask
import mysql.connector
import time, sys

api = Flask(__name__)

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

@api.route('/metriche', methods=['GET'])
def get_metriche():
    try: 
        mydb.commit()
        sql = "SELECT DISTINCT metrica from METRICHE;"
        mycursor.execute(sql)
        dati = mycursor.fetchall()
    except mysql.connector.Error as err:
        sys.stderr.write("Errore: {}\n".format(err))
        return "Query al DB fallita"
    if mycursor.rowcount == 0:
        return "Nessun dato"
    result = "Metriche disponibili: <br/>"
    for riga in dati:
        result += riga[0] + "<br/>"
    return result

@api.route('/<metrica>/<tipo>', methods = ['GET'])
def get_info(metrica, tipo):
    try: 
        mydb.commit()
        if tipo == "metadati":
            sql = "SELECT autocorrelazione, stazionarieta, stagionalita, timestamp from METRICHE where metrica = '" + metrica + "' ORDER BY timestamp DESC LIMIT 100;"
            mycursor.execute(sql)
            dati = mycursor.fetchall()
            if mycursor.rowcount == 0:
                return "Nessun dato"
            result = "Risultati per la metrica " + metrica + ":<br/>"
            for riga in dati:
                result += "Timestamp: " + str(riga[3]) + " Metrica autocorrelata per i seguenti lag: " + str(riga[0]) + " Stazionarieta': " + str(riga[1]) + " Stagionalita': " + str(riga[2]) + "<br/>"
            return result
        elif tipo == "statistiche":
            #Massimo timestamp per la metrica scelta
            subquery = "SELECT max(STAT_METRICHE.timestamp) FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "'"
            #Query per 1h
            sql = "SELECT max, min, avg, dev_std, STAT_METRICHE.timestamp FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE tempo = '1h' AND METRICHE.metrica = '" + metrica + "' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati == None:
                return "Nessun dato"
            result = "Risultati per la metrica " + metrica + " per l'ultima ora:<br/>"
            result += "Timestamp: " + str(dati[4]) + " Max: " + str(dati[0]) + " Min: " + str(dati[1]) + " Avg: " + str(dati[2]) + " Dev_std: " + str(dati[3]) + "<br/>"
            #Query per 3h
            sql = "SELECT max, min, avg, dev_std, STAT_METRICHE.timestamp FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE tempo = '3h' AND METRICHE.metrica = '" + metrica + "' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            result += "Risultati per la metrica " + metrica + " per le ultime 3 ore:<br/>"
            result += "Timestamp: " + str(dati[4]) + " Max: " + str(dati[0]) + " Min: " + str(dati[1]) + " Avg: " + str(dati[2]) + " Dev_std: " + str(dati[3]) + "<br/>"
            #Query per 12h
            sql = "SELECT max, min, avg, dev_std, STAT_METRICHE.timestamp FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE tempo = '12h' AND METRICHE.metrica = '" + metrica + "' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            result += "Risultati per la metrica " + metrica + " per le ultime 12 ore:<br/>"
            result += "Timestamp: " + str(dati[4]) + " Max: " + str(dati[0]) + " Min: " + str(dati[1]) + " Avg: " + str(dati[2]) + " Dev_std: " + str(dati[3]) + "<br/>"
            return result
        elif tipo == "predizioni":
            #Massimo timestamp per la metrica scelta
            subquery = "SELECT max(STAT_METRICHE.timestamp) FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "'"
            #Query per 1h
            sql = "SELECT max_predetto, min_predetto, avg_predetta, STAT_METRICHE.timestamp FROM (STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id) JOIN PREDIZIONI ON PREDIZIONI.metrica = STAT_METRICHE.id WHERE tempo = '1h' AND METRICHE.metrica = '" + metrica + "' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati == None:
                return "Nessun dato"
            result = "Predizioni per i prossimi 10 minuti a partire da " + str(dati[3]) + " per la metrica " + metrica + " considerando i campioni dell'ultima ora:<br/>"
            result += "Max: " + str(dati[0]) + " Min: " + str(dati[1]) + " Avg: " + str(dati[2]) + "<br/>"
            #Query per 3h
            sql = "SELECT max_predetto, min_predetto, avg_predetta, STAT_METRICHE.timestamp FROM (STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id) JOIN PREDIZIONI ON PREDIZIONI.metrica = STAT_METRICHE.id WHERE tempo = '3h' AND METRICHE.metrica = '" + metrica + "' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            result += "Predizioni per i prossimi 10 minuti a partire da " + str(dati[3]) + " per la metrica " + metrica + " considerando i campioni delle ultime 3 ore:<br/>"
            result += "Max: " + str(dati[0]) + " Min: " + str(dati[1]) + " Avg: " + str(dati[2]) + "<br/>"
            #Query per 12h
            sql = "SELECT max_predetto, min_predetto, avg_predetta, STAT_METRICHE.timestamp FROM (STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id) JOIN PREDIZIONI ON PREDIZIONI.metrica = STAT_METRICHE.id WHERE tempo = '12h' AND METRICHE.metrica = '" + metrica + "' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            result += "Predizioni per i prossimi 10 minuti a partire da " + str(dati[3]) + " per la metrica " + metrica + " considerando i campioni delle ultime 12 ore:<br/>"
            result += "Max: " + str(dati[0]) + " Min: " + str(dati[1]) + " Avg: " + str(dati[2]) + "<br/>"
            return result
        else:
            return "Tipo non valido"
    except mysql.connector.Error as err:
        sys.stderr.write("Errore: {}\n".format(err))
        return "Query al DB fallita"

if __name__ == '__main__':
    api.run(host='0.0.0.0', port=40000)
    
