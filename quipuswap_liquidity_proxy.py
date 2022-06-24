import smartpy as sp 

Addresses = sp.io.import_script_from_url("file:test-helpers/addresses.py")
Constants = sp.io.import_script_from_url("file:common/constants.py")
Errors = sp.io.import_script_from_url("file:common/errors.py")

################################################################
# State Machine
################################################################

IDLE = 0
WAITING_FOR_TOKEN_BALANCE = 1

################################################################
# Contract
################################################################

# Creates a liquidity fund contract for managing liquidity on a Quipuswap pair
# Allows the "Executor" address to add liquidity to Quipuswap and veto
# Allows the "Governor" address to remove liquidity, claim rewards, vote, transfer tokens or XTZ, and set the Executor address
class LiquidityFundContract(sp.Contract):
    def __init__(
        self,
        governorContractAddress = Addresses.GOVERNOR_ADDRESS,
        executorContractAddress = Addresses.EXECUTOR_ADDRESS,
        tokenContractAddress = Addresses.TOKEN_ADDRESS,
        quipuswapContractAddress = Addresses.QUIPUSWAP_ADDRESS,
        harbingerContractAddress = Addresses.HARBINGER_ADDRESS,

        volatilityTolerance = sp.nat(5), # 5%
        
        state = IDLE,
        sendAllTokens_destination = sp.none,
        **extra_storage
    ):
        self.exception_optimization_level = "DefaultUnit"

        self.init(
            governorContractAddress = governorContractAddress,
            executorContractAddress = executorContractAddress,
            tokenContractAddress = tokenContractAddress,
            quipuswapContractAddress = quipuswapContractAddress,
            harbingerContractAddress = harbingerContractAddress,

            volatilityTolerance = volatilityTolerance,

            # State machine
            state = state,
            sendAllTokens_destination = sendAllTokens_destination,

            **extra_storage
        )

    ################################################################
    # Public API
    ################################################################

    # Allow XTZ transfers into the fund.
    @sp.entry_point
    def default(self):
        pass

    ################################################################
    # Quipuswap API
    ################################################################

    @sp.entry_point
    def addLiquidity(self, param):
        sp.set_type(param, sp.TRecord(tokens = sp.TNat, mutez = sp.TNat).layout(("tokens", "mutez")))

        # Verify the caller is the permissioned executor account.
        sp.verify(sp.sender == self.data.executorContractAddress, message = Errors.NOT_EXECUTOR)

        # Destructure parameters.
        tokensToAdd = param.tokens
        mutezToAdd = param.mutez

        # Read vwap from Harbinger Normalizer views
        harbingerVwap = sp.view(
            "getPrice",
            self.data.harbingerContractAddress,
            Constants.ASSET_CODE,
            sp.TPair(sp.TTimestamp, sp.TNat)
        ).open_some(message = Errors.VWAP_VIEW_ERROR)

        harbingerPrice = (sp.snd(harbingerVwap))

        # Calculate input price to compare to Harbinger
        inputPrice = tokensToAdd // mutezToAdd // 1000000

        # Check for volatility difference between Harbinger and function input
        volatilityDifference = (abs(harbingerPrice - inputPrice) // harbingerPrice) * 100 # because tolerance is a percent
        sp.verify(self.data.volatilityTolerance > volatilityDifference, Errors.VOLATILITY)

        # Assert that the Harbinger data is newer than max data delay
        dataAge = sp.as_nat(sp.now - sp.fst(sp.snd(harbingerVwap)))
        sp.verify(dataAge <= self.data.maxDataDelaySec, Errors.STALE_DATA)
        
        # Approve Quipuswap contract to spend on token contract
        approveHandle = sp.contract(
            sp.TPair(sp.TAddress, sp.TNat),
            self.data.tokenContractAddress,
            "approve"
        ).open_some(message = Errors.APPROVAL)
        approveArg = sp.pair(self.data.quipuswapContractAddress, tokensToAdd)
        sp.transfer(approveArg, sp.mutez(0), approveHandle)

        # Add the liquidity to the Quipuswap contract.
        addHandle = sp.contract(
            sp.TNat,
            self.data.quipuswapContractAddress,
            "investLiquidity"
        ).open_some(message = Errors.DEX_CONTRACT_ERROR)
        sp.transfer(tokensToAdd, sp.utils.nat_to_mutez(mutezToAdd), addHandle)
    
    @sp.entry_point
    def removeLiquidity(self, param):
        sp.set_type(param, sp.TRecord(
            min_mutez_out = sp.TNat, 
            min_tokens_out = sp.TNat, 
            lp_to_remove = sp.TNat
            ).layout((("min_mutez_out", "min_tokens_out"), ("lp_to_remove"))))

        # Verify the caller is the governor address
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)

        # Destructure parameters
        minMutez = param.min_mutez_out
        minTokens = param.min_tokens_out
        amountToRemove = param.lp_to_remove

        # Remove liquidity from the Quipuswap contract
        divestHandle = sp.contract(
            sp.TPair(sp.TPair(sp.TNat, sp.TNat), sp.TNat),
            self.data.quipuswapContractAddress,
            "divestLiquidity"
        ).open_some(message = Errors.DEX_CONTRACT_ERROR)
        arg = sp.pair(sp.pair(minMutez, minTokens), amountToRemove)
        sp.transfer(arg, sp.mutez(0), divestHandle)

    @sp.entry_point
    def claimRewards(self):

        # Verify the caller is the governor address
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)

        address = sp.self_address

        # Claim rewards from the Quipuswap contract
        claimHandle = sp.contract(
            sp.TAddress,
            self.data.quipuswapContractAddress,
            "withdrawProfit"
        ).open_some(message = Errors.DEX_CONTRACT_ERROR)
        sp.transfer(address, sp.mutez(0), claimHandle) 

    @sp.entry_point
    def vote(self, param):
        sp.set_type(param, sp.TRecord(
            candidate = sp.TKeyHash,
            value = sp.TNat,
            voter = sp.TAddress
        ).layout((("candidate", "value"), ("voter"))))
        
        # Verify the caller is the governor address
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)


        # Claim rewards from the Quipuswap contract
        voteHandle = sp.contract(
            sp.TPair(sp.TPair(sp.TKeyHash, sp.TNat), sp.TAddress),
            self.data.quipuswapContractAddress,
            "vote"
        ).open_some(message = Errors.DEX_CONTRACT_ERROR)
        arg = sp.pair(sp.pair(param.candidate, param.value), param.voter)
        sp.transfer(arg, sp.mutez(0), voteHandle)
    
    @sp.entry_point
    def veto(self, param):
        sp.set_type(param, sp.TRecord(
            value = sp.TNat,
            voter = sp.TAddress
        ).layout((("value", "voter"))))

        # Verify the caller is the executor address
        sp.verify(sp.sender == self.data.executorContractAddress, message = Errors.NOT_GOVERNOR)
    
        vetoHandle = sp.contract(
            sp.TPair(sp.TNat,sp.TAddress),
            self.data.quipuswapContractAddress,
            "veto"
        ).open_some(message = Errors.DEX_CONTRACT_ERROR)
        arg = sp.pair(param.value,param.voter)
        sp.transfer(arg, sp.mutez(0), vetoHandle) 	


    ################################################################
    # Governance
    ################################################################

    @sp.entry_point
    def setDelegate(self, newDelegate):
        sp.set_type(newDelegate, sp.TOption(sp.TKeyHash))

        # Verify the caller is the governor.
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_ADMIN)

        sp.set_delegate(newDelegate)

    # Governance is timelocked and can always transfer funds.
    @sp.entry_point
    def send(self, param):
        sp.set_type(param, sp.TPair(sp.TMutez, sp.TAddress))

        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)
        sp.send(sp.snd(param), sp.fst(param))

    # Governance is timelocked and can always transfer funds.
    @sp.entry_point
    def sendAll(self, destination):
        sp.set_type(destination, sp.TAddress)

        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)
        sp.send(destination, sp.balance)        

    # Governance is timelocked and can always transfer funds.
    @sp.entry_point
    def sendTokens(self, param):
        sp.set_type(param, sp.TPair(sp.TNat, sp.TAddress))

        # Verify sender is governor.
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)

        # Destructure parameters.
        amount = sp.fst(param)
        destination = sp.snd(param)

        # Invoke token contract
        tokenContractParam = sp.record(
            to_ = destination,
            from_ = sp.self_address,
            value = amount
        )
        contractHandle = sp.contract(
            sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
            self.data.tokenContractAddress,
            "transfer"
        ).open_some()
        sp.transfer(tokenContractParam, sp.mutez(0), contractHandle)

    # Transfer the entire balance of kUSD
    @sp.entry_point
    def sendAllTokens(self, destination):
        sp.set_type(destination, sp.TAddress)

        # Verify sender is governor.
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)

        # Verify state is correct.
        sp.verify(self.data.state == IDLE, message = Errors.BAD_STATE)

        # Call token contract to get the balance
        tokenContractHandle = sp.contract(
            sp.TPair(
                sp.TAddress,
                sp.TContract(sp.TNat),
            ),
            self.data.tokenContractAddress,
            "getBalance"
        ).open_some()
        tokenContractArg = (
            sp.self_address,
            sp.self_entry_point(entry_point = "sendAllTokens_callback")
        )
        sp.transfer(tokenContractArg, sp.mutez(0), tokenContractHandle)

        # Save state to state machine
        self.data.state = WAITING_FOR_TOKEN_BALANCE
        self.data.sendAllTokens_destination = sp.some(destination)      

    # Private callback for `sendAllTokens`
    @sp.entry_point
    def sendAllTokens_callback(self, tokenBalance):
        sp.set_type(tokenBalance, sp.TNat)

        # Verify sender is the token contract
        sp.verify(sp.sender == self.data.tokenContractAddress, message = Errors.BAD_SENDER)

        # Verify state is correct.
        sp.verify(self.data.state == WAITING_FOR_TOKEN_BALANCE, message = Errors.BAD_STATE)

        # Unwrap saved parameters.
        destination = self.data.sendAllTokens_destination.open_some()

        # Invoke token contract
        tokenContractParam = sp.record(
            to_ = destination,
            from_ = sp.self_address,
            value = tokenBalance
        )
        contractHandle = sp.contract(
            sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
            self.data.tokenContractAddress,
            "transfer"
        ).open_some()
        sp.transfer(tokenContractParam, sp.mutez(0), contractHandle)

        # Reset state
        self.data.state = IDLE
        self.data.sendAllTokens_destination = sp.none      

    # Rescue FA1.2 Tokens
    @sp.entry_point
    def rescueFA12(self, params):
        sp.set_type(params, sp.TRecord(
            tokenContractAddress = sp.TAddress,
            amount = sp.TNat,
            destination = sp.TAddress,
        ).layout(("tokenContractAddress", ("amount", "destination"))))

        # Verify sender is governor.
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)

        # Transfer the tokens
        handle = sp.contract(
            sp.TRecord(
                from_ = sp.TAddress,
                to_ = sp.TAddress, 
                value = sp.TNat
            ).layout(("from_ as from", ("to_ as to", "value"))),
            params.tokenContractAddress,
            "transfer"
        ).open_some()
        arg = sp.record(from_ = sp.self_address, to_ = params.destination, value = params.amount)
        sp.transfer(arg, sp.mutez(0), handle)

    # Rescue FA2 tokens
    @sp.entry_point
    def rescueFA2(self, params):
        sp.set_type(params, sp.TRecord(
            tokenContractAddress = sp.TAddress,
            tokenId = sp.TNat,
            amount = sp.TNat,
            destination = sp.TAddress,
        ).layout(("tokenContractAddress", ("tokenId", ("amount", "destination")))))

        # Verify sender is governor.
        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)

        # Transfer the tokens
        handle = sp.contract(
            sp.TList(
                sp.TRecord(
                    from_ = sp.TAddress,
                    txs = sp.TList(
                        sp.TRecord(
                            amount = sp.TNat,
                            to_ = sp.TAddress, 
                            token_id = sp.TNat,
                        ).layout(("to_", ("token_id", "amount")))
                    )
                ).layout(("from_", "txs"))
            ),
            params.tokenContractAddress,
            "transfer"
        ).open_some()

        arg = [
            sp.record(
            from_ = sp.self_address,
            txs = [
                sp.record(
                    amount = params.amount,
                    to_ = params.destination,
                    token_id = params.tokenId
                )
            ]
            )
        ]
        sp.transfer(arg, sp.mutez(0), handle)                

    # Update the governor contract.
    @sp.entry_point
    def setGovernorContract(self, newGovernorContractAddress):
        sp.set_type(newGovernorContractAddress, sp.TAddress)

        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)
        self.data.governorContractAddress = newGovernorContractAddress

    # Update the executor contract.
    @sp.entry_point
    def setExecutorContract(self, newExecutorContractAddress):
        sp.set_type(newExecutorContractAddress, sp.TAddress)

        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)
        self.data.executorContractAddress = newExecutorContractAddress
    
    # Set volatility tolerance (in percent)
    @sp.entry_point
    def setVolatilityTolerance(self, newVolatilityTolerance):
        sp.set_type(newVolatilityTolerance, sp.TNat)

        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)
        self.data.volatilityTolerance = newVolatilityTolerance

    # Update the harbinger normalizer contract.
    @sp.entry_point
    def setHarbingerContract(self, newHarbingerContractAddress):
        sp.set_type(newHarbingerContractAddress, sp.TAddress)

        sp.verify(sp.sender == self.data.governorContractAddress, message = Errors.NOT_GOVERNOR)
        self.data.harbingerContractAddress = newHarbingerContractAddress
