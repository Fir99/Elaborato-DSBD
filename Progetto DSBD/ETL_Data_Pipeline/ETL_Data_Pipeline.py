from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame, PrometheusApiClientException
import requests, sys, json, time, threading
from datetime import timedelta, datetime
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from confluent_kafka import Producer, KafkaException
from prometheus_api_client.utils import parse_datetime
from statsmodels.tsa.stattools import adfuller, acf
from flask import Flask, request
import numpy as np

def connessione_Prometheus():
    global prom
    prom = PrometheusConnect(url="http://15.160.61.227:29090/", disable_ssl=True)

label_config = {'instance': '105', 'job': 'summary'}
metriche = ["availableMem", "connectionStatus", "cpuLoad", "cpuTemp", "diskUsage", "inodeUsage", "networkThroughput", "realUsedMem"]
durate = ["1h", "3h", "12h"]
end_time = parse_datetime("now")
broker = "kafka:9092"
topic = "prometheusdata"
conf = {'bootstrap.servers': broker}
prod = Producer(**conf)
lock = threading.Lock()

api = Flask(__name__)

@api.route('/update', methods = ['POST'])
def update_SLA_set():
    dati = request.json
    for x in dati:
        if x not in metriche:
            return str(False)
    global SLA_set
    lock.acquire()
    SLA_set = dati
    sla_file = open("SLA.txt","w")
    sla_file.write(str(dati))
    sla_file.flush()
    sla_file.close()
    lock.release()
    return str(True)

@api.route('/get_sla_set', methods = ['GET'])
def return_SLA_set():
    metriche = []
    for x in SLA_set:
        metriche.append(x)
    return json.dumps(metriche)

def read_SLA():
    global SLA_set
    sla_file = open("SLA.txt","r")
    SLA_set = eval(sla_file.read())
    sla_file.close()


def delivery_callback(err, msg):
    if err:
        sys.stderr.write('%% Message failed delivery: %s\n' % err)
    else:
        sys.stderr.write('%% Message delivered to %s [%d] @ %d\n' %
                            (msg.topic(), msg.partition(), msg.offset()))

def get_serie(nome, start):
    while True:
        try:
            metric_data = prom.get_metric_range_data(
                    metric_name = nome,
                    label_config = label_config,
                    start_time = parse_datetime(start),
                    end_time = end_time
                    )
            break
        except requests.exceptions.RequestException:
            sys.stderr.write("Errore nella connessione a Prometheus: RequestException\n")
            connessione_Prometheus()
        except PrometheusApiClientException: 
            sys.stderr.write("Errore nella comunicazione con Prometheus: PrometheusApiClientException\n")
            pass
    return metric_data

def calcola_stazionarieta(tsr):
    adft = adfuller(tsr.dropna(),autolag='AIC')
    if adft[1] > 0.05:
        for x in adft[4].values():
            if adft[0] <= x:
                return True
        return False
    else:
        return True

def calcola_autoc(tsr):
    tsr = tsr.dropna()
    tsr = tsr[["value"]]
    AC = acf(tsr)
    #Lag per cui il coefficiente di autocorrelazione e' maggiore di 0.5
    lags = "{"
    for i in range(1, len(AC)):
        if AC[i] > 0.5:
            lags += str(i) + ", "
    if len(lags) > 1:
        lags = lags[:len(lags)-2]
    lags += "}"
    return lags

def calcola_stag(tsr):
    tsr = tsr.dropna()
    tsr = tsr[["value"]]
    if tsr["value"].max() == tsr["value"].min():
        #Serie costante
        return 0     #Stagionalita' 0, autocorrelazione 1
    nobs = len(tsr)
    fft = np.abs(np.fft.rfft(tsr["value"]))
    fft_freq = np.fft.rfftfreq(nobs)
    freqs = fft_freq[2:]
    fft2 = fft[2:]
    max_freq = freqs[np.argmax(fft2)]
    periodo = int(1/max_freq) 
    return periodo

def violazioni_passate(metrica, serie):
    count = 0
    if "min" in SLA_set[metrica] and "max" in SLA_set[metrica]:
        # SLO: min <= SLI <= max
        for x in serie["value"]:
            if x < SLA_set[metrica]["min"] or x > SLA_set[metrica]["max"]:
                count += 1
    elif "min" in SLA_set[metrica]:
        # SLO: min <= SLI
        for x in serie["value"]:
            if x < SLA_set[metrica]["min"]:
                count += 1
    else:
        # SLO: SLI <= max
        for x in serie["value"]:
            if x > SLA_set[metrica]["max"]:
                count += 1
    return count

def violazione_futura(metrica, max_futuro, min_futuro):
    # SLO: min <= SLI <= max
    if "min" in SLA_set[metrica] and "max" in SLA_set[metrica]:
        if min_futuro < SLA_set[metrica]["min"] or max_futuro > SLA_set[metrica]["max"]:
            return True
        else:
            return False
    elif "min" in SLA_set[metrica]:
        # SLO: min <= SLI
        if min_futuro < SLA_set[metrica]["min"]:
            return True
        else:
            return False
    else:
        # SLO: SLI <= max
        if max_futuro > SLA_set[metrica]["max"]:
            return True
        else:
            return False

