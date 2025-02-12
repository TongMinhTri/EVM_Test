import argparse
import time

from pyrevm import EVM, BlockEnv
from web3 import Web3

from contract import Contract

MY_ADDR = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth
BOT_ADDR = "0x66B8a48DD0A0F42A4f0cb8286ED796D41E664f07"  # vitalik.eth

erc20token = dict()


class ERC20Token:
    # No fee
    def transfer(self, amount):
        return amount


class TokenFixedFee(ERC20Token):
    fee_rate: float

    def __init__(self, fee_rate):
        self.fee_rate = fee_rate

    def transfer(self, amount):
        return amount - amount * self.fee_rate / 100


class TokenBuyCountTimeFee(ERC20Token):
    buy_count: int
    transaction_time: int
    trading_opened_time: int
    fee_tier = []

    def __init__(self, buy_count, transaction_time, trading_opened_time, fee_tier):
        self.buy_count = buy_count
        self.transaction_time = transaction_time
        self.trading_opened_time = trading_opened_time
        self.fee_tier = fee_tier

    def transfer(self, amount):
        current_fee_tier = 0

        if self.transaction_time >= self.trading_opened_time:
            current_fee_tier = self.fee_tier[3]
        else:
            if 30 <= self.buy_count < 60:
                current_fee_tier = self.fee_tier[0]
            elif 60 <= self.buy_count < 90:
                current_fee_tier = self.fee_tier[1]
            elif self.buy_count >= 90:
                current_fee_tier = self.fee_tier[2]

        return amount - amount * current_fee_tier / 100


class TokenBuyCountFee(ERC20Token):
    buy_count: int
    initial_fee: int
    final_fee: int
    reduce_fee_at: int

    def __init__(self, buy_count, initial_fee, final_fee, reduce_fee_at):
        self.buy_count = buy_count
        self.initial_fee = initial_fee
        self.final_fee = final_fee
        self.reduce_fee_at = reduce_fee_at

    def transfer(self, amount):
        current_fee = self.initial_fee
        if self.buy_count > self.reduce_fee_at:
            current_fee = self.final_fee

        return amount - amount * current_fee / 100


class CheckResult:
    has_v2_pair: bool = True
    buy_fee: float = 0.0
    sell_fee: float = 0.0
    transfer_fee: float = 0.0
    transfer_status: str = ""


def get_args() -> argparse.Namespace:
    parse = argparse.ArgumentParser()
    parse.add_argument('--rpc_url', default='http://192.168.1.58:8545')
    parse.add_argument('--file_path')
    return parse.parse_args()


def init_token():
    erc20token['0x298d492e8c1d909d3f63bc4a36c66c64acb3d695'] = TokenFixedFee(0.5)
    erc20token['0xa2b4c0af19cc16a6cfacce81f192b024d625817d'] = TokenFixedFee(2)
    erc20token['0x469084939d1c20fae3c73704fe963941c51be863'] = TokenFixedFee(0.7)
    erc20token['0x1bfce574deff725a3f483c334b790e25c8fa9779'] = TokenFixedFee(0)
    erc20token['0xf0f9d895aca5c8678f706fb8216fa22957685a13'] = TokenFixedFee(0.4)
    erc20token['0x75151153cfb0f3dafeb83189cf677192b00b1575'] = TokenFixedFee(1)
    erc20token['0x3882e37697e756e6a9d58387a0ee6c9e7f7a0f58'] = TokenFixedFee(2)
    erc20token['0xe717a30d8a97faa8788559d19e52d574c9593d37'] = TokenFixedFee(2)
    erc20token['0x78b1ceb872fefc6440fbdfa643f9bc533db41457'] = TokenFixedFee(3.8)
    erc20token['0xa3cb87080e68ad54d00573983d935fa85d168fde'] = TokenFixedFee(3)
    erc20token['0xb6ef90858ca39a5fbfd8b20d2e3792253965e80d'] = TokenFixedFee(1)
    erc20token['0x0fc6c0465c9739d4a42daca22eb3b2cb0eb9937a'] = TokenFixedFee(1.6)
    erc20token['0xf2ec4a773ef90c58d98ea734c0ebdb538519b988'] = TokenFixedFee(1)

    # Try different buy_count and transaction_time, trading_opened_time and fee_tier are fixed
    # Try buy_count < 30, 30 <= buy_count < 60, 60 <= buy_count < 90 or buy_count >= 90
    # Try transaction_time < trading_opened_time or transaction_time >= trading_opened_time
    erc20token['0x695d38eb4e57e0f137e36df7c1f0f2635981246b'] = TokenBuyCountTimeFee(100, 50,
                                                                                    trading_opened_time=45,
                                                                                    fee_tier=[30, 20, 10, 5])

    erc20token['0x7039cd6d7966672f194e8139074c3d5c4e6dcf65'] = TokenBuyCountTimeFee(100, 50,
                                                                                    trading_opened_time=45,
                                                                                    fee_tier=[30, 20, 10, 0.3])

    erc20token['0x33c04bed4533e31f2afb8ac4a61a48eda38c4fa0'] = TokenBuyCountTimeFee(100, 4321,
                                                                                    trading_opened_time=4320,
                                                                                    fee_tier=[30, 15, 10, 0.5])

    # Try different buy_count and transaction_time, initial_fee, final_fee and reduce_fee_at are fixed
    # Try buy_count <= reduce_fee_at and buy_count > reduce_fee_at
    erc20token['0x96e99106d9c58573171dd6c19d767d2ae7ec0435'] = TokenBuyCountFee(10, initial_fee=0, final_fee=0,
                                                                                reduce_fee_at=0)

    erc20token['0x576e2bed8f7b46d34016198911cdf9886f78bea7'] = TokenBuyCountFee(25, initial_fee=20, final_fee=1,
                                                                                reduce_fee_at=20)

    erc20token['0x36096eb8c11729fdd7685d5e1b82b17d542c38ce'] = TokenBuyCountFee(30, initial_fee=25, final_fee=5,
                                                                                reduce_fee_at=25)

    erc20token['0x240d6faf8c3b1a7394e371792a3bf9d28dd65515'] = TokenBuyCountFee(buy_count=15, initial_fee=13,
                                                                                final_fee=1, reduce_fee_at=13)

    erc20token['0xbb9b264c9f9ed7294b98ab4d83fb9f5762408390'] = TokenBuyCountFee(buy_count=8, initial_fee=25,
                                                                                final_fee=1, reduce_fee_at=5)


