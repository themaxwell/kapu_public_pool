import requests
import json
import sys
import time
import copy

NODE = "http://212.237.60.84:9700"
NODEPAY = "http://localhost:9700"
PUBKEY = "03bd7c8c685b156502a61106b92d9e42a9799f1d212be4a95efc6175b3796a9950"
LOGFILE = 'poollogs.json'
PERCENTAGE = 80
TRANSACTIONFEE = 0.1
KAPUPERDAY = 423
MINPAYOUT = 1
SECRET = ""
SECONDSECRET = ""

def loadLog ():
	try:
		data = json.load (open (LOGFILE, 'r'))
	except:
		data = {
			"lastpayout": (int (time.time ())),
			"lastupdate": (int (time.time ())), 
			"lastforged": 0,
			"lastforgedupdate": 0,
			"accounts": {},
			"skip": [],
			"voters": [],
			"withdraw": {},
			"standby": {}
		}
	return data
	
	
def saveLog (log):
	json.dump (log, open (LOGFILE, 'w'), indent=4, separators=(',', ': '))
	


def calcPayouts (log):
	dopayout = False
	weight = 0.0
	payouts = []
	voters = []
	delItems=[]

	#Fetch forged KAPU
	uri = NODE + '/api/delegates/forging/getForgedByAccount?generatorPublicKey=' + PUBKEY 
	d = requests.get (uri)
	lfu = log['lastforgedupdate']
	lf = log['lastforged']
	rew = int (d.json ()['rewards'])
	log['lastforgedupdate'] = rew 

	forgedpayout = (int (rew-lf) / 100000000)
	forged = (int (rew-lfu) / 100000000)

	print ('To distribute since last payout: %f KAPU' % (forgedpayout))
	print ('To distribute since last update: %f KAPU' % (forged))

	#Do payout if kapu of full day is forged
	if forgedpayout > KAPUPERDAY:
		dopayout = True
		log['lastpayout'] = int (time.time ())
		log['lastforged'] = rew

	#Get Voters 
	d = requests.get (NODE + '/api/delegates/voters?publicKey=' + PUBKEY).json ()

	#Get Weight of Pool
	for x in d['accounts']:
		if x['balance'] == '0' or x['address'] in log['skip'] or (len(log['voters']) != 0 and x['address'] not in log['voters']):
			continue
		weight += float (x['balance']) / 100000000 
		voters.append(x['address'])

	print ('Total weight is: %f' % weight)

	#Withdraw to defined wallets
	for x  in log['withdraw']:
		withdrawbalance=forged*log['withdraw'][x]['share']/100+log['withdraw'][x]['pending']
		if dopayout:
			print ('Withdraw %f KAPU to wallet %s' % (withdrawbalance-TRANSACTIONFEE,x))
			payouts.append ({ "address": x, "balance": (withdrawbalance-TRANSACTIONFEE)})
			log['withdraw'][x]['pending'] = 0.0
			log['withdraw'][x]['received'] += withdrawbalance-TRANSACTIONFEE
		else:
			log['withdraw'][x]['pending']=withdrawbalance

	#Withdraw to voters update log
	for x in d['accounts']:
		if x['address'] in log['skip'] or (len(log['voters']) != 0 and x['address'] not in log['voters']) or x['balance'] == '0':
			continue

		if not (x['address'] in log['accounts']):
			if x['address'] in log['standby']:
				log['accounts'][x['address']]=copy.deepcopy(log['standby'][x['address']])
				del log['standby'][x['address']]
			else:
				log['accounts'][x['address']] = { 'pending': 0.0, 'received': 0.0 }

		voterbalance = (float (x['balance'])) / 100000000 * (forged * PERCENTAGE/100) / weight
		voterbalance += log['accounts'][x['address']]['pending']

		log['accounts'][x['address']]['balance']=float (x['balance']) / (100000000)
		log['accounts'][x['address']]['share']=float (x['balance']) / (weight*1000000)
		log['accounts'][x['address']]['kapuperday']=float (x['balance']) / (weight*10000000000)*KAPUPERDAY*PERCENTAGE

		if voterbalance < MINPAYOUT:
			log['accounts'][x['address']]['pending'] = voterbalance
			continue

		if dopayout:
			print ('Withdraw %f Kapu to investor with wallet %s' % (voterbalance-TRANSACTIONFEE,x['address']))
			payouts.append ({ "address": x['address'], "balance": (voterbalance-TRANSACTIONFEE)})
			log['accounts'][x['address']]['pending'] = 0.0
			log['accounts'][x['address']]['received'] += voterbalance-TRANSACTIONFEE
		else:
			log['accounts'][x['address']]['pending'] = voterbalance

	#Search for voters who removed their vote
	for y in log['accounts']:
		if not y in voters or float(log['accounts'][y]['balance']) == 0:
			delItems.append(y)

	#Copy and del old items from accounts
	for z in delItems:
		log['standby'][z]=copy.deepcopy(log['accounts'][z])
		del log['accounts'][z]
		try:
			del log['standby'][z]['balance']
			del log['standby'][z]['share']
			del log['standby'][z]['kapuperday']
		except:
			pass

	log['weight']=weight
	log['kapuperday']=KAPUPERDAY*PERCENTAGE/100

	return payouts

def performPayouts (topay,log):
	#Do Payouts
	f = open ('payments.sh', 'w')
	for x in topay:
		f.write ('echo Sending ' + str (x['balance']) + ' to ' + x['address'] + '\n')

		data = { "secret": SECRET, "amount": int (x['balance'] * 100000000), "recipientId": x['address'] }
		if SECONDSECRET != None:
			data['secondSecret'] = SECONDSECRET

		f.write ('curl -k -H  "Content-Type: application/json" -X PUT -d \'' + json.dumps (data) + '\' ' + NODEPAY + "/api/transactions\n\n")
		f.write ('sleep 10\n')

	f.close ()

if __name__ == "__main__":
	#Load logfile
	log = loadLog ()

	#Get payments
	topay = calcPayouts(log)

	#Do Payouts
	performPayouts(topay,log)

	log['lastupdate'] = int (time.time ())

	#Print log to console
	print (json.dumps (log, indent=4, separators=(',', ': ')))

	#Save and exit
	if len (sys.argv) > 1 and sys.argv[1] == '-y':
		print ('Saving...')
		saveLog (log)
	else:
		yes = input ('save? y/n: ')
		if yes == 'y':
			saveLog (log)
