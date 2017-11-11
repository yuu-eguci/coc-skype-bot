# coding: utf-8

'''
author = 'Midoriiro<http://guild-elf.jugem.jp/>'
date = '2016.09.07.'
'''

from random import randint

class Command:
    '''文字列や数値を返すメソッドをまとめたクラス。'''

    def randomInt(digit):
        '''digit桁の数を返す。'''
        start = int('1' + '0' * (digit - 1))
        end = int('9' * digit)
        return randint(start, end)

    def expressionDiceRoll(expression, useResultList=False, useTargetNumber=False):
        '''「 *d* -*d* * -* 」の形式の式を計算して返す。
        結果は「 ** (* * *) 」で返す。
        useResultListがTrueなら、結果とresultListをディクショナリで返す。
        xxx xxx** から始まるなら目標値判定モードになる。結果を比較して成功(True)失敗(False)もディクショナリに加えて返す。'''

        # Dを小文字にし、スペースで区切る。
        expression = expression.lower()
        expressionList = expression.split(' ')

        # 計算
        resultList = []
        result = 0
        targetResult = False
        try:
            # 目標値判定モードかどうか判断する。
            if useTargetNumber:
                targetNumber = 0
                if expressionList[0].startswith('xxx'):
                    # xxxを切ったものが対象の数値
                    targetNumber = int(expressionList[0][3:])
                    del expressionList[0]

            for term in expressionList:
                # dを含む
                if 'd' in term:
                    # マイナスから始まるなら、マイナスとってsimpleDiceRollへ
                    if term.startswith('-'):
                        aANDb = term[1:].split('d')
                        # フリーズ対策
                        tmp = Command.simpleDiceRoll(aANDb[0], aANDb[1])
                        if not tmp:
                            result = 'BotError: Too big number was used.'
                            break
                        result -= tmp
                        resultList.append('-' + str(tmp))
                    else:
                        aANDb = term.split('d')
                        # フリーズ対策
                        tmp = Command.simpleDiceRoll(aANDb[0], aANDb[1])
                        if not tmp:
                            result = 'BotError: Too big number was used.'
                            break
                        result += tmp
                        resultList.append('+' + str(tmp))
                # マイナスから始まる整数
                elif term.startswith('-'):
                    # フリーズ対策
                    tmp = int(term[1:])
                    if Command.checkTooBigNumber(tmp):
                        result = 'BotError: Too big number was used.'
                        break
                    result -= tmp
                    resultList.append('-' + str(tmp))
                # ソレ以外なら正の整数だろう
                else:
                    # フリーズ対策
                    tmp = int(term)
                    if Command.checkTooBigNumber(tmp):
                        result = 'BotError: Too big number was used.'
                        break
                    result += tmp
                    resultList.append('+' + str(tmp))

            if useTargetNumber and result <= targetNumber:
                targetResult = True
        except Exception as e:
            print(str(e))
            # 形式に悖っていたら「おかしーよ」とだけ返す
            result = 'BotError: Please check your input or blame the maker.'

        # 結果を返す。
        if useResultList or (targetNumber != False):
            return {
                'result': result,
                'resultList': resultList,
                'targetResult': targetResult,
            }
        else:
            return result

    def checkTooBigNumber(num):
        '''5桁以上ならTrueを返す。'''
        if int(num) >= 10000:
            return True
        else:
            return False

    def simpleDiceRoll(a, b):
        '''aDbの結果を返す。'''
        a = int(a)
        b = int(b)

        # フリーズ対策  5桁以上ならアウト
        if Command.checkTooBigNumber(a) or Command.checkTooBigNumber(b):
            return False

        result = 0
        for i in range(a):
            c = randint(1, b)
            result += c
        return result

    def cocCharamake(getString=False):
        '''CoCのキャラステータスを作成して返す。
        getStringがTrueなら文字列にして返す。'''
        d = {
            'str': Command.simpleDiceRoll(3, 6),
            'con': Command.simpleDiceRoll(3, 6),
            'pow': Command.simpleDiceRoll(3, 6),
            'dex': Command.simpleDiceRoll(3, 6),
            'app': Command.simpleDiceRoll(3, 6),
            'siz': Command.simpleDiceRoll(2, 6) + 6,
            'int': Command.simpleDiceRoll(2, 6) + 6,
            'edu': Command.simpleDiceRoll(3, 6) + 3,
        }
        if (getString):
            return ('STR:%s CON:%s POW:%s DEX:%s APP:%s SIZ:%s INT:%s EDU:%s' %
                (d['str'], d['con'], d['pow'], d['dex'], d['app'], d['siz'], d['int'], d['edu']))
        return d




if __name__ in '__main__':
    # メソッドのテスト。
    print(Command.randomInt(5))
    print(Command.expressionDiceRoll('2d4 1d4 -5', useResultList=True, targetNumber=5))
    print(Command.checkTooBigNumber(10001))
    print(Command.simpleDiceRoll(1, 100))
    print(Command.cocCharamake(getString=True))

