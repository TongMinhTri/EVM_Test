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
    def buy(self, amount):
        return amount


class TokenFixedFee(ERC20Token):
    buy_fee: float
    sell_fee: float

    def __init__(self, buy_fee):
        self.buy_fee = buy_fee

    def buy(self, amount):
        return amount - amount * self.buy_fee / 100


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

    def buy(self, amount):
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

    def buy(self, amount):
        current_fee = self.initial_fee
        if self.buy_count > self.reduce_fee_at:
            current_fee = self.final_fee

        return amount - amount * current_fee / 100


class CheckResult:
    has_v2_pair: bool = True
    buy_fee: float = 0.0
    buy_status: str = ""


def get_args() -> argparse.Namespace:
    parse = argparse.ArgumentParser()
    parse.add_argument('--rpc_url', default='http://192.168.1.58:8545')
    parse.add_argument('--file_path')
    return parse.parse_args()


def init_token():
    erc20token['0x55a8f6c6b3aa58ad6d1f26f6afeded78f32e19f4'] = TokenFixedFee(5)
    erc20token['0xfc4276d4454c2a949c2519c749f89b360e477e1b'] = TokenFixedFee(2)
    erc20token['0x84018071282d4b2996272659d9c01cb08dd7327f'] = TokenFixedFee(5)
    erc20token['0xe7ef051c6ea1026a70967e8f04da143c67fa4e1f'] = TokenFixedFee(5)
    erc20token['0xb6ef90858ca39a5fbfd8b20d2e3792253965e80d'] = TokenFixedFee(0.9)
    erc20token['0xbb9b264c9f9ed7294b98ab4d83fb9f5762408390'] = TokenFixedFee(1)
    erc20token['0x8edc6f7d2f23c10653972e611f707ce0562d61b1'] = TokenFixedFee(5)
    erc20token['0x0305f515fa978cf87226cf8a9776d25bcfb2cc0b'] = TokenFixedFee(1)
    erc20token['0x7b86f9feb2832c3c455148f33acaf59f8a4250ed'] = TokenFixedFee(3)
    erc20token['0x298d492e8c1d909d3f63bc4a36c66c64acb3d695'] = TokenFixedFee(0.5)
    erc20token['0x1e241521f4767853b376c2fe795a222a07d588ee'] = TokenFixedFee(5)
    erc20token['0x622984873c958e00aa0f004cbdd2b5301cf0b132'] = TokenFixedFee(5)
    erc20token['0xc15e520e80ce9d3bfd2f3dacc902545d60804573'] = TokenFixedFee(3)
    # erc20token['0x14fee680690900ba0cccfc76ad70fd1b95d10e16'] = TokenFixedFee(4) => Actual buy fee 0% ??
    erc20token['0x292fcdd1b104de5a00250febba9bc6a5092a0076'] = TokenFixedFee(0)
    erc20token['0xa3cb87080e68ad54d00573983d935fa85d168fde'] = TokenFixedFee(3)
    erc20token['0xccf5cf1d039f1a7b66be855b79b14a01d0a4dbd5'] = TokenFixedFee(4)
    erc20token['0xbe4d9c8c638b5f0864017d7f6a04b66c42953847'] = TokenFixedFee(3)
    erc20token['0x6dd5f0038474dc29a0adc6ad34d37b0ba53e5435'] = TokenFixedFee(3)
    erc20token['0x8c444197d64e079323a1eb8d40655910b052f85a'] = TokenFixedFee(4)
    erc20token['0xd699b83e43415b774b6ed4ce9999680f049af2ab'] = TokenFixedFee(4)
    erc20token['0x72831eebef4e3f3697a6b216e3713958210ae8cd'] = TokenFixedFee(3)
    erc20token['0x477a3d269266994f15e9c43a8d9c0561c4928088'] = TokenFixedFee(5)
    erc20token['0x5aef5bba19e6a1644805bd4f5c93c8557b87c62c'] = TokenFixedFee(4)
    erc20token['0x75151153cfb0f3dafeb83189cf677192b00b1575'] = TokenFixedFee(1)
    erc20token['0xf1df7305e4bab3885cab5b1e4dfc338452a67891'] = TokenFixedFee(3)
    erc20token['0x38e68a37e401f7271568cecaac63c6b1e19130b4'] = TokenFixedFee(0)
    erc20token['0x2056ec69ac5afaf210b851ff74de4c194fcd986e'] = TokenFixedFee(5)
    erc20token['0x7efbac35b65e73484764fd00f18e64929e782855'] = TokenFixedFee(5)
    erc20token['0x6a7eff1e2c355ad6eb91bebb5ded49257f3fed98'] = TokenFixedFee(5)
    erc20token['0x6a7eff1e2c355ad6eb91bebb5ded49257f3fed98'] = TokenFixedFee(5)
    erc20token['0xfc4237fb8357badac8d4ff3fe9038660de5da6ae'] = TokenFixedFee(0)
    erc20token['0xb369daca21ee035312176eb8cf9d88ce97e0aa95'] = TokenFixedFee(3)
    erc20token['0xae41b275aaaf484b541a5881a2dded9515184cca'] = TokenFixedFee(5)
    erc20token['0x1258d60b224c0c5cd888d37bbf31aa5fcfb7e870'] = TokenFixedFee(4)
    erc20token['0xda63feff6e6d75cd7a862cd56c625045dcf26e88'] = TokenFixedFee(5)
    erc20token['0x78b1ceb872fefc6440fbdfa643f9bc533db41457'] = TokenFixedFee(4)
    erc20token['0x0b88b6e09718a4c9fafe4acdda2b07a5fb83897b'] = TokenFixedFee(0)
    erc20token['0xe1ec350ea16d1ddaff57f31387b2d9708eb7ce28'] = TokenFixedFee(4)
    erc20token['0x1bfce574deff725a3f483c334b790e25c8fa9779'] = TokenFixedFee(0)
    erc20token['0x22994fdb3f8509cf6a729bbfa93f939db0b50d06'] = TokenFixedFee(5)
    erc20token['0x3b604747ad1720c01ded0455728b62c0d2f100f0'] = TokenFixedFee(0.2)
    erc20token['0x469084939d1c20fae3c73704fe963941c51be863'] = TokenFixedFee(0.7)
    erc20token['0x578b388528f159d026693c3c103100d36ac2ad65'] = TokenFixedFee(5)
    erc20token['0x9cf0ed013e67db12ca3af8e7506fe401aa14dad6'] = TokenFixedFee(5)
    erc20token['0x32b053f2cba79f80ada5078cb6b305da92bde6e1'] = TokenFixedFee(4)
    erc20token['0x9b4a69de6ca0defdd02c0c4ce6cb84de5202944e'] = TokenFixedFee(5)
    erc20token['0xe717a30d8a97faa8788559d19e52d574c9593d37'] = TokenFixedFee(2)
    erc20token['0x3882e37697e756e6a9d58387a0ee6c9e7f7a0f58'] = TokenFixedFee(2)
    erc20token['0x6E96394B930ffb40AfE27cBd5c0133671AD239e9'] = TokenFixedFee(2)
    erc20token['0x2390e14AaeBE7272735209ce954fc9D7053F4ba0'] = TokenFixedFee(3)
    erc20token['0xf0f9d895aca5c8678f706fb8216fa22957685a13'] = TokenFixedFee(0.4)
    erc20token['0xa2b4c0af19cc16a6cfacce81f192b024d625817d'] = TokenFixedFee(2)
    erc20token['0x030ba81f1c18d280636f32af80b9aad02cf0854e'] = TokenFixedFee(2)
    erc20token['0x14fee680690900ba0cccfc76ad70fd1b95d10e16'] = TokenFixedFee(0)
    erc20token['0x6dd5f0038474dc29a0adc6ad34d37b0ba53e5435'] = TokenFixedFee(3)
    erc20token['0x1bb9b64927e0c5e207c9db4093b3738eef5d8447'] = TokenFixedFee(3)

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
    erc20token['0x240d6faf8c3b1a7394e371792a3bf9d28dd65515'] = TokenBuyCountFee(15, initial_fee=13, final_fee=1,
                                                                                reduce_fee_at=13)

    erc20token['0x576e2bed8f7b46d34016198911cdf9886f78bea7'] = TokenBuyCountFee(25, initial_fee=20, final_fee=1,
                                                                                reduce_fee_at=20)

    erc20token['0x36096eb8c11729fdd7685d5e1b82b17d542c38ce'] = TokenBuyCountFee(30, initial_fee=25, final_fee=5,
                                                                                reduce_fee_at=25)

    erc20token['0xd7746061e569a5fb66aeac806b59f3a4fe401abb'] = TokenBuyCountFee(buy_count=25, initial_fee=23,
                                                                                final_fee=0, reduce_fee_at=23)

    erc20token['0x72fca22c6070b4cf68abdb719fa484d9ef10a73b'] = TokenBuyCountFee(buy_count=35, initial_fee=20,
                                                                                final_fee=4.5, reduce_fee_at=30)

    erc20token['0x80ee5c641a8ffc607545219a3856562f56427fe9'] = TokenBuyCountFee(buy_count=35, initial_fee=15,
                                                                                final_fee=0, reduce_fee_at=30)

    erc20token['0xc19ac322844eca09eaed37fd6b3f49f0755b60c6'] = TokenBuyCountFee(buy_count=15, initial_fee=19,
                                                                                final_fee=0, reduce_fee_at=10)

    erc20token['0x449a917fb4910cb2f57335d619e71674ffb8bc44'] = TokenBuyCountFee(buy_count=25, initial_fee=23,
                                                                                final_fee=0, reduce_fee_at=23)

    erc20token['0x7c851d60b26a4f2a6f2c628ef3b65ed282c54e52'] = TokenBuyCountFee(buy_count=45, initial_fee=23,
                                                                                final_fee=3, reduce_fee_at=40)


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

    # Check the buy fee
    current_balance = token.balanceOf(MY_ADDR)
    try:

        deadline = int(time.time()) + 600
        # WETH to token
        amount_in, amount_out = router.swapExactTokensForTokens(1000000000, 1, [weth.address, token.address], MY_ADDR,
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

    expected_after_transfer = get_token(token.address).buy(amount_out)
    current_fee = round((amount_out - expected_after_transfer) * 100 / amount_out, 1)
    print(expected_after_transfer, actual_amount_out)
    print("Expected buy fee: {}%".format(current_fee))
    print("  Actual buy fee: {}%".format(round(check_result.buy_fee, 1)))

    # Set the threshold (% of difference) for the small difference because of integer division
    # when calculating the amount of tokens charged as fee
    if expected_after_transfer < 10_000:
        tolerance = 0.01
    elif expected_after_transfer > 1_000_000:
        tolerance = 0.0001
    else:
        tolerance = 0.001
    difference = abs(expected_after_transfer - actual_amount_out)
    relative_diff = difference / expected_after_transfer if expected_after_transfer > 0 else 0
    check_result.buy_status = "WRONG_FEE" if relative_diff > tolerance else "OK"

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
                "    V2Pair: {}, Buy Fee: {}%, Buy Status: {}".format(result.has_v2_pair,
                                                                      "{:.1f}".format(result.buy_fee),
                                                                      result.buy_status))
            print("--" * 50)
        except Exception as e:
            print("==> Token: ", name, "got error: ", e)


if __name__ == "__main__":
    main()
