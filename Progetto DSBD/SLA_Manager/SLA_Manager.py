from flask import Flask, request
import mysql.connector, requests, time, sys

api = Flask(__name__)

URL_BASE = "http://etl_data_pipeline:50000/"

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

@api.route('/set', methods = ['POST'])
def set_SLA_set():
    if request.content_length == 0:
        return "Messaggio vuoto"
    try:
        dati = request.json
    except:
        return "Formato non valido"
    if len(dati) != 5:
        return "Inserire 5 metriche nel formato corretto"
    for x in dati:
        if "min" in dati[x] and "max" in dati[x]:
            if dati[x]["min"] > dati[x]["max"]:
                return "SLO non valido"
        if "min" not in dati[x] and "max" not in dati[x]:
            return "Indicare almeno il minimo o il massimo"
    #Dati nel formato corretto
    try:
        resp = requests.post(URL_BASE + "update", json = dati).text
        if resp == "True":
            return "Aggiornamento riuscito"
        else:
            return "Metriche inserite non valide"
    except requests.exceptions.ConnectionError:
        return "Errore di connessione"

@api.route('/stato', methods = ['GET'])
def get_stato():
    metriche = []
    try:
        metriche = requests.get(URL_BASE + "get_sla_set").json()
    except requests.exceptions.ConnectionError:
        return "Errore di connessione"
    try:
        result = "Stato dell'SLA<br/>"
        mydb.commit()
        for metrica in metriche:
            # Massimo timestamp presente in STAT_METRICHE per la metrica
            subquery = "SELECT max(STAT_METRICHE.timestamp) FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "'"
            # Verifica violazioni per 1h per "metrica"
            sql = "SELECT num_violazioni, SLO_min, SLO_max FROM (SLO JOIN STAT_METRICHE ON SLO.stat_metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '1h' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati == None:
                result += "Dati non ancora disponibili per la metrica " + metrica + "<br/>"
                continue
            result += "Stato della metrica " + metrica + " con SLO ["
            if dati[1] == None:
                result += ":"
            else:
                result += (str(dati[1]) + ":")
            if dati[2] == None:
                result += "]<br/>"
            else:
                result += (str(dati[2]) + "]<br/>")
            if dati[0] > 0:
                result += "---> Ultima ora: violated<br/>"
            else:
                result += "---> Ultima ora: not violated<br/>"
            # Verifica violazioni per 3h per "metrica"
            sql2 = "SELECT num_violazioni FROM (SLO JOIN STAT_METRICHE ON SLO.stat_metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '3h' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql2)
            dati = mycursor.fetchone()
            if dati[0] > 0:
                result += "---> Ultime 3 ore: violated<br/>"
            else:
                result += "---> Ultime 3 ore: not violated<br/>"
            # Verifica violazioni per 12h per "metrica"
            sql3 = "SELECT num_violazioni FROM (SLO JOIN STAT_METRICHE ON SLO.stat_metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '12h' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql3)
            dati = mycursor.fetchone()
            if dati[0] > 0:
                result += "---> Ultime 12 ore: violated<br/>"
            else:
                result += "---> Ultime 12 ore: not violated<br/>"
        return result
    except mysql.connector.Error as err:
        sys.stderr.write("Errore: {}\n".format(err))
        return "Errore di connessione al DB"

