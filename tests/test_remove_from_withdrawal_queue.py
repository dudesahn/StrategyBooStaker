import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_remove_from_withdrawal_queue(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    staking,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400 * 9)
    chain.mine(1)
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    before = strategy.estimatedTotalAssets()

    # set emergency and exit, then confirm that the strategy has no funds
    vault.removeStrategyFromQueue(strategy, {"from": gov})
    after = strategy.estimatedTotalAssets()
    assert before == after

    zero = "0x0000000000000000000000000000000000000000"
    assert vault.withdrawalQueue(0) == zero
