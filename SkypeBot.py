# coding: utf-8

'''CocSkypeBot

CoC TRPG 用 skype bot です。
使い方:
    SkypeBot.conf に情報を書く。
    $ python SkypeBot.py で起動する。

SkypeBot.confの url と token の調べ方。
    1. ブラウザで skype for web 開く。
    2. Developer Tools 開く。
    3. 目的のグループでなんかメッセージ送る。
    4. リクエストヘッダを見て……
        url: General欄の Request URL のやつ。
        token: Request Headers欄の RegistrationToken のやつ。

コマンドヘルプ:
    xxx help
        でダイスロールのフォーマットとかコマンドの種類を見ることができます。
'''

import sqlite3
import requests
import time
import os
import sys
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from Command import Command


# 設定を読む。
def readConf(paramater):
    with open('SkypeBot.conf', 'r', encoding='utf-8') as conf:
        lines = conf.readlines()
    for line in lines:
        if line.startswith(paramater):
            return line.split(' = ')[1].rstrip('\n')
conf_dbPath = str(readConf('dbPath'))
conf_roomId = str(readConf('roomId'))
conf_key    = str(readConf('key'))
conf_url    = str(readConf('url'))
conf_token  = str(readConf('token'))

# session
session = requests.session()
session.post(conf_url)
# 起動時のタイムスタンプ
startTimestamp = round(time.time())
# 反応済みIDが入るリスト
doneIdList = []
# skype for webへ送るリクエストヘッダ。
headers = {
    'Accept'           :'application/json, text/javascript',
    'Accept-Encoding'  :'gzip, deflate',
    'Accept-Language'  :'ja,en-US;q=0.8,en;q=0.6',
    'BehaviorOverride' :'redirectAs404',
    'Cache-Control'    :'no-cache, no-store, must-revalidate',
    'ClientInfo'       :'os=Windows; osVer=7; proc=Win32; lcid=en-us; deviceType=1; country=n/a; clientName=skype.com; clientVer=908/1.42.0.98//skype.com',
    'Connection'       :'keep-alive',
    # contextidは何なのか(変更や作成が必要なのか)不明
    'ContextId'        :'tcid=146372019467711519',
    'Content-Type'     :'application/json',
    'Expires'          :'0',
    'Host'             :'client-s.gateway.messenger.live.com',
    'Origin'           :'https://web.skype.com',
    'Pragma'           :'no-cache',
    'Referer'          :'https://web.skype.com/ja/',
    'User-Agent'       :'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'RegistrationToken':conf_token,
}
# 開始文字列
openMessage = 'SKYPE BOT MESSAGE: Now opened the Skype Bot!'
# 終了文字列。
closeMessage = 'You closed the Bot. Bye bye!'
# ヘルプ文字列。
helpMessage = ('Dice roll format example: \'1d100\', \'2d4 -1d4\', \'1d6 3\' or \'10 -1\'. '
    + 'You can use also commands: charamake str con pow dex app siz int edu end help. '
    + 'Write one of them after \'%s \'. :::Written by Midoriiro:::' % conf_key)
# エラー落ち文字列。
errorMessage = 'SKYPE BOT MESSAGE: Got an error! Close the Skype Bot...'


