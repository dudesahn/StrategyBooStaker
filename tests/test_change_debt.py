import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_change_debt(gov, token, vault, dudesahn, strategist, whale, strategy, chain, shared_setup, rewardscontract):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    newWhale = token.balanceOf(whale)
    starting_assets = vault.totalAssets()

    # evaluate our current total assets
    startingLive = strategy.estimatedTotalAssets()

    # debtRatio is in BPS (aka, max is 10,000, which represents 100%), and is a fraction of the funds that can be in the strategy
    currentDebt = 10000
    vault.updateStrategyDebtRatio(strategy, currentDebt/2, {"from": gov})
    strategy.harvest({"from": gov})

    assert strategy.estimatedTotalAssets() <= (startingLive)

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400*9)
    chain.mine(1)

    # set DebtRatio back to 100%
    vault.updateStrategyDebtRatio(strategy, currentDebt, {"from": gov})
    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() >= startingLive

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)
    
    # withdraw and confirm we made money or at least got it back
    vault.withdraw({"from": whale})    
    assert token.balanceOf(whale) >= startingWhale 
