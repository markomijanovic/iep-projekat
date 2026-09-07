import json
import os
from pathlib import Path

from web3 import Web3


BLOCKCHAIN_URL = os.getenv(
    "BLOCKCHAIN_URL",
    "http://127.0.0.1:8545"
)

BASE_DIR = Path(__file__).resolve().parent
ABI_PATH = BASE_DIR / "build" / "InvestmentVoting.abi"
BYTECODE_PATH = BASE_DIR / "build" / "InvestmentVoting.bin"


web3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_URL))

if not web3.is_connected():
    raise RuntimeError(
        f"Cannot connect to blockchain at {BLOCKCHAIN_URL}"
    )


with ABI_PATH.open("r", encoding="utf-8") as file:
    contract_abi = json.load(file)

contract_bytecode = BYTECODE_PATH.read_text(
    encoding="utf-8"
).strip()

if not contract_bytecode.startswith("0x"):
    contract_bytecode = f"0x{contract_bytecode}"


accounts = web3.eth.accounts

director = accounts[0]
voters = accounts[1:4]


contract_factory = web3.eth.contract(
    abi=contract_abi,
    bytecode=contract_bytecode
)


def wait_for_transaction(transaction_hash):
    receipt = web3.eth.wait_for_transaction_receipt(
        transaction_hash
    )

    assert receipt.status == 1
    return receipt


def deploy_contract():
    transaction_hash = contract_factory.constructor(
        voters
    ).transact({
        "from": director
    })

    receipt = wait_for_transaction(transaction_hash)

    return web3.eth.contract(
        address=receipt.contractAddress,
        abi=contract_abi
    )


def send_transaction(function, sender):
    transaction_hash = function.transact({
        "from": sender
    })

    return wait_for_transaction(transaction_hash)


def expect_revert(action, expected_message):
    try:
        action()
    except Exception as error:
        if expected_message not in str(error):
            raise AssertionError(
                f"Expected '{expected_message}', got: {error}"
            ) from error

        print(f"Correctly rejected: {expected_message}")
        return

    raise AssertionError(
        f"Transaction should have failed: {expected_message}"
    )


print("Connected to Ganache.")
print(f"Director: {director}")
print(f"Voters: {voters}")


approved_contract = deploy_contract()

assert approved_contract.functions.director().call() == director
assert approved_contract.functions.requiredVotes().call() == 2
assert approved_contract.functions.status().call() == 0

send_transaction(
    approved_contract.functions.voteFor(),
    voters[0]
)

assert approved_contract.functions.votesFor().call() == 1
assert approved_contract.functions.status().call() == 0

send_transaction(
    approved_contract.functions.voteFor(),
    voters[1]
)

assert approved_contract.functions.votesFor().call() == 2
assert approved_contract.functions.status().call() == 1

expect_revert(
    lambda: approved_contract.functions.voteAgainst().transact({
        "from": voters[2]
    }),
    "Voting ended."
)


vetoed_contract = deploy_contract()

expect_revert(
    lambda: vetoed_contract.functions.veto().transact({
        "from": voters[0]
    }),
    "Only director."
)

send_transaction(
    vetoed_contract.functions.veto(),
    director
)

assert vetoed_contract.functions.status().call() == 3

expect_revert(
    lambda: vetoed_contract.functions.voteFor().transact({
        "from": voters[0]
    }),
    "Voting ended."
)


print("All smart contract tests passed.")