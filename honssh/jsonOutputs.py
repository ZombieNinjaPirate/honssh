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

from honssh import elastic
from hpfeeds import hpfeeds
from twisted.python import log


class JsonOutputter():
    
    def setClients(self, hpLogClient, esLogClient, cfg, sensorName, sessionID):
        self.cfg = cfg
        self.sensorName = sensorName
        self.sessionID = sessionID
        
        if self.cfg.get('hpfeeds', 'enabled') == 'true':
            self.hpLog = hpfeeds.HPLogger()
            self.hpLog.setClient(hpLogClient)
            
        if self.cfg.get('elasticsearch', 'enabled') == 'true':
            self.esLog = elastic.ESLogger()
            self.esLog.setClient(esLogClient)
    
    def handleConnectionLost(self, dt):
        self.sessionMeta['endTime'] = dt
        
        if self.cfg.get('hpfeeds', 'enabled') == 'true':
            self.hpLog.handleConnectionLost(self.sessionMeta)
        if self.cfg.get('elasticsearch', 'enabled') == 'true':
            self.esLog.handleConnectionLost(self.sessionMeta)
            
    def handleLoginSucceeded(self, dt, username, password, peerIP, peerPort, honeyIP, honeyPort, version):
        authMeta = {'sensor_name': self.sensorName, 'datetime': dt, 'username': username, 'password': password, 'success': True, 'ip':peerIP}

        self.sessionMeta = { 'sensor_name': self.sensorName, 'uuid': self.sessionID, 'startTime': dt, 'channels': [] }
        self.sessionMeta['connection'] = {'peerIP': peerIP, 'peerPort': peerPort, 'honeyIP': honeyIP, 'honeyPort': honeyPort, 'version': version}
        
        if self.cfg.get('hpfeeds', 'enabled') == 'true':
            self.hpLog.handleLoginSucceeded(authMeta)
            
        if self.cfg.get('elasticsearch', 'enabled') == 'true':
            self.esLog.handleLoginSucceeded(authMeta)

    def handleLoginFailed(self, dt, username, password, endIP):
        authMeta = {'sensor_name': self.sensorName, 'datetime': dt, 'username': username, 'password': password, 'success': False, 'ip':endIP}

        if self.cfg.get('hpfeeds', 'enabled') == 'true':
            self.hpLog.handleLoginFailed(authMeta)
            
        if self.cfg.get('elasticsearch', 'enabled') == 'true':
            self.esLog.handleLoginFailed(authMeta)
            
    def handleChannelOpened(self, dt, uuid, channelName):   
        self.sessionMeta['channels'].append({'name': channelName, 'uuid': uuid, 'startTime': dt, 'commands': []})
        
    def handleChannelClosed(self, dt, uuid, ttylog=None):           
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
          
    def findChannel(self, uuid):
        for chan in self.sessionMeta['channels']:
            if chan['uuid'] == uuid:
                return chan
    