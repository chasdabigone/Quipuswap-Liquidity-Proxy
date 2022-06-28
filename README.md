# Quipuswap-Liquidity-Proxy
This is a fork of https://github.com/Hover-Labs/kolibri-contracts/blob/master/smart_contracts/dev-fund.py

**Overview**

A LiquidityFund contract collects funds in kUSD and XTZ for interaction with a Quipuswap AMM Contract.

The LiquidityFund can add and remove liquidity, along with utilizing Quipuswap governance. It can also disburse any XTZ and tokens it contains.

The LiquidityFund contract has two permissions on it: 

(1) Executor: Can use the `addLiquidity` and `veto` functions 

(2) Governor: Can utilize `removeLiquidity`, `claimRewards`, and `vote` functions. Can swap Governors, Administrators and transfer XTZ

Executor should be a multi-sig or governance function controlled without a time delay, while Governor should be a higher privileged multi-sig or DAO with a time lock.

**ACL Checking**

Anyone may deposit XTZ into a DevFund.

The Governor can utilize the `divestLiquidity`, `vote`, and `claimRewards` functions that are wrappers for the Quipuswap AMM DEX. The Governor can choose the baker for the LiquidityFund. The Governor can change the executor and other contract references. The Governor can also disburse funds.

**Core Upgrade Path**

Any contract which needs to interact with a LiquidityFund should have a governable reference to the LiquidityFund.

If a new LiquidityFund contract is needed then: (1) A new LiquidityFund contract would be deployed (2) The Governor would update every contract that interacts with the DevFund to point to the new LiquidityFund. (3) The Governor would transfer existing tokens and XTZ to the new LiquidityFund

**State Machine**

The LiquidityFund contract has a state machine for utilizing the `sendAllTokens()` and `sendAllTokens_callback()` functions.

**Storage**

The LiquidityFund contract stores the following:

`governorContractAddress` (address): The Governor.

`executorContractAddress` (address): The Executor.

`tokenContractAddress` (address): FA 1.2 token

`quipuswapContractAddress` (address): Quipuswap AMM Contract Address

`harbingerContractAddress` (address): Address of the Harbinger Oracle Normalizer

`volatilityTolerance` (nat): A number in percent that determines how much spread between oracle and Quipuswap is allowed


These storage parameters are governable and can be changed by governorContractAddress.

Other storage:

`state`: for state machine callback

`sendAllTokens_destination`: for sendAllTokens callback

**Entrypoints**

The LiquidityFund contract has the following entrypoints:

`default`: No-op. Implemented so the contract can receive XTZ.

`addLiquidity`: Call `investLiquidity()` on the Quipuswap contract. Can only be called by the executorContractAddress.

`removeLiquidity`: Call `divestLiquidity()` on the Quipuswap contract. Can only be called by the governorContractAddress.

`claimRewards`: Call `withdrawProfit()` on the Quipuswap contract. Can only be called by the governorContractAddress.

`vote`: Call `vote()` on the Quipuswap contract. Can only be called by the governorContractAddress.

`veto`: Call `veto()` on the Quipuswap contract. Can only be called by the executorContractAddress.

`setDelegate`: Set the baker for the contract. Can only be called by the administratorContractAddress.

`send`: Send XTZ to a recipient. Can only be called by the governorContractAddress.

`sendAll`: Send all XTZ to a recipient. Can only be called by the governorContractAddress.

`sendTokens`: Send tokenContractAddress tokens to a recipient. Can only be called by the governorContractAddress.

`sendAllToken`s: Send all tokenContractAddress tokens to a recipient. Can only be called by the governorContractAddress.

`sendAllTokens_callback`: Callback for the sendAllTokens function. Can only be called by tokenContractAddress.

`rescueFA12`: Send any FA1.2 token to a recipient. Can only be called by the governorContractAddress.

`rescueFA2`: Send any FA2 token to a recipient. Can only be called by the governorContractAddress.

`setGovernorContract`: Update the governorContractAddress. Can only be called by the governorContractAddress.

`setExecutorContract`: Update the executorContractAddress. Can only be called by the governorContractAddress.

`setVolatilityTolerance`: Update the volatilityTolerance. Can only be called by the governorContractAddress.

`setHarbingerContract`: Update the harbingerContractAddress. Can only be called by the governorContractAddress.
