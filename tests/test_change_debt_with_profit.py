import brownie
from brownie import Wei, chain
from pytest import approx

# test passes as of 21-06-26
def test_change_debt_with_profit(
    gov, token, vault, dudesahn, strategist, whale, strategy, chain, rewardscontract,
):

    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(10000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400 * 9)
    chain.mine(1)

    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.sleep(60 * 60 * 10)
    chain.mine(1)

    prev_params = vault.strategies(strategy).dict()

    currentDebt = vault.strategies(strategy)[2]
    vault.updateStrategyDebtRatio(strategy, currentDebt / 2, {"from": gov})
    token.transfer(strategy, 10000e18, {"from": whale})

    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400 * 9)
    chain.mine(1)

    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.sleep(60 * 60 * 10)
    chain.mine(1)
    new_params = vault.strategies(strategy).dict()

    assert new_params["totalGain"] > prev_params["totalGain"]
    assert new_params["totalGain"] - prev_params["totalGain"] > Wei("1_000 ether")
    assert new_params["debtRatio"] == currentDebt / 2
    assert new_params["totalLoss"] == prev_params["totalLoss"]
    assert (
        approx(vault.totalAssets() * 0.150, Wei("1 ether"))
        == strategy.estimatedTotalAssets()
    )
