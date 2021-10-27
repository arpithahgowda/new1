import logging
import time
from pprint import pprint
from kiteconnect import KiteConnect
from nsepython import *
from multiprocessing import Process

logging.basicConfig(level=logging.DEBUG)

kite = KiteConnect(api_key="mgo0cpu0qgooilh8")
kite.set_access_token("SHIWWZrBHCufA8EDtUpg6GKKO5KJm93D")

trailRunning = False
quantity = 350
hedgePrice = 9
# expiry = "21SEP"
expiry = "21O07"
indice = "BANKNIFTY"
strikeDiff = 100
defaultVals = {
    "BANKNIFTY": {"strikeDiff": 100,
                  "stoplossType": "percentage",
                  "stoplossValue": 0.30,
                  "combinedSl": False,
                  "combinedSLVal": 100,
                  "type": "ATM"},
    "NIFTY": {"strikeDiff": 50,
              "stoplossType": "absolute",
              "stoplossValue": 30,
              "type": "ITM"},
}
ATMSTraddleVal = {"PE": {}, "CE": {}}

'''Steps followed in the script..
 Place hedge buys for both put and call option based on premium defined above
 Wait for a particular time. by default 9:18:55
 Place the ATM straddle and stop loss orders
 Get all open Orders. if the Order type is Buy, that means its part of the straddle
 Now check the current price of that instrument. If it is less than its sell price,
 move the SL closer to the current price. Do this every min. Also keep track of the number of modify orders that has
 been done till now for the order. if it crosses 29, delete the existing order and place a new one. 

 Also, make sure to sleep atleast 1 sec before doing any kite query to make sure API quota isnt crossed'''


# place strangle at 9:19 am by selecting the hedges and strike price

def sleepUntil(hour, minute, second):
    t = datetime.datetime.today()
    future = datetime.datetime(t.year, t.month, t.day, hour, minute, second)
    if t.timestamp() > future.timestamp():
        future += datetime.timedelta(days=1)
    time.sleep((future - t).total_seconds())


def getATMDetails():
    # get the banknifty current price
    currentPrice = kite.quote('NSE:NIFTY BANK')['NSE:NIFTY BANK']['last_price']
    print("Current price of the indice ", indice, ": ", currentPrice)
    print("Getting values for CE and PE")
    quotient = currentPrice // strikeDiff
    reminder = currentPrice % strikeDiff
    if reminder > 50:
        ATMSTraddleVal["PE"]["StrikePrice"] = int(quotient * strikeDiff + strikeDiff)
        ATMSTraddleVal["CE"]["StrikePrice"] = int(quotient * strikeDiff + strikeDiff)
    else:
        ATMSTraddleVal["PE"]["StrikePrice"] = int(quotient * strikeDiff)
        ATMSTraddleVal["CE"]["StrikePrice"] = int(quotient * strikeDiff)
    # if we have same strike order already placed, it might mess up with the stop loss calculation
    # that is why we check for it and make it strangle if that happens
    isPlaced = checkSameStrikePlaced()
    if isPlaced:
        ATMSTraddleVal["PE"]["StrikePrice"] = ATMSTraddleVal["PE"]["StrikePrice"] + 100
        ATMSTraddleVal["CE"]["StrikePrice"] = ATMSTraddleVal["PE"]["StrikePrice"] - 100
    ATMSTraddleVal["PE"]["OptionPrice"] = \
    list(kite.quote('NFO:BANKNIFTY' + expiry + str(ATMSTraddleVal["PE"]["StrikePrice"]) + "PE").values())[0][
        'average_price']
    ATMSTraddleVal["CE"]["OptionPrice"] = \
    list(kite.quote('NFO:BANKNIFTY' + expiry + str(ATMSTraddleVal["CE"]["StrikePrice"]) + "CE").values())[0][
        'average_price']
    if defaultVals[indice]["stoplossType"] == "absolute":
        ATMSTraddleVal["PE"]["StopLoss"] = ATMSTraddleVal["PE"]["OptionPrice"] + defaultVals[indice]["stoplossValue"]
        ATMSTraddleVal["CE"]["StopLoss"] = ATMSTraddleVal["CE"]["OptionPrice"] + defaultVals[indice]["stoplossValue"]
    else:
        ATMSTraddleVal["PE"]["StopLoss"] = int(ATMSTraddleVal["PE"]["OptionPrice"] + (
                    defaultVals[indice]["stoplossValue"] * ATMSTraddleVal["PE"]["OptionPrice"]))
        ATMSTraddleVal["CE"]["StopLoss"] = int(ATMSTraddleVal["CE"]["OptionPrice"] + (
                    defaultVals[indice]["stoplossValue"] * ATMSTraddleVal["CE"]["OptionPrice"]))
    print("#=========================================#")
    print("#=========================================#")
    print("Current price of the indice ", indice, ": ", currentPrice)
    print("PE Details::\tStrikePrice: ", ATMSTraddleVal["PE"]["StrikePrice"], "\tOptionPrice:",
          ATMSTraddleVal["PE"]["OptionPrice"], "\tStopLoss:", ATMSTraddleVal["PE"]["StopLoss"])
    print("CE Details::\tStrikePrice: ", ATMSTraddleVal["CE"]["StrikePrice"], "\tOptionPrice:",
          ATMSTraddleVal["CE"]["OptionPrice"], "\tStopLoss:", ATMSTraddleVal["CE"]["StopLoss"])
    print("#=========================================#")
    print("#=========================================#")


