import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-05-20
def test_emergency_exit(gov, token, vault, dudesahn, strategist, whale, strategy, chain, strategist_ms, rewardsContract):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": dudesahn})

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400*9)
    chain.mine(1)

    # confirm that we will claim rewards on withdrawal, set emergency and exit, then confirm that the strategy has no funds
    strategy.setClaimRewards(True, {"from": gov})
    strategy.setEmergencyExit({"from": gov})
    strategy.harvest({"from": dudesahn})
    assert strategy.estimatedTotalAssets() == 0
    assert rewardsContract.balanceOf(strategy) == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)
    
    # withdraw and confirm we made money
    vault.withdraw({"from": whale})    
    assert token.balanceOf(whale) > startingWhale