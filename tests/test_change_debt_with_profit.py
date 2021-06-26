import brownie
from brownie import Wei, chain
from pytest import approx

# test passes as of 21-06-26
def test_change_debt_with_profit(gov, token, vault, whale, strategy, chain, shared_setup):
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": gov})
    prev_params = vault.strategies(strategy).dict()

    currentDebt = vault.strategies(strategy)[2]
    vault.updateStrategyDebtRatio(strategy, currentDebt/2, {"from": gov})
    token.transfer(strategy, 1000e18, {"from": whale})

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400 * 9)
    chain.mine(1)

    strategy.harvest({"from": gov})
    new_params = vault.strategies(strategy).dict()
    
    assert new_params["totalGain"] > prev_params["totalGain"]
    assert new_params["totalGain"] - prev_params["totalGain"] > Wei("1_000 ether")
    assert new_params["debtRatio"] == currentDebt/2
    assert new_params["totalLoss"] == prev_params["totalLoss"]
    assert approx(vault.totalAssets() * 0.150, Wei("1 ether")) == strategy.estimatedTotalAssets()
