import brownie
from brownie import Contract
from brownie import config

def test_emergency_withdraw(gov, token, vault, dudesahn, strategist, whale, strategy, chain, strategist_ms, rewardsContract):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": dudesahn})

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400 * 9)
    chain.mine(1)

    strategy.setEmergencyExit({"from": gov})
    strategy.emergencyWithdraw({"from": gov})

    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() == 0
    assert rewardsContract.balanceOf(strategy) == 0

    # sweep this from the strategy with gov and wait until we can figure out how to unwrap them
    strategy.sweep(cvxIBDeposit, {"from": gov})
    assert cvxIBDeposit.balanceOf(gov) > 0