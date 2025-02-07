import unittest

from pyrevm import EVM, BlockEnv
from web3 import Web3

from contract import Contract

FORK_URL = "http://192.168.1.58:8545"
BLOCK_NUM = 20967700
ERC20_LIST = []

UNISWAP_V2_PAIRS = []
MY_ADDR = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth


class UniswapV2Test(unittest.TestCase):
    erc20_contracts: dict = dict()
    uniswap_v2_pairs: dict = dict()

    def init_contract(self):
        self.erc20_contracts["WETH"] = Contract(address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", revm=self.evm,
                                                abi_file_path="./abi/weth.abi")

        with open("./data/token.txt") as f:
            for line in f.readlines():
                token = line[0: 42].rstrip()
                name = line[43:].rstrip()
                self.erc20_contracts[name] = Contract(address=token, revm=self.evm, abi_file_path="./abi/erc20.abi")
                ERC20_LIST.append((name, token))

        for name, addr in ERC20_LIST:
            self.erc20_contracts[name] = Contract(address=addr, revm=self.evm, abi_file_path="./abi/erc20.abi")

        for name, pair_addr in UNISWAP_V2_PAIRS:
            self.uniswap_v2_pairs[name] = Contract(address=pair_addr, revm=self.evm,
                                                   abi_file_path="./abi/uniswapv2.abi")

        self.uniswap_v2_router = Contract("0x7a250d5630b4cf539739df2c5dacb4c659f2488d", revm=self.evm,
                                          abi_file_path="./abi/uniswapv2router.abi")

        self.uniswap_v2_factory = Contract("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f", revm=self.evm,
                                           abi_file_path="./abi/uniswapv2factory.abi")

    def setUp(self) -> None:
        self.w3 = Web3(Web3.HTTPProvider(FORK_URL))
        block = self.w3.eth.get_block(block_identifier=BLOCK_NUM, full_transactions=True)
        self.evm = EVM(fork_url=FORK_URL, fork_block="0x" + block['parentHash'].hex(), tracing=False)
        self.init_contract()
        return super().setUp()

    def init_block(self, block_number):
        block = self.w3.eth.get_block(block_identifier=block_number, full_transactions=True)
        blockEnv = BlockEnv(number=block["number"], timestamp=block["timestamp"])
        self.evm.set_block_env(blockEnv)
        self.evm.get_balance(MY_ADDR)
        self.erc20_contracts['WETH'].deposit(value=10 ** 19, caller=MY_ADDR)
        return block

    def test_transfer(self):
        balance = self.erc20_contracts['WETH'].balanceOf(MY_ADDR)
        print(f"Balance: {balance}")
        count = 1

        self.init_block(BLOCK_NUM)
        self.erc20_contracts['WETH'].approve(self.uniswap_v2_router.address, 0x10000000000000000000, caller=MY_ADDR)

        # token swap and transfer
        error = []
        transfer_fee = []
        no_transfer_fee = []
        no_pair_with_eth = []
        receive_fee = []
        to_addr = "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB"
        self.init_block(BLOCK_NUM)
        self.erc20_contracts['WETH'].approve(self.uniswap_v2_router.address, 0x10000000000000000000, caller=MY_ADDR)
        for name, addr in ERC20_LIST:
            print("{}. Token Name: {}".format(count, name))
            count += 1
            try:
                old_balance = self.erc20_contracts[name].balanceOf(MY_ADDR)
                amount_in, amount_out = self.uniswap_v2_router.swapExactTokensForTokens(1000000000, 1, [
                    self.erc20_contracts['WETH'].address, addr], MY_ADDR, 1734284800, caller=MY_ADDR)
            except:
                print("===> Error swapping WETH to {}".format(name))
                no_pair_with_eth.append((name, addr))
            else:
                print("Swap {} WETH to {} {}".format(amount_in, amount_out, name))
                new_balance = self.erc20_contracts[name].balanceOf(MY_ADDR)
                lost_tokens_swap = amount_out - (new_balance - old_balance)
                fee_swap = round(lost_tokens_swap / amount_out * 100, 1)
                print("Number of lost tokens after swapping: {}".format(lost_tokens_swap))
                print("Swap fee: {}%".format(fee_swap))

                if lost_tokens_swap > 0:
                    print("===> Token {} has a receive fee".format(name))
                    receive_fee.append((name, addr, fee_swap))
                    amount_out = new_balance - old_balance
                if amount_out <= 0:
                    continue
                try:
                    self.erc20_contracts[name].transfer(to_addr, amount_out, caller=MY_ADDR)
                    balance = self.erc20_contracts[name].balanceOf(to_addr)
                    print("Transfer {} tokens".format(amount_out))
                    lost_tokens_transfer = amount_out - balance
                    fee_transfer = round(lost_tokens_transfer / amount_out * 100, 1)
                    print("Number of lost tokens after transferring: {}".format(lost_tokens_transfer))
                    print("Transfer fee: {}%".format(fee_transfer))
                    if lost_tokens_transfer > 0:
                        print("===> Token {} applies a transfer fee".format(name))
                        transfer_fee.append((name, addr, fee_transfer))
                    elif lost_tokens_transfer == 0:
                        print("===> Token {} doesn't apply a transfer fee".format(name))
                        no_transfer_fee.append((name, addr))
                except:
                    error.append((name, addr))
                    print("===> Error transferring {}".format(name))

            print("--" * 30)

        # Export receive_fee to a text file
        with open("receive_fee_results.txt", "w") as f:
            for token in receive_fee:
                f.write(f"{token[2]}%, {token[1]}, {token[0]}\n")

        print("Tokens that apply a transfer fee: ", transfer_fee)
        print("Number of tokens that apply a transfer fee: ", len(transfer_fee))
        # print("Tokens that don't apply a transfer fee: ", [item[0] for item in no_transfer_fee])
        print("Number of tokens don't that apply a transfer fee: ", len(no_transfer_fee))

        print("Tokens that have a receive fee: ", receive_fee)
        print("Number of tokens that have a receive fee: ", len(receive_fee))

        # print("Number of tokens with no pair against ETH: ", len(no_pair_with_eth))  # print("Number of tokens that have errors during transfers: ", len(error))


if __name__ == "__main__":
    unittest.main()
