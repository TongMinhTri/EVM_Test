import json
from pyrevm import EVM
from abi import ABIFunction, ContractABI, parse_json_abi

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

class Contract:
    def __init__(
        self,
        address: str,
        revm: EVM,
        abi: dict = None,
        abi_file_path: str = None,
        contract_abi: "ContractABI" = None,
        caller: str = ZERO_ADDRESS,
        fork_url="",
        block_number=0,
    ):
        self.address = address
        self.caller = caller
        self.revm = revm

        if contract_abi:
            self.abi = contract_abi
        else:
            self.abi = self._load_abi(abi, abi_file_path)

    def __getattr__(self, attribute):
        for func in self.abi.functions:
            if func.name == attribute or func.selector == attribute:
                return lambda *args, **kwargs: self.call_function(func, args, kwargs)
        raise AttributeError(f"No function named {attribute} in contract ABI")

    def __getitem__(self, identifier):
        identifier = identifier.lstrip("0x")
        for func in self.abi.functions:
            if identifier in [func.name, func.get_selector().hex()]:
                return lambda *args, **kwargs: self.call_function(func, args, kwargs)
        raise AttributeError(
            f"No function with identifier {identifier} in contract ABI"
        )

    def _load_abi(self, abi: dict = None, file_path: dict = None) -> ContractABI:
        if not abi and not file_path:
            raise ValueError("Either abi or abi_file_path must be provided")

        if file_path:
            with open(file_path, "r") as file:
                abi = json.load(file)

        return parse_json_abi(abi)

    def call_function(self, func: ABIFunction, args: tuple, kwargs: dict = {}):
        value = kwargs.get("value", 0)
        caller = kwargs.get("caller", self.caller)
        ignore_outputs = kwargs.get("ignore_outputs", False)
        calldata = func.encode_inputs(args)

        if not func.payable and value > 0:
            raise ValueError("Cannot send value to a non-payable function")

        if not func.constant and caller == ZERO_ADDRESS:
            raise ValueError("Cannot call a non-constant function without a caller")

        raw_output = self.revm.message_call(
            caller=caller,
            to=self.address,
            calldata=calldata,
            value=value,
            is_static=func.constant,
        )

        if not ignore_outputs:
            return func.decode_outputs(raw_output)

    def balance(self):
        return self.revm.get_balance(self.address)