@api.route('/violazioni_passate', methods = ['GET'])
def violazioni_passate():
    metriche = []
    try:
        metriche = requests.get(URL_BASE + "get_sla_set").json()
    except requests.exceptions.ConnectionError:
        return "Errore di connessione"
    try:
        result = "Numero di violazioni per le metriche dell'SLA<br/>"
        mydb.commit()
        for metrica in metriche:
            # Massimo timestamp presente in STAT_METRICHE per la metrica
            subquery = "SELECT max(STAT_METRICHE.timestamp) FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "'"
            # Verifica violazioni per 1h per "metrica"
            sql = "SELECT num_violazioni FROM (SLO JOIN STAT_METRICHE ON SLO.stat_metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '1h' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati == None:
                result += "Dati non ancora disponibili per la metrica " + metrica + "<br/>"
                continue
            result += "Numero di violazioni della metrica " + metrica + "<br/>"
            result += "---> Per l'ultima ora: " + str(dati[0]) + "<br/>"
            # Verifica violazioni per 3h per "metrica"
            sql2 = "SELECT num_violazioni FROM (SLO JOIN STAT_METRICHE ON SLO.stat_metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '3h' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql2)
            dati = mycursor.fetchone()
            result += "---> Per le ultime 3 ore: " + str(dati[0]) + "<br/>"
            # Verifica violazioni per 12h per "metrica"
            sql3 = "SELECT num_violazioni FROM (SLO JOIN STAT_METRICHE ON SLO.stat_metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '12h' AND STAT_METRICHE.timestamp = (" + subquery + ");"
            mycursor.execute(sql3)
            dati = mycursor.fetchone()
            result += "---> Per le ultime 12 ore: " + str(dati[0]) + "<br/>"
        return result
    except mysql.connector.Error as err:
        sys.stderr.write("Errore: {}\n".format(err))
        return "Errore di connessione al DB"

@api.route('/violazioni_future', methods = ['GET'])
def violazioni_future():
    metriche = []
    try:
        metriche = requests.get(URL_BASE + "get_sla_set").json()
    except requests.exceptions.ConnectionError:
        return "Errore di connessione"
    try:
        result = "Possibili violazioni future per le metriche dell'SLA<br/>"
        mydb.commit()
        for metrica in metriche:
            # Massimo timestamp presente in STAT_METRICHE per la metrica
            subquery = "SELECT max(STAT_METRICHE.timestamp) FROM STAT_METRICHE JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "'"
            # Verifica violazioni future per 1h per "metrica"
            sql = "SELECT violazione FROM (PREDIZIONI JOIN STAT_METRICHE ON PREDIZIONI.metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '1h' AND STAT_METRICHE.timestamp = (" + subquery + ");" 
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati == None:
                result += "Dati non ancora disponibili per la metrica " + metrica + "<br/>"
                continue
            result += "Violazioni nei prossimi 10 minuti per la metrica " + metrica + "<br/>"
            if dati[0] == True:
                result += "---> Considerando i campioni dell'ultima ora: violazione presente<br/>"
            else:
                result += "---> Considerando i campioni dell'ultima ora: violazione non presente<br/>"
            # Verifica violazioni future per 3h per "metrica"
            sql = "SELECT violazione FROM (PREDIZIONI JOIN STAT_METRICHE ON PREDIZIONI.metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '3h' AND STAT_METRICHE.timestamp = (" + subquery + ");" 
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati[0] == True:
                result += "---> Considerando i campioni delle ultime 3 ore: violazione presente<br/>"
            else:
                result += "---> Considerando i campioni delle ultime 3 ore: violazione non presente<br/>"
            # Verifica violazioni future per 12h per "metrica"
            sql = "SELECT violazione FROM (PREDIZIONI JOIN STAT_METRICHE ON PREDIZIONI.metrica = STAT_METRICHE.id) JOIN METRICHE ON STAT_METRICHE.metrica = METRICHE.id WHERE METRICHE.metrica = '" + metrica + "' AND tempo = '12h' AND STAT_METRICHE.timestamp = (" + subquery + ");" 
            mycursor.execute(sql)
            dati = mycursor.fetchone()
            if dati[0] == True:
                result += "---> Considerando i campioni delle ultime 12 ore: violazione presente<br/>"
            else:
                result += "---> Considerando i campioni delle ultime 12 ore: violazione non presente<br/>"
        return result
    except mysql.connector.Error as err:
        sys.stderr.write("Errore: {}\n".format(err))
        return "Errore di connessione al DB"

if __name__ == '__main__':
    api.run(host='0.0.0.0', port=45000)
    
