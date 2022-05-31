import requests
import urllib.parse
import json
import base64
import sys
import os
import configparser
import logging
import time
import datetime as dt
import smtplib
import codecs
import email.utils
from email.message import EmailMessage
import locale
import pandas as pd
import socks
import socket
import re

locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')

TOKEN_SERVICE_URL = "TOKEN_SERVICE_URL"
SERVICE_URL = "SERVICE_URL"
SERVICE_URL_CLOUDAGENT = "SERVICE_URL_CLOUDAGENT"
SERVICE_URL_CLOUDAGENT_ALL = "SERVICE_URL_CLOUDAGENT_ALL"
DEFAULT = "DEFAULT"
HOST_URL = "HOST_URL"
PAAS_HOST = "PAAS_HOST"
CLIENT_ID = "CLIENT_ID"
ClIENT_SECRET = "CLIENT_SECRET"
RETRY_COUNT = "RETRY_COUNT"
SENDERNAME = "SENDERNAME"
SENDER = "SENDER"
RECIPIENT = "RECIPIENT"
HOST = "HOST"
PORT = "PORT"
API_INTERVAL_SEC = 1
aliveStatus = "<b>X</b>"
deadStatus = "<b>Y</b>"

def usage():
    print("Usage: python3 main.py <logfile Dir> <logfile> <config file>")