def placeOptionOrderMarket(tradingsymbol, transactionType, quan=quantity):
    kite.place_order("regular", kite.EXCHANGE_NFO, tradingsymbol, transactionType, quan,
                     kite.PRODUCT_MIS, kite.ORDER_TYPE_MARKET,
                     validity=kite.VALIDITY_DAY,
                     disclosed_quantity=0)


def placeHedge():
    # get the banknifty current price
    orders = kite.orders()
    pprint(orders)
    currentPrice = kite.quote('NSE:NIFTY BANK')['NSE:NIFTY BANK']['last_price']
    print("Current price of the indice ", indice, ": ", currentPrice)
    quotient = currentPrice // strikeDiff
    ceStraddleStrike = int((quotient * strikeDiff) + 100)
    ceStraddlePrice = list(kite.quote('NFO:BANKNIFTY' + expiry + str(ceStraddleStrike) + "CE").values())[0][
        'average_price']
    peStraddleStrike = int((quotient * strikeDiff) - 100)
    peStraddlePrice = list(kite.quote('NFO:BANKNIFTY' + expiry + str(ceStraddleStrike) + "PE").values())[0][
        'average_price']
    foundStrikeCE = False
    foundStrikePE = False
    while (not (foundStrikeCE and foundStrikePE)):
        if ceStraddlePrice > hedgePrice and not foundStrikeCE:
            ceStraddleStrike = ceStraddleStrike + 100
            ceStraddlePrice = list(kite.quote('NFO:BANKNIFTY' + expiry + str(ceStraddleStrike) + "CE").values())[0][
                'average_price']
            print("strike is ", ceStraddleStrike)
            pprint(ceStraddlePrice)
        else:
            foundStrikeCE = True
        if peStraddlePrice > hedgePrice and not foundStrikePE:
            peStraddleStrike = peStraddleStrike - 100
            peStraddlePrice = list(kite.quote('NFO:BANKNIFTY' + expiry + str(peStraddleStrike) + "PE").values())[0][
                'average_price']
            print("strike is ", peStraddleStrike)
            pprint(peStraddlePrice)
        else:
            foundStrikePE = True
    print("#=========================================#")
    print("#=========================================#")
    print("Current price of the indice ", indice, ": ", currentPrice)
    print("PE Straddle Details::\tStrikePrice: ", peStraddleStrike, "\tOptionPrice:", peStraddlePrice)
    print("CE Straddle Details::\tStrikePrice: ", ceStraddleStrike, "\tOptionPrice:", ceStraddlePrice)
    print("#=========================================#")
    print("#=========================================#")
    kite.place_order("regular", kite.EXCHANGE_NFO, 'BANKNIFTY' + expiry + str(peStraddleStrike) + "PE",
                     kite.TRANSACTION_TYPE_BUY, quantity,
                     kite.PRODUCT_MIS, kite.ORDER_TYPE_LIMIT, price=peStraddlePrice - 1,
                     validity=kite.VALIDITY_DAY,
                     disclosed_quantity=0)
    kite.place_order("regular", kite.EXCHANGE_NFO, 'BANKNIFTY' + expiry + str(ceStraddleStrike) + "CE",
                     kite.TRANSACTION_TYPE_BUY, quantity,
                     kite.PRODUCT_MIS, kite.ORDER_TYPE_LIMIT, price=ceStraddlePrice - 1,
                     validity=kite.VALIDITY_DAY,
                     disclosed_quantity=0)


