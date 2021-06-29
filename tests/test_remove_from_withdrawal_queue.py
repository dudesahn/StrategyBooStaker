import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_remove_from_withdrawal_queue(
    gov, token, vault, whale, strategy, chain, staking, shared_setup
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": gov})

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400 * 9)
    chain.mine(1)
    strategy.harvest({"from": gov})
    before = strategy.estimatedTotalAssets()

    # set emergency and exit, then confirm that the strategy has no funds
    vault.removeStrategyFromQueue({"from": gov})
    after = strategy.estimatedTotalAssets()
    assert before == after
    
    # this should revert
    strategy.harvest({"from": gov})

    # this should also revert
    vault.withdraw({"from": whale})