class MessageService():
    def __init__(self,retry_count):
        self.retry_count = retry_count
    
    def _request(self, method, url, headers, data):
        error = ""
        for i in range(self.retry_count + 1):
            try:
                response = requests.request(method, url, headers=headers, data=data)
                return response
            except Exception as e:
                error = e
                time.sleep(API_INTERVAL_SEC)
        logger.error("IDCS Error is , %s ." %(error))
        exit(1)
    
    def initAccessToken(self, hosturl, url, clientid, clientsecret, paas_host):
        self.hosturl = hosturl
        authzHdrVal = 'Basic ' + \
            base64.b64encode(
                (clientid + ":" + clientsecret).encode()).decode("utf8")

        payload = 'grant_type=client_credentials&scope='+ paas_host +'/serviceapi/'
        headers = {
            'Authorization': authzHdrVal,
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
        response = self._request("POST", self.hosturl + url, headers=headers, data=payload)
        self.accesstoken = json.loads(response.text)["access_token"]
    
    def getHostMetric(self, paas_url, url, entityName):
        today = dt.datetime.utcnow()
        start = today + dt.timedelta(hours=0) + dt.timedelta(minutes=-10)
        end = today + dt.timedelta(hours=0)

        headers = {
            'Authorization': 'Bearer ' + self.accesstoken,
            'Content-Type': 'application/json'
        }
        params = {
            "entityType": "HostLinux",
            "entityName": entityName,
            "startTime": (str(start.isoformat(timespec='milliseconds'))+ "Z").replace('+00:00', 'Z'),
            "endTime": (str(end.isoformat(timespec='milliseconds'))+ "Z").replace('+00:00', 'Z'),
            "metricGroup": "CPU",
            "metric": "CPUUtilization",
            "limit": 1
        }
        
        response = requests.get(paas_url + url + "?%s" % (urllib.parse.urlencode(params)), headers=headers,timeout=10)
        data = json.loads(response.text)
        
        logger.info("dataPoint : %s.",data["dataPoints"])
        logger.info("dataPoint len: %s.",len(data["dataPoints"]))
        return len(data["dataPoints"])

    def getCloudAgentMetric(self, paas_url, agentall_url, agentid_url, hostname):
        headers = {
            'Authorization': 'Bearer ' + self.accesstoken,
            'Content-Type': 'application/json'
        }
        response_agent = requests.get(paas_url + agentall_url, headers=headers,timeout=5)
        df = pd.json_normalize(response_agent.json())
        
        agentId = df[df["agentName"].str.startswith(hostname)]['agentId'].astype(str).to_list()[0]
        response = requests.get(paas_url + agentid_url + "/" + agentId, headers=headers,timeout=5)
        data = response.json()
        return data["availabilityStatus"]

    def getWeblogicSeverMetric(self, paas_url, url, entityName):
        today = dt.datetime.utcnow()
        start = today + dt.timedelta(days=0) + dt.timedelta(minutes=-10)
        end = today + dt.timedelta(days=0)

        headers = {
            'Authorization': 'Bearer ' + self.accesstoken,
            'Content-Type': 'application/json'
        }
        params = {
            "entityType": "WebLogicServer",
            "entityName": entityName,
            "startTime": (str(start.isoformat(timespec='milliseconds'))+ "Z").replace('+00:00', 'Z'),
            "endTime": (str(end.isoformat(timespec='milliseconds'))+ "Z").replace('+00:00', 'Z'),
            "metricGroup": "CPU",
            "metric": "CPUUtilization",
            "limit": 1
        }
        
        response = requests.get(paas_url + url + "?%s" % (urllib.parse.urlencode(params)), headers=headers,timeout=10)
        data = json.loads(response.text)
        
        logger.info("dataPoint : %s.",data["dataPoints"])
        logger.info("dataPoint len: %s.",len(data["dataPoints"]))
        return len(data["dataPoints"])

    def getDatabaseMetric(self, paas_url, url, entityName):
        today = dt.datetime.utcnow()
        start = today + dt.timedelta(days=0) + dt.timedelta(minutes=-10)
        end = today + dt.timedelta(days=0)

        headers = {
            'Authorization': 'Bearer ' + self.accesstoken,
            'Content-Type': 'application/json'
        }
        params = {
            "entityType": "OracleDatabase",
            "entityName": entityName,
            "startTime": (str(start.isoformat(timespec='milliseconds'))+ "Z").replace('+00:00', 'Z'),
            "endTime": (str(end.isoformat(timespec='milliseconds'))+ "Z").replace('+00:00', 'Z'),
            "metricGroup": "CPU",
            "metric": "CPUUtilization",
            "limit": 1
        }
        
        response = requests.get(paas_url + url + "?%s" % (urllib.parse.urlencode(params)), headers=headers,timeout=10)
        data = json.loads(response.text)
        
        logger.info("dataPoint : %s.",data["dataPoints"])
        logger.info("dataPoint len: %s.",len(data["dataPoints"]))
        return len(data["dataPoints"])


    def createSubject(self):
        week = ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')
        today = dt.datetime.now()
        SUBJECT = dt.datetime.now().strftime('%Y/%m/%d') + '(' + week[today.weekday()]+ ') ' + '稼働確認'
        return SUBJECT
    
    def sendMessage(self, SUBJECT, SENDERNAME, SENDER, RECIPIENT, BODY_HTML, HOST, PORT):
        msg = EmailMessage()
        msg['Subject'] = SUBJECT
        msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
        msg['To'] = RECIPIENT
        msg.set_content(BODY_HTML, subtype='html')

        try:
            #With Proxy
            #socks.setdefaultproxy(socks.HTTP, 'proxy-name.com', 80)
            #socks.wrapmodule(smtplib)
            server = smtplib.SMTP(HOST, PORT)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.sendmail(SENDER, RECIPIENT, msg.as_string())
            server.close()

        except Exception as e:
            error = e
            logger.error("SMTP Processing Error is %s." %(error))
            exit(1)
        else:
            logger.info("Email is Submitted.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage()
        exit(1)
    
    formatter = '[%(asctime)s] - %(levelname)s - [Notify]%(message)s'
    time_formatter = '%Y/%m/%d:%H:%M:%S'
    logging.basicConfig(level=logging.INFO, format = formatter, datefmt = time_formatter, filename='log/sample.log')
    logger = logging.getLogger(__name__)

    config_ini = configparser.ConfigParser()
    config_ini.read("./config/config.ini")
    config_key = ["DEFAULT"]    
    key = ["PAAS_HOST","CLIENT_ID","CLIENT_SECRET"]

    lack_key = []
    primary_lack_key = []
    secondary_lack_key = []

    primary_config = config_ini[DEFAULT]
    
    if RETRY_COUNT in config_ini[DEFAULT]:
        retry_count = int(config_ini["DEFAULT"]["RETRY_COUNT"])
        logger.info("Config Read.")
    else:
        logger.warn("Retry_count=2.")
        retry_count = 2
    
    configWeblogic = open("./config/configWeblogic.json", "r")
    jsonConfig = json.load(configWeblogic)
    
    MessageService = MessageService(retry_count)
    
    logger.info("Access Token Initiated")
    MessageService.initAccessToken(
        primary_config[HOST_URL], 
        TOKEN_SERVICE_URL, 
        primary_config[CLIENT_ID], 
        primary_config[ClIENT_SECRET],
        primary_config[PAAS_HOST]
    )

    hostnameCloudAgentList = eval(config.get("LIST", "hostnameCloudAgentList"))
    hostnameHostList = eval(config.get("LIST", "hostnameHostList"))
    hostnameWeblogicList = eval(config.get("LIST", "hostnameWeblogicList"))
    hostnameDatabaseList = eval(config.get("LIST", "hostnameDatabaseList"))

    #Call Host Metric API
    logger.info("Host Metric API")
    checkedHostDict = {}
    for v in hostnameHostList:
        logger.info("metricHost: %s is processed.",v)
        checkedHostDict["metricHost_"+v] = aliveStatus \
        if MessageService.getHostMetric( \
            primary_config[PAAS_HOST],\
            SERVICE_URL,\
            v + ".oracle.com" \
        ) == 1 else deadStatus

    #Call CloudAgent Metric API
    logger.info("CloudAgent Metric")
    checkedCloudAgentDict = {}
    for v in hostnameCloudAgentList:
        logger.info("metricCloudAgent: %s is processed.",v)
        checkedCloudAgentDict["metricCloudAgent_" + v] = aliveStatus \
        if MessageService.getCloudAgentMetric( \
            primary_config[PAAS_HOST],\
            SERVICE_URL_CLOUDAGENT_ALL, \
            SERVICE_URL_CLOUDAGENT,\
            v \
        ) == "UP" else deadStatus
    
    #Call WLS Metric API
    logger.info("WLS Metric API")
    checkedWlsDict = {}
    for v in hostnameWeblogicList:
        logger.info("metricWls: %s is processed.",v)
        print(jsonConfig["mgd"][v])
        checkedWlsDict["metricWlsMgd_" + v] = aliveStatus \
        if MessageService.getWeblogicSeverMetric( \
            primary_config[PAAS_HOST],\
            SERVICE_URL,\
            jsonConfig["adm"][v] \
        ) == 1 else deadStatus
    
    #Call Database Metric API
    logger.info("Database Metric API")
    checkedDatabaseDict = {}
    for v in hostnameDatabaseList:
        logger.info("metricDatabase: %s is processed.",v)
        checkedDatabaseDict["metricDatabase_" + v] = aliveStatus \
        if MessageService.getDatabaseMetric( \
            primary_config[PAAS_HOST],\
            SERVICE_URL,\
            jsonConfig["db"][v] \
        ) == 1 else deadStatus

    #Summary Count
    #p = re.compile(aliveStatus)
    checkedSummaryDict = {}
    checkedSummaryDict["allHostMetric"] = aliveStatus if sum(1 for i in list(checkedHostDict.values()) if i.__eq__(aliveStatus)) == len(checkedHostDict) else deadStatus
    checkedSummaryDict["allCloudAgentMetric"] = aliveStatus if sum(1 for i in list(checkedCloudAgentDict.values()) if i.__eq__(aliveStatus)) == len(checkedCloudAgentDict) else deadStatus
    checkedSummaryDict["allWlsMetric"] = aliveStatus if sum(1 for i in list(checkedWlsDict.values()) if i.__eq__(aliveStatus)) == len(checkedWlsDict) else deadStatus
    checkedSummaryDict["allDatabaseMetric"] = aliveStatus if sum(1 for i in list(checkedDatabaseDict.values()) if i.__eq__(aliveStatus)) == len(checkedDatabaseDict) else deadStatus

    #Python to HTML
    print(checkedCloudAgentDict)
    dictMerged = {**checkedHostDict, **checkedCloudAgentDict, \
     **checkedWlsDict, **checkedDatabaseDict, \
     **checkedSummaryDict}
    index = codecs.open("./contents/index.html",encoding="utf-8").read().format(**dictMerged)
    
    MessageService.sendMessage(
        MessageService.createSubject(), primary_config[SENDERNAME], \
        primary_config[SENDER],primary_config[RECIPIENT],index, \
        primary_config[HOST],primary_config[PORT])