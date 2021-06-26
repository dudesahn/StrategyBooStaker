import brownie
from brownie import Contract
from brownie import config

def test_emergency_withdraw(gov, token, vault, dudesahn, strategist, whale, strategy, chain, strategist_ms, rewardsContract, staking):
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
    assert staking.balanceOf(strategy) == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)
    
    # withdraw and confirm we didn't lose money
    vault.withdraw({"from": whale})    
    assert token.balanceOf(whale) >= startingWhale