def get_token(addr) -> ERC20Token:
    return erc20token.get(addr, ERC20Token())


def setup_contract(evm, file_path):
    contracts = dict()
    token_contracts = dict()

    contracts["WETH"] = Contract(
        address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        revm=evm,
        abi_file_path="./abi/weth.abi"
    )

    with open(file_path) as f:
        for line in f.readlines():
            token = line[0: 42].rstrip()
            name = line[43:].rstrip()
            token_contracts[name] = Contract(
                address=token,
                revm=evm,
                abi_file_path="./abi/erc20.abi"
            )

    contracts["UNISWAP_V2_ROUTER"] = Contract(
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
        revm=evm,
        abi_file_path="./abi/uniswapv2router.abi"
    )

    return contracts, token_contracts


def check_token_fee(weth: Contract, token: Contract, router: Contract) -> CheckResult:
    check_result = CheckResult()
    current_balance = token.balanceOf(MY_ADDR)
    try:

        deadline = int(time.time()) + 600
        # WETH to token
        amount_in, amount_out = router.swapExactTokensForTokens(1000, 1, [weth.address, token.address], MY_ADDR,
                                                                deadline, caller=MY_ADDR)
    except Exception as e:
        print(f"Token {token.address} swap failed: {e}")
        check_result.has_v2_pair = False
        return check_result

    new_balance = token.balanceOf(MY_ADDR)

    actual_amount_out = new_balance - current_balance
    if actual_amount_out < amount_out:
        # TODO convert to rate and return it
        check_result.buy_fee = (amount_out - actual_amount_out) * 100 / amount_out

    # Don't transfer the full balance
    transfer_amount = int(actual_amount_out * 99 / 100)
    old_bot_balance = token.balanceOf(BOT_ADDR)
    token.transfer(BOT_ADDR, transfer_amount, caller=MY_ADDR)
    new_bot_balance = token.balanceOf(BOT_ADDR)
    actual_amount_transfer = new_bot_balance - old_bot_balance

    if actual_amount_transfer != transfer_amount:
        check_result.transfer_fee = (transfer_amount - actual_amount_transfer) * 100 / transfer_amount

    expected_after_transfer = get_token(token.address).transfer(transfer_amount)
    current_fee = round((transfer_amount - expected_after_transfer) * 100 / transfer_amount, 1)
    print("Expected transfer fee: {}%".format(current_fee))
    print("  Actual transfer fee: {}%".format(round(check_result.transfer_fee, 1)))

    # Set the threshold (% of difference) for the small difference because of integer division
    # when calculating the amount of tokens charged as fee
    if expected_after_transfer < 10_000:
        tolerance = 0.01
    elif expected_after_transfer > 1_000_000:
        tolerance = 0.0001
    else:
        tolerance = 0.001
    difference = abs(expected_after_transfer - actual_amount_transfer)
    relative_diff = difference / expected_after_transfer if expected_after_transfer > 0 else 0
    check_result.transfer_status = "WRONG_FEE" if relative_diff > tolerance else "OK"

    return check_result


def main():
    args = get_args()
    w3 = Web3(Web3.HTTPProvider(args.rpc_url))
    block = w3.eth.get_block(block_identifier="latest", full_transactions=True)  # Latest block
    block_env = BlockEnv(number=block["number"], timestamp=block["timestamp"])
    evm = EVM(fork_url=args.rpc_url, fork_block="0x" + block['parentHash'].hex(), tracing=False)
    evm.set_block_env(block_env)
    contracts, token_contracts = setup_contract(evm, args.file_path)

    contracts['WETH'].deposit(value=10 ** 19, caller=MY_ADDR)
    contracts['WETH'].approve(contracts["UNISWAP_V2_ROUTER"].address, 0x10000000000000000000, caller=MY_ADDR)

    init_token()

    for name, token in token_contracts.items():
        try:
            result = check_token_fee(contracts['WETH'], token, contracts["UNISWAP_V2_ROUTER"])
            print("==> Token {} {}".format(name, token.address))
            print(
                "    V2Pair: {}, Transfer Fee: {}%, Status: {}".format(result.has_v2_pair,
                                                                       "{:.1f}".format(result.transfer_fee),
                                                                       result.transfer_status))
            print("--" * 50)
        except Exception as e:
            print("==> Token: ", name, "got error: ", e)


if __name__ == "__main__":
    main()
