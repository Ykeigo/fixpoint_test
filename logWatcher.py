import argparse    # 1. argparseをインポート
import csv

#サブネットアドレスを2進数にして返す（サブネット生死判定用）
def getNetworkAddress(address):
    slashPos = address.find('/')
    prefixLengths = int(address[slashPos+1:])

    adds = address[:slashPos].split(".")
    binary_adds = ""
    for i in adds:
        binary_adds += bin(int(i))[2:].zfill(8)

    #print(prefixLengths)
    #print(binary_adds)
    return binary_adds[:prefixLengths]

#2進数のアドレスを8桁ごとに区切って10進数に戻す（見やすくするため）
def getDecimalAddress(binAddress):
    binAddsSplit = [binAddress[i: i+8] for i in range(0, len(binAddress), 8)]
    decimalString = ""
    for i in binAddsSplit:
        decimalString += str(int(i,2)) + "."
    return decimalString[:-1]

parser = argparse.ArgumentParser(description='ログ監視プログラム')    # 2. パーサを作る

# 3. parser.add_argumentで受け取る引数を追加していく
parser.add_argument('logFilePath')    # 必須の引数を追加
parser.add_argument('-n', '--n')    # オプション引数（指定しなくても良い引数）を追加
parser.add_argument('-m', '--m')    # オプション引数（指定しなくても良い引数）を追加
parser.add_argument('-t', '--t')   # よく使う引数なら省略形があると使う時に便利

args = parser.parse_args()    # 4. 引数を解析

if args.n:
    N = int(args.n)
else:
    N = 1

#mとtがあれば過負荷状態を監視する
watchOverload = False
M = None
T = None
if args.m and args.t:
    watchOverload = True
    M = int(args.m)
    T = int(args.t)

#print(args)

log = []
with open(args.logFilePath) as f:
    reader = csv.reader(f)
    log = [row for row in reader]

unavailabled = []
failed = {}
responceTimes = {}
avrResponceTimes = {}

subnetState = {}
subnetFailed = {}
subnetUnavailabled = []

for i in log:
    #応答時間を記録する
    if watchOverload:
        #print(responceTimes)
        if i[1] not in responceTimes:
            responceTimes[i[1]] = [i[2]]
        else:
            responceTimes[i[1]].append(i[2])

        if len(responceTimes[i[1]]) > M:
            responceTimes[i[1]].pop(0)
        if len(responceTimes[i[1]]) == M:
            s = 0
            num = 0
            for j in responceTimes[i[1]]:
                if j != '-':
                    s += int(j)
                    num += 1
            if i[1] not in avrResponceTimes:
                avrResponceTimes[i[1]] = []
            if num != 0:
                avrResponceTimes[i[1]].append([i[0], s/num])
            else:
                avrResponceTimes[i[1]].append([i[0], -1])

    #サブネットにこのアドレスを追加
    subnetAddress = getNetworkAddress(i[1])
    if subnetAddress not in subnetState:
        subnetState[subnetAddress] = {}
    if i[1] not in subnetState[subnetAddress]:
        subnetState[subnetAddress][i[1]] = True
    #print("{}のサブネット".format(i[1]))
    #print(subnetState[subnetAddress])
    #このサーバーが故障してたらサブネットを調べる
    dead = False
    #タイムアウト監視
    if i[1] in failed:
        if i[2] != '-':
            #print(i)
            #print(failed[i[1]])
            #N回以上応答なしだったやつから応答があれば故障ログに記録
            if failed[i[1]][2] >= N:
                unavailabled.append([i[1], failed[i[1]][0], i[0]])
                #そのサブネットのアドレスが死んでる判定を出す
                subnetState[subnetAddress][i[1]] = False
                dead = True

            failed.pop(i[1])
        #また応答なしなら応答なしカウンタを増やす
        else:
            failed[i[1]][2] += 1
            if failed[i[1]][2] >= N:
                #そのサブネットのアドレスが死んでる判定を出す
                subnetState[subnetAddress][i[1]] = False
                dead = True

    #応答がなければそれを記録する
    elif i[2] == '-':
        #3つめの要素は応答なしの回数
        failed[i[1]] = [i[0],i[1],1]
        # N=1のときのためにここでもサブネット生死判定しておく
        if failed[i[1]][2] >= N:
            #そのサブネットのアドレスが死んでる判定を出す
            subnetState[subnetAddress][i[1]] = False
            dead = True


    #サブネットが落ちてるか確認
    alldead = False
    if dead:
        alldead = True
        #print(subnetState)
        for server in subnetState[subnetAddress]:
            if subnetState[subnetAddress][server]:
                alldead = False
                break
    #サブネットが落ちてたら記録
    if alldead:
        if subnetAddress not in subnetFailed:
            subnetFailed[subnetAddress] = i[0]
    #サブネットが落ちてて復活したら記録
    else:
        #print(subnetFailed)
        if subnetAddress in subnetFailed:
            subnetUnavailabled.append([subnetAddress,subnetFailed[subnetAddress], i[0]])
            subnetFailed.pop(subnetAddress)

print("故障していたサーバー")
if len(unavailabled) == 0:
    print("なし")
for i in unavailabled:
    #print(getNetworkAddress(i[0]))
    print("{} {} - {}".format(i[0], i[1], i[2]))
"""
print("現在故障しているかもしれないサーバー")
for i in failed:
    print("{} {}~".format(failed[i][0], failed[i][1]))
"""

if watchOverload:
    print()
    print("過負荷状態だったサーバー")
    #print(responceTimes)
    #print(avrResponceTimes)
    for server in avrResponceTimes:
        overloaded = []
        start = -1
        pretime = -1
        for resTimeLog in avrResponceTimes[server]:
            #print(resTimeLog[1])
            if resTimeLog[1] > T:
                if start == -1:
                    start = resTimeLog[0]
            else:
                if start != -1:
                    overloaded.append([start, pretime])
                    start = -1

            pretime = resTimeLog[0]
        if start != -1:
            overloaded.append([start, "now"])
        
        if len(overloaded) > 0:
            print("server {}".format(server))
            for i in overloaded:
                print("{} - {}".format(i[0], i[1]))

print()
print("故障していたサブネット")
if len(subnetUnavailabled) == 0:
    print("なし")
for i in subnetUnavailabled:
    #print(getNetworkAddress(i[0]))
    print("{} {} - {}".format(getDecimalAddress(i[0]), i[1], i[2]))

#print(avrResponceTimes)