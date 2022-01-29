import brownie
from brownie import Contract
from brownie import config
import math

# test passes as of 21-06-26
def test_emergency_shutdown_from_vault(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    amount,
    is_slippery,
    no_profit,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate one day of earnings
    chain.sleep(86400)

    chain.mine(1)
    strategy.harvest({"from": gov})

    # simulate one day of earnings
    chain.sleep(86400)

    # set emergency and exit, then confirm that the strategy has no funds
    vault.setEmergencyShutdown(True, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert math.isclose(strategy.estimatedTotalAssets(), 0, abs_tol=5)

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm our whale made money, or that we didn't lose more than dust
    vault.withdraw({"from": whale})
    if is_slippery and no_profit:
        assert math.isclose(token.balanceOf(whale), startingWhale, abs_tol=10)
    else:
        assert token.balanceOf(whale) >= startingWhale
