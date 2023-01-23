create database monitoring;
use monitoring;

CREATE TABLE METRICHE
(
	id integer PRIMARY KEY AUTO_INCREMENT,
	metrica varchar(255),
	autocorrelazione varchar(255),
	stazionarieta bool,
	stagionalita integer,
	timestamp datetime
) Engine = 'InnoDB';

CREATE TABLE STAT_METRICHE
(
	id integer PRIMARY KEY AUTO_INCREMENT,
	metrica integer,
	max float,
	min float,
	avg float,
	dev_std float,
	tempo varchar(255),
	timestamp datetime,
	INDEX idx_metrica(metrica),
	FOREIGN KEY (metrica) REFERENCES METRICHE(id)
) Engine = 'InnoDB';

CREATE TABLE SLO
(
	id integer PRIMARY KEY AUTO_INCREMENT,
	num_violazioni integer,
	SLO_min float,
	SLO_max float,
	stat_metrica integer,
	INDEX idx_stat_metrica(stat_metrica),
	FOREIGN KEY (stat_metrica) REFERENCES STAT_METRICHE(id)
) Engine = 'InnoDB';

CREATE TABLE PREDIZIONI
(
	id integer PRIMARY KEY AUTO_INCREMENT,
	metrica integer,
	max_predetto float,
	min_predetto float,
	avg_predetta float,
	violazione bool,
	INDEX idx_metrica(metrica),
	FOREIGN KEY (metrica) REFERENCES STAT_METRICHE(id)
) Engine = 'InnoDB';