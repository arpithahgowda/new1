import logging
from kiteconnect import KiteConnect

logging.basicConfig(level=logging.DEBUG)

kite = KiteConnect(api_key= "mgo0cpu0qgooilh8")

# Redirect the user to the login url obtained
# from kite.login_url(), and receive the request_token
# from the registered redirect url after the login flow.
# Once you have the request_token, obtain the access_token
# as follows.

data = kite.generate_session("I7iO7PUmOe740eP5rsl7cVoOHgGQU6y8",api_secret="8retc59vcbx2no9kptxawcivk08wap4i")
kite.set_access_token(data["access_token"])

# # Place an order
# try:
#     order_id = kite.place_order(
#         variety=kite.VARIETY_REGULAR,
#         exchange=kite.EXCHANGE_NSE,
#         tradingsymbol="INFY",
#         transaction_type=kite.TRANSACTION_TYPE_BUY,
#         quantity=1,
#         product=kite.PRODUCT_CNC,
#         order_type=kite.ORDER_TYPE_MARKET
#     )
#
#     logging.info("Order placed. ID is: {}".format(order_id))
# except Exception as e:
#     logging.info("Order placement failed: {}".format(e.message))
try:
    order_id = kite.place_gtt(	self, trigger_type, tradingsymbol, exchange, trigger_values, last_price, orders)

    logging.info("Order placed. ID is: {}".format(order_id))
except Exception as e:
    logging.info("Order placement failed: {}".format(e.message))

# Fetch all orders
kite.orders()

# Get instruments
kite.instruments()

    # # Place an mutual fund order
    # kite.place_mf_order(
    #     tradingsymbol="INF090I01239",
    #     transaction_type=kite.TRANSACTION_TYPE_BUY,
    #     amount=5000,
    #     tag="mytag"
# )

# Cancel a mutual fund order
kite.cancel_mf_order(order_id="order_id")

# Get mutual fund instruments
kite.mf_instruments()
