# Copyright (c) 2013 Thomas Nicholson <tnnich@googlemail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The names of the author(s) may not be used to endorse or promote
#    products derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHORS ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from twisted.python import log
from twisted.internet import threads

import pyes
import json

class ESLogger():
    auth_mapping = {
        "password": {
            "type": "string",
            "index": "not_analyzed"
        },
        "sensor": {
            "type": "string",
            "index": "not_analyzed"
        },
        "success": {
            "type": "boolean"
        },
        "timestamp": {
            "type": "date"
        },
        "username": {
            "type": "string",
            "index": "not_analyzed"
        },
        "ip": {
            "type": "ip"
        }
    }
    #TODO: work this one out...
    session_mapping = {
        "username": {
            "type": "string",
            "index": "not_analyzed"
        }
    }
    
    def start(self, cfg):
        log.msg('[ELASTIC] - elastic DBLogger start')
        server	= cfg.get('elasticsearch', 'server')
        port	= cfg.get('elasticsearch', 'port')
        es = pyes.ES(server + ':' + port)
        es.indices.create_index_if_missing('honssh')
        es.indices.put_mapping('auth', {'properties': self.auth_mapping}, ['honssh'])
        es.indices.put_mapping('session', {'properties': self.session_mapping}, ['honssh'])
        return es
    
    def setClient(self, esClient, cfg, sensor):
        self.sensor_name = sensor
        self.client = esClient

    def createSession(self, dt, session, peerIP, peerPort, honeyIP, honeyPort):
        self.sessionMeta = { 'sensor_name': self.sensor_name, 'uuid': session, 'startTime': dt, 'channels': [] }
        self.sessionMeta['connection'] = {'peerIP': peerIP, 'peerPort': peerPort, 'honeyIP': honeyIP, 'honeyPort': honeyPort, 'version': None}
        return session
    
    def handleConnectionLost(self, dt):
        log.msg('[ELASTIC] - publishing metadata to es')
        meta = self.sessionMeta
        meta['endTime'] = dt
        toSend = json.dumps(meta)
        log.msg("[ELASTIC] - sessionMeta: " + toSend)
        
        #threads.deferToThread(self.client.index, toSend, 'honssh', 'session')

    def handleLoginFailed(self, dt, username, password, ip):
        authMeta = {'sensor_name': self.sensor_name, 'datetime': dt,'username': username, 'password': password, 'success': False, 'ip':ip}
        toSend = json.dumps(authMeta)
        log.msg('[ELASTIC] - authMeta: ' + toSend)
        threads.deferToThread(self.client.index, toSend, 'honssh', 'auth')
        
    def handleLoginSucceeded(self, dt, username, password, ip):
        authMeta = {'sensor_name': self.sensor_name, 'datetime': dt,'username': username, 'password': password, 'success': True, 'ip':ip}
        toSend = json.dumps(authMeta)
        log.msg('[ELASTIC] - authMeta: ' + toSend)
        threads.deferToThread(self.client.index, toSend, 'honssh', 'auth')
        
    def channelOpened(self, dt, uuid, channelName):
        self.sessionMeta['channels'].append({'name': channelName, 'uuid': uuid, 'startTime': dt, 'commands': []})
        
    def channelClosed(self, dt, uuid, ttylog=None):
        chan = self.findChannel(uuid)
        chan['endTime'] = dt
        if ttylog != None: 
            fp = open(ttylog, 'rb')
            ttydata = fp.read()
            fp.close()
            chan['ttylog'] = ttydata.encode('hex')
                
    def handleCommand(self, dt, uuid, command):
        chan = self.findChannel(uuid)
        chan['commands'].append([dt, command])

    def handleClientVersion(self, version):
        self.sessionMeta['connection']['version'] = version
            
    def findChannel(self, uuid):
        for chan in self.sessionMeta['channels']:
            if chan['uuid'] == uuid:
                return chan