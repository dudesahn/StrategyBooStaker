import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_emergency_exit(gov, token, vault, whale, strategy, chain, staking, shared_setup):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": gov})

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400*9)
    chain.mine(1)
    strategy.harvest({"from": gov})

    # set emergency and exit, then confirm that the strategy has no funds
    strategy.setEmergencyExit({"from": gov})
    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() == 0
    assert staking.balanceOf(strategy, token) == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)
    
    # withdraw and confirm we made money
    vault.withdraw({"from": whale})    
    assert token.balanceOf(whale) > startingWhale