def trailingSL(combinedSL=True):
    counter = {}
    flag = True
    trailRunning = True
    while flag:
        flag = False
        time.sleep(1)
        orders = kite.orders()
        print("Total Orders till now : ", len(orders))
        print("Create a dict from all the sell orders and price it was sold at")
        sellOrders = {}
        for order in orders:
            if order['transaction_type'] == "SELL" and order['status'].upper() == "COMPLETE":
                sellOrders[order["instrument_token"]] = {"price": order["average_price"],
                                                         "name": order["tradingsymbol"],
                                                         }
                if order["instrument_token"] not in counter.keys():
                    counter[order["instrument_token"]] = 0
        pprint(sellOrders)
        pprint(counter)
        print("Get only the BUY orders which have order status OPEN")
        openOrders = []
        for order in orders:
            if order['transaction_type'] == "BUY" and order['status'].upper() == "TRIGGER PENDING" and order[
                'order_type'] == "SL":
                flag = True
                openOrders.append(order)
                trigPrice = order['trigger_price']
                stopLoss = order['price']
                orderPrice = sellOrders[order['instrument_token']]['price']
                currMarkPrice = list(kite.quote('NFO:' + order["tradingsymbol"]).values())[0]['last_price']
                print("===============================================")
                print("Current order being checked is \t", order["tradingsymbol"])
                print("The order was placed at the price: \t", orderPrice)
                print("Current market price:\t", currMarkPrice)
                print("Its current trigger price is \t", trigPrice)
                print("Its current stoploss price is \t", stopLoss)
                calcStop = 9999
                calcTrigger = 9999
                if currMarkPrice < orderPrice:
                    print("since current market price is less than order price, checking whether to modify stoploss")
                    if "BANK" in order["tradingsymbol"]:
                        if defaultVals[indice]["combinedSl"]:
                            calcStop = (orderPrice + defaultVals[indice]["combinedSLVal"]) - (
                                    orderPrice - currMarkPrice)
                            calcStop = calcStop + 10
                            calcTrigger = calcStop - 10
                        else:
                            calcStop = round((orderPrice + defaultVals[indice]["stoplossValue"] * orderPrice) - (
                                        orderPrice - currMarkPrice), 1)
                            calcStop = calcStop + 10
                            calcTrigger = calcStop - 10
                    else:
                        calcStop = (orderPrice + 30) - (orderPrice - currMarkPrice + 3)
                        calcTrigger = calcStop - 3

                    if (calcStop < stopLoss) and (stopLoss - calcStop > 3):
                        print("New stoploss will be \t", calcStop)
                        print("New trigger will be \t", calcTrigger)
                        print("Modifying existing order for the instrument")
                        try:
                            kite.modify_order(variety=order["variety"], order_id=order["order_id"],
                                              parent_order_id=None, quantity=order["quantity"], price=calcStop,
                                              order_type="SL", trigger_price=calcTrigger, validity="DAY",
                                              disclosed_quantity=0)
                            counter[order["instrument_token"]] += 1
                        except Exception as e:
                            counter[order["instrument_token"]] = 0
                            print("Order modify failed since it crossed the limit. Hence placing a new order")
                            kite.cancel_order(order["variety"], order["order_id"], parent_order_id=None)
                            kite.place_order(order["variety"], kite.EXCHANGE_NFO, order["tradingsymbol"],
                                             kite.TRANSACTION_TYPE_BUY, order["quantity"],
                                             kite.PRODUCT_MIS, kite.ORDER_TYPE_SL,
                                             price=calcStop, validity=kite.VALIDITY_DAY,
                                             disclosed_quantity=0, trigger_price=calcTrigger)
                print("===============================================")
        print("****************************************************")
        print("****************************************************")
        print("Sleeping for 15 seconds")
        time.sleep(15)
    trailRunning = False


def checkSameStrikePlaced():
    orders = kite.orders()
    print("Total Orders till now : ", len(orders))
    print("Create a dict from all the sell orders and price it was sold at")
    sellOrders = {}
    for order in orders:
        if order['transaction_type'] == "SELL" and order['status'].upper() == "COMPLETE":
            sellOrders[order["instrument_token"]] = {"price": order["average_price"],
                                                     "name": order["tradingsymbol"],
                                                     }
    print("Get only the BUY orders which have order status OPEN")
    openOrders = []
    for order in orders:
        if order['transaction_type'] == "BUY" and order['status'].upper() == "TRIGGER PENDING" and order[
            'order_type'] == "SL":
            if order["tradingsymbol"] == 'BANKNIFTY' + expiry + str(ATMSTraddleVal["PE"]["StrikePrice"]) + "PE" or \
                    order["tradingsymbol"] == 'BANKNIFTY' + expiry + str(ATMSTraddleVal["CE"]["StrikePrice"]) + "CE":
                return True
    return False