def calcola_1_3_12_ore(dati, log, metrica):
    for x in range(3): 
        #Tempo di inizio
        tempo_inizio = time.perf_counter()
        metric_data = get_serie(metrica, durate[x])
        if not metric_data:
            sys.stderr.write("Risultato vuoto da Prometheus\n")
            sys.exit()
        metric_df = MetricRangeDataFrame(metric_data)
        dati["max" + str(x)] = metric_df["value"].max()
        dati["min" + str(x)] = metric_df["value"].min()
        dati["avg" + str(x)] = metric_df["value"].mean()
        dati["std" + str(x)] = metric_df["value"].std()
        dati["range" + str(x)] = durate[x]
        predicted = False
        if metrica in SLA_set: 
            predicted = True
            #Campionamento a 5 minuti
            ts_to_predict = metric_df.resample(rule="5T").mean(numeric_only=True)
            dati["num_violazioni_passate" + str(x)] = violazioni_passate(metrica, ts_to_predict)
            periodo = calcola_stag(ts_to_predict)
            if periodo == 0:
                periodo = 2
            tsmodel = ExponentialSmoothing(ts_to_predict, trend='add', seasonal='add',seasonal_periods=periodo).fit()
            prediction = tsmodel.forecast(2)
            dati["predicted_max" + str(x)] = prediction.max()
            dati["predicted_min" + str(x)] = prediction.min()
            dati["predicted_avg" + str(x)] = prediction.mean()
            dati["violazione_futura" + str(x)] = violazione_futura(metrica, prediction.max(), prediction.min())
            if "min" in SLA_set[metrica]:
                dati["SLO_min"] = SLA_set[metrica]["min"]
            else:
                dati["SLO_min"] = None
            if "max" in SLA_set[metrica]:
                dati["SLO_max"] = SLA_set[metrica]["max"]
            else:
                dati["SLO_max"] = None
        #Tempo finale
        tempo_fine = time.perf_counter()
        #Tempo in hh:mm:ss
        durata = str(timedelta(seconds=tempo_fine-tempo_inizio))
        log.write("Timestamp: " + str(datetime.now()) + "\tMetrica: " + metrica + "\tRange: " + durate[x] + "\tDurata: " + durata + "\tPredetto: " + str(predicted) + "\n")
        log.flush()   

def invia_dati(dati):
    while True:
        try:
            prod.produce(topic, json.dumps(dati), callback=delivery_callback)
            prod.poll(0)
            break
        except BufferError:
            sys.stderr.write('Eccezione: coda locale del producer piena (%d messaggi in attesa di delivery)\n' % len(prod))
            time.sleep(1)
        except KafkaException as e:
            sys.stderr.write("Eccezione: KafkaException\n")
            if not(e.args[0].retriable()):
                break
            time.sleep(1)


def flask_program():
    #Avvio server per poter ricevere l'SLA Set
    api.run(host='0.0.0.0', port=50000)

if __name__ == '__main__':
    connessione_Prometheus()
    thread_flask = threading.Thread(target = flask_program)
    thread_flask.daemon = True
    thread_flask.start()
    dati = dict()
    log = open("log.txt","a")
    cont = 0
    read_SLA()
    while True:
        lock.acquire()
        for metrica in metriche:
            dati.clear()
            if (cont == 3360 or cont == 0):   # Ogni 7 giorni, per aggiornare i metadati delle metriche
                cont = 0
                metadati = dict()
                metadati["tipo"] = "metadati"
                metadati["timestamp"] = str(datetime.now())
                serie = get_serie(metrica, "7d")
                if not serie:
                    sys.stderr.write("Risultato vuoto da Prometheus\n")
                    sys.exit()
                serie_df = MetricRangeDataFrame(serie)  
                tsr = serie_df.resample(rule="5T").mean(numeric_only=True)
                #Stazionarieta', stagionalita', autocorrelazione
                metadati["staz"] = calcola_stazionarieta(tsr)
                metadati["stag"] = calcola_stag(tsr)
                metadati["autoc"] = calcola_autoc(tsr)
                metadati["name"] = metrica
                sys.stderr.write("Invio metadati metrica %s\n" % str(metrica))
                invia_dati(metadati)
                time.sleep(2)

            dati["name"] = metrica
            dati["timestamp"] = str(datetime.now())
            dati["tipo"] = "valori"
            calcola_1_3_12_ore(dati, log, metrica) 
            sys.stderr.write("Invio statistiche metrica %s\n" % str(metrica))
            invia_dati(dati)

        cont += 1
        lock.release()
        prod.flush()
        time.sleep(180)

    prod.flush(10)
    log.close()
 