class SkypeBot:
    '''confファイルを読んで、スカイプのBOTを実行する。
    基本的な動作は、
        1. main.dbからレコードを取得。
        2. conf_keyから始まる発言に反応。
        3. 発言の内容によってCommandクラスの各メソッドから返答を取得。
        4. conf_urlとconf_tokenで指定したスカイプのグループへ返答を送信。
    '''

    def __init__(self):
        '''インスタンス変数を定義する。'''

        # 一番最初の挨拶をしたかどうかのフラグ。
        self.doneGreeting = False


    def main(self):
        '''トップレベルメソッド。'''

        # 最初の挨拶
        if not self.doneGreeting:
            self.sendSkype(openMessage)
            self.doneGreeting = True

        # 1. main.dbからレコードを取得。
        # 2. conf_keyから始まる発言に反応。
        # 処理が重い時?(原因よくわからん)sqlite3.OperationalError: disk I/O errorが出るのでそんときは処理をやり直す。
        recordList = []
        while True:
            try:
                recordList = self.selectRecordList()
                break
            except sqlite3.OperationalError:
                print('sqlite3.OperationalError')
                continue
        if not recordList:
            return False

        for record in recordList:
            # 3. 発言の内容によってCommandクラスの各メソッドから返答を取得。
            reply1 = self.getReply(record['body_xml'])
            reply2 = record['author'] + '->' + reply1
            doneIdList.append(record['id'])

            # 4. conf_urlとconf_tokenで指定したスカイプのグループへ返答を送信。
            sent = self.sendSkype(reply2)

            # 返答の中身で終了の判断をする。
            if reply1 == 'end ' + closeMessage:
                sys.exit()

        return


    def selectRecordList(self):
        '''main.dbからレコードを取得する。'''

        # コネクションを外で作るとマルチスレッドエラーになっちゃうのでここで。
        connection = sqlite3.connect(conf_dbPath + '/main.db')
        cursor = connection.cursor()
        # 反応済みIDをCSVにする。
        idCsv = ''
        for doneId in doneIdList:
            idCsv += str(doneId) + ','
        # 最後のコンマ切除。
        if idCsv:
            idCsv = idCsv[0:-1]
        # 発言を取得するSQL。「BOT起動時のタイムスタンプ後」「body_xmlがconf_keyから始まる」「反応済みリストのIDを除く」
        sql = ('SELECT id,author,body_xml FROM `Messages` '
            + 'WHERE `timestamp`>? AND `body_xml` LIKE ? AND `id` NOT IN (%s)' % idCsv)
        bind = (startTimestamp, conf_key+' %')
        if conf_roomId:
            sql += 'AND `convo_id`=?'
            bind = (startTimestamp, conf_key+' %', conf_roomId)
        # 取得する。
        cursor.execute(sql, bind)
        trash = cursor.fetchall()
        # 閉じる。
        connection.close()
        # 成形して返す。
        if not trash:
            return False
        else:
            return self.assoc(trash, ['id', 'author', 'body_xml'])


    def assoc(self, trash, columns):
        '''いつものsqlite3モジュール補助。'''
        rows = []
        for i in range(len(trash)):
            rows.append({})
            for j in range(len(trash[i])):
                rows[i][columns[j]] = trash[i][j]
        return rows


    def getReply(self, body_xml):
        '''body_xmlの内容に従ってCommandクラスから返答を得る。
        反応パターンを増やしたかったらこいつをがんがん伸ばす。'''

        # conf_keyを切除したもので判断する。
        command = body_xml[len(conf_key)+1:]
        result = ''
        if command in 'charamake':
            result = Command.cocCharamake(getString=True)
        elif command in 'str':
            result = 'STR: ' + str(Command.simpleDiceRoll(3, 6))
        elif command in 'con':
            result = 'CON: ' + str(Command.simpleDiceRoll(3, 6))
        elif command in 'pow':
            result = 'POW: ' + str(Command.simpleDiceRoll(3, 6))
        elif command in 'dex':
            result = 'DEX: ' + str(Command.simpleDiceRoll(3, 6))
        elif command in 'app':
            result = 'APP: ' + str(Command.simpleDiceRoll(3, 6))
        elif command in 'siz':
            result = 'SIZ: ' + str(Command.simpleDiceRoll(2, 6) + 6)
        elif command in 'int':
            result = 'INT: ' + str(Command.simpleDiceRoll(2, 6) + 6)
        elif command in 'edu':
            result = 'EDU: ' + str(Command.simpleDiceRoll(3, 6) + 3)
        elif command in 'end':
            result = closeMessage
        elif command in 'help':
            result = helpMessage
        elif command.startswith('xxx'):
            # xxx50 みたいなのを最初につければ成功失敗を出してくれる。
            resultDic = Command.expressionDiceRoll(command, useResultList=True, useTargetNumber=True)
            # Result:20 [+10 +10] <SUCCESS!>
            resultStr = 'SUCCESS!' if resultDic['targetResult'] else 'FAILED..'
            result = ('Result: %s %s %s' %
                (resultDic['result'], resultDic['resultList'], resultStr))
        else:
            # 以上の指定コマンドの他はダイスロール式。
            resultDic = Command.expressionDiceRoll(command, useResultList=True)
            # Result:20 [+10 +10]
            result = ('Result: %s %s' %
                (resultDic['result'], resultDic['resultList']))
        # 最終的に'someone->1d100 50 Result:20'にしたいのでコマンドをくっつけとく。
        result = command + ' ' + result
        return result


    def sendSkype(self, reply):
        '''skype for webに送信する。'''
        postjson = ('{' +
            'content        : "%s",' % reply +
            'clientmessageid: "%s",' % Command.randomInt(13) +
            'messagetype    : "RichText",' +
            'contenttype    : "text",' +
        '}')
        session.post(conf_url, data=postjson, headers=headers)
        return True



class WatchDog(FileSystemEventHandler):
    '''ファイルの変更を感知したらSkypeBotオブジェクトのmainメソッドを走らせる。'''

    def on_modified(self, events):
        '''ファイルに変更(スカイプに発言)があったらSkypeBotオブジェクトの動作開始。'''
        if events.src_path.endswith('main.db'):
            try:
                bot.main()
            except Exception as e:
                # エラー落ちしたら終了前にメッセージを送っておく
                bot.sendSkype(errorMessage)
                print(str(e))
                sys.exit()
            return


if __name__ in '__main__':
    # msn.dbのあるディレクトリ(conf_dbPathのディレクトリ)
    dbDirPath = os.path.dirname(conf_dbPath)
    bot = SkypeBot()
    dog = WatchDog()
    observer = Observer()
    observer.schedule(dog, dbDirPath, recursive=True)
    observer.start()
    # 最初に一周まわしとく。スタートメッセージ表示のため。
    bot.main()
    # 多分このjoin()の中にループWatchDogのループがある。
    observer.join()
