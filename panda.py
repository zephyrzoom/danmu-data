#!/usr/bin/env python3
#author=707
import urllib.request
import socket
import json
import time
import threading
import kmp


CHATINFOURL = 'http://www.panda.tv/ajax_chatinfo?roomid='
DELIMITER = b'}}'
KMP_TABLE = kmp.kmpTb(DELIMITER)
IGNORE_LEN = 16
FIRST_REQ = b'\x00\x06\x00\x02'
FIRST_RPS = b'\x00\x06\x00\x06'
KEEPALIVE = b'\x00\x06\x00\x00'
RECVMSG = b'\x00\x06\x00\x03'
DANMU_TYPE = '1'
BAMBOO_TYPE = '206'
AUDIENCE_TYPE = '207'
INIT_PROPERTIES = 'init.properties'
MANAGER = '60'
SP_MANAGER = '120'
HOSTER = '90'
DANMU = 'danmu.json'
danmu = []

def initDanmu():
    with open(DANMU, 'r') as f:
        global danmu
        danmu = json.loads(f.read())

def loadInit():
    with open(INIT_PROPERTIES, 'r') as f:
        init = f.read()
        init = init.split('\n')
        roomid = init[0].split(':')[1].split(' ')
        return roomid


def getChatInfo(roomid):
    with urllib.request.urlopen(CHATINFOURL + roomid) as f:
        data = f.read().decode('utf-8')
        chatInfo = json.loads(data)
        chatAddr = chatInfo['data']['chat_addr_list'][0]
        socketIP = chatAddr.split(':')[0]
        socketPort = int(chatAddr.split(':')[1])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((socketIP,socketPort))
        rid      = str(chatInfo['data']['rid']).encode('utf-8')
        appid    = str(chatInfo['data']['appid']).encode('utf-8')
        authtype = str(chatInfo['data']['authtype']).encode('utf-8')
        sign     = str(chatInfo['data']['sign']).encode('utf-8')
        ts       = str(chatInfo['data']['ts']).encode('utf-8')
        msg  = b'u:' + rid + b'@' + appid + b'\nk:1\nt:300\nts:' + ts + b'\nsign:' + sign + b'\nauthtype:' + authtype
        msgLen = len(msg)
        sendMsg = FIRST_REQ + int.to_bytes(msgLen, 2, 'big') + msg
        s.sendall(sendMsg)
        recvMsg = s.recv(4)
        if recvMsg == FIRST_RPS:
            print('成功连接弹幕服务器')
            recvLen = int.from_bytes(s.recv(2), 'big')
        #s.send(b'\x00\x06\x00\x00')
        #print(s.recv(4))
        def keepalive():
            while True:
                #print('================keepalive=================')
                s.send(KEEPALIVE)
                time.sleep(300)
        threading.Thread(target=keepalive).start()

        while True:
            recvMsg = s.recv(4)
            if recvMsg == RECVMSG:
                recvLen = int.from_bytes(s.recv(2), 'big')
                recvMsg = s.recv(recvLen)   #ack:0
                #print(recvMsg)
                recvLen = int.from_bytes(s.recv(4), 'big')
                s.recv(IGNORE_LEN)
                recvLen -= IGNORE_LEN
                recvMsg = s.recv(recvLen)   #chat msg
                #print(recvMsg)
                try:
                    analyseMsg(recvMsg, roomid)
                except Exception as e:
                    pass



def analyseMsg(recvMsg, roomid):
    position = kmp.kmp(recvMsg, DELIMITER, KMP_TABLE)
    if position == len(recvMsg) - len(DELIMITER):
        formatMsg(recvMsg, roomid)
    else:
        preMsg = recvMsg[:position + len(DELIMITER)]
        formatMsg(preMsg, roomid)
        # analyse last msg
        analyseMsg(recvMsg[position + len(DELIMITER) + IGNORE_LEN:], roomid)

# pass one audience alert
is_second_audience = False
def formatMsg(recvMsg, roomid):
    try:
        jsonMsg = eval(recvMsg)
        content = jsonMsg['data']['content']
        global danmu
        if jsonMsg['type'] == DANMU_TYPE:
            identity = jsonMsg['data']['from']['identity']
            nickName = jsonMsg['data']['from']['nickName']
            try:
                spIdentity = jsonMsg['data']['from']['sp_identity']
                if spIdentity == SP_MANAGER:
                    nickName = '*超管*' + nickName
            except Exception as e:
                pass
            if identity == MANAGER:
                nickName = '*房管*' + nickName
            if identity == HOSTER:
                nickName = '*主播*' + nickName
            print("[" + roomid + "]" + nickName + ":" + content)
            timestamp = time.ctime()
            danmu["danmu"].append({"roomid":roomid, "type":1, "nick":nickName, "content":content, "timestamp":timestamp})
        elif jsonMsg['type'] == BAMBOO_TYPE:
            nickName = jsonMsg['data']['from']['nickName']
            print("[" + roomid + "]" + nickName + "送给主播[" + content + "]个竹子")
            danmu["danmu"].append({"roomid":roomid, "type":2, "nick":nickName, "content":content, "timestamp":timestamp})
        elif jsonMsg['type'] == AUDIENCE_TYPE:
            global is_second_audience
            if is_second_audience:
                print("[" + roomid + "]" + '===========观众人数' + content + '==========')
                is_second_audience = False
                nickName = 'sys'
                danmu["danmu"].append({"roomid":roomid, "type":3, "nick":nickName, "content":content, "timestamp":timestamp})
            else:
                is_second_audience = True
        else:
            pass
    except Exception as e:
        pass


def save_danmu():
    while True :
        time.sleep(5)
        with open(DANMU, 'w') as f:
            global danmu
            json.dump(danmu, f)

def main():
    roomids = loadInit()
    print(roomids)
    initDanmu()
    for roomid in roomids:
        threading.Thread(target=getChatInfo, args=([roomid])).start()

    threading.Thread(target=save_danmu).start()

if __name__ == '__main__':
    main()
