import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_emergency_shutdown_from_vault(
    gov, token, vault, whale, strategy, chain, staking,
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

    # set emergency and exit, then confirm that the strategy has no funds
    vault.setEmergencyShutdown(True, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0
    assert staking.balanceOf(strategy, token) == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) > startingWhale
