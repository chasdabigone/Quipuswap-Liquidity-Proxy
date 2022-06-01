################################################################
# Errors from Kolibri contracts.
#
#  IMPORTANT: Keep this file in sync with /sdk/src/contract-errors.py.
################################################################

# The sender of a contract invocation was required to be the Governor contract.
NOT_GOVERNOR = 1

# The sender of an operation was required to be the Administrator of the contract.
NOT_EXECUTOR = 2

# The sender of an operation was required to be the Pause Guardian.
NOT_PAUSE_GUARDIAN = 3

# The data provided was too old.
STALE_DATA = 4

# The system is paused.
PAUSED = 5

# Cannot receive funds.
CANNOT_RECEIVE_FUNDS = 6

# The swap was attempted before min delay time
TRADE_TIME = 7

# VWAP vs input price is too volatile
VOLATILITY = 8

# Not enough tokens to perform swap
NOT_ENOUGH_TOKENS = 9

# The sender was not the expected contract
BAD_SENDER = 10

# Error calling view on Harbinger Normalizer
VWAP_VIEW_ERROR = 11

# Error while interacting with DEX contract
DEX_CONTRACT_ERROR = 13