def placeStraddle(timehr=None, timemin=None, timesec=None):
    # sleepUntil(timehr, timemin, timesec)
    print("woke up for straddle")
    getATMDetails()
    # place the sell order
    placeOptionOrderMarket('BANKNIFTY' + expiry + str(ATMSTraddleVal["PE"]["StrikePrice"]) + "PE",
                           kite.TRANSACTION_TYPE_SELL, int(ATMSTraddleVal["PE"]["OptionPrice"] - 10), quan=quantity / 2)
    placeOptionOrderMarket('BANKNIFTY' + expiry + str(ATMSTraddleVal["CE"]["StrikePrice"]) + "CE",
                           kite.TRANSACTION_TYPE_SELL, int(ATMSTraddleVal["CE"]["OptionPrice"] - 10), quan=quantity / 2)
    # place the SL order based on the order price placed
    orders = kite.orders()
    print("Total Orders till now : ", len(orders))
    print("Create a dict from all the sell orders and price it was sold at")
    sellOrders = {}
    for order in orders:
        if order["tradingsymbol"] == 'BANKNIFTY' + expiry + str(ATMSTraddleVal["PE"]["StrikePrice"]) + "PE":
            ATMSTraddleVal["PE"]["StopLoss"] = int(
                order["average_price"] * defaultVals[indice]["stoplossValue"] + order["average_price"])
        elif order["tradingsymbol"] == 'BANKNIFTY' + expiry + str(ATMSTraddleVal["CE"]["StrikePrice"]) + "CE":
            ATMSTraddleVal["CE"]["StopLoss"] = int(
                order["average_price"] * defaultVals[indice]["stoplossValue"] + order["average_price"])

    kite.place_order("regular", kite.EXCHANGE_NFO,
                     'BANKNIFTY' + expiry + str(ATMSTraddleVal["PE"]["StrikePrice"]) + "PE",
                     kite.TRANSACTION_TYPE_BUY, quantity / 2,
                     kite.PRODUCT_MIS, kite.ORDER_TYPE_SL,
                     price=ATMSTraddleVal["PE"]["StopLoss"] + 10, validity=kite.VALIDITY_DAY,
                     disclosed_quantity=0, trigger_price=ATMSTraddleVal["PE"]["StopLoss"])
    kite.place_order("regular", kite.EXCHANGE_NFO,
                     'BANKNIFTY' + expiry + str(ATMSTraddleVal["CE"]["StrikePrice"]) + "CE",
                     kite.TRANSACTION_TYPE_BUY, quantity / 2,
                     kite.PRODUCT_MIS, kite.ORDER_TYPE_SL,
                     price=ATMSTraddleVal["CE"]["StopLoss"] + 10, validity=kite.VALIDITY_DAY,
                     disclosed_quantity=0, trigger_price=ATMSTraddleVal["CE"]["StopLoss"])
    print("straddle of time ", timehr, "is placed")
    datetime_object = datetime.datetime.now()
    print(datetime_object)
    if not trailRunning:
        trailingSL()


def main(hedge, straddle):
    # sleepUntil(9,17,58)
    # if hedge:
    #     print("woke up for hedge")
    #     placeHedge()
    # datetime_object = datetime.datetime.now()
    # print(datetime_object)
    # if straddle:
    # p1 = Process(target=placeStraddle, args=(9,21,0))
    # p2 = Process(target=placeStraddle, args=(10,50,0))
    # p1.start()
    # p2.start()
    # p1.join()
    # p2.join()
    # datetime_object = datetime.datetime.now()
    placeStraddle()
    # print(datetime_object)
    trailingSL()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Script for BN straddle with hedge')
    parser.add_argument('--hedge', metavar='Boolean', required=False, default=True,
                        help='Set to false if dont want hedge')
    parser.add_argument('--straddle', metavar='Boolean', required=False,
                        help='Set to false if you dont want to place the straddle order', default=True)
    # parser.print_help()
    args = parser.parse_args()
    trailingSL()
    # main(args.hedge, args.straddle)
    # main(True, True)
    # main(False, False)




