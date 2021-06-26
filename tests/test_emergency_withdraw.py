import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_emergency_withdraw(gov, token, vault, whale, strategy, chain, strategist_ms, shared_setup, staking):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": gov})

    # simulate a day of waiting
    chain.sleep(86400)
    chain.mine(1)
    
    # withdraw
    vault.withdraw(1e18, {"from": whale}) 

    # simulate 11 weeks so we can emergency withdraw
    chain.sleep(86400 * 7 * 11)
    chain.mine(1)

    strategy.setEmergencyExit({"from": gov})
    strategy.emergencyWithdraw({"from": gov})
    strategy.harvest({"from": gov})
    
    assert strategy.estimatedTotalAssets() == 0
    assert staking.balanceOf(strategy, token) == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)
    
    # withdraw and confirm we didn't lose money
    vault.withdraw({"from": whale})    
    assert token.balanceOf(whale) >= startingWhale