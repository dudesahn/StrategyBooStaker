import brownie
from brownie import Contract
from brownie import config
import math


def test_revoke_strategy_from_vault(
    gov,
    token,
    vault,
    whale,
    chain,
    strategy,
    amount,
    no_profit,
):

    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    # wait a day
    chain.sleep(86400)
    chain.mine(1)

    vaultAssets_starting = vault.totalAssets()
    vault_holdings_starting = token.balanceOf(vault)
    strategy_starting = strategy.estimatedTotalAssets()
    vault.revokeStrategy(strategy.address, {"from": gov})

    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    vaultAssets_after_revoke = vault.totalAssets()

    # confirm we made money, or at least that we have about the same
    # if we have any profit,
    if no_profit:
        assert math.isclose(vaultAssets_after_revoke, vaultAssets_starting, abs_tol=10)
        assert math.isclose(
            token.balanceOf(vault),
            vault_holdings_starting + strategy_starting,
            abs_tol=10,
        )
    else:
        assert vaultAssets_after_revoke >= vaultAssets_starting
        assert token.balanceOf(vault) >= vault_holdings_starting + strategy_starting

    # we may get a few wei leftover due to conversion of xBOO or similar tokens
    # if we want to 100% empty strategy, use emergency exit instead
    assert strategy.estimatedTotalAssets() < 10

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm our whale made money, or that we didn't lose more than dust
    vault.withdraw({"from": whale})
    if no_profit:
        assert math.isclose(token.balanceOf(whale), startingWhale, abs_tol=10)
    else:
        assert token.balanceOf(whale) >= startingWhale
