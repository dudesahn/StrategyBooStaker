import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_simple_harvest(
    gov,
    token,
    vault,
    dudesahn,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    staking,
    shared_setup,
):
    ## clone our strategy for the link vault
    link_vault = Contract("0x671a912C10bba0CFA74Cfc2d6Fba9BA1ed9530B2")
    link_farming = Contract("0x1f926b0924f64175dB5d10f652628e7849d0185e")
    link = Contract("0x514910771AF9Ca656af840dff83E8264EcF986CA")
    _newStrategy = newStrategy.clone(link_vault, link_farming, dudesahn, dudesahn, dudesahn)
    newStrategy = Contract(_newStrategy)
    
    # attach our new strategy
    link_vault.setManagementFee(0, {"from": gov})
    link_vault.updateStrategyDebtRatio("0x328C39cD6cFD7DA6E64a5efdEF23CD63892f76A0", 0)
    link_vault.addStrategy(strategy, 1500, 0, 2 ** 256 - 1, 1000, {"from": gov})
    link.approve(link_vault, 2 ** 256 - 1, {"from": whale})
    link_vault.deposit(1000e18, {"from": whale})
    newStrategy.harvest({"from": gov})
    newWhale = link.balanceOf(whale)

    # harvest, store asset amount
    newStrategy.harvest({"from": gov})
    old_assets_dai = link_vault.totalAssets()
    assert old_assets_dai > 0
    assert link.balanceOf(strategy) == 0
    assert newStrategy.estimatedTotalAssets() > 0
    assert link_farming.balanceOf(strategy, token) > 0
    print("\nStarting Assets: ", old_assets_dai / 1e18)
    print("\nAssets Staked: ", link_farming.balanceOf(strategy, token) / 1e18)

    # simulate 9 days of earnings
    chain.sleep(86400 * 9)
    chain.mine(1)

    # harvest after a day, store new asset amount
    newStrategy.harvest({"from": gov})
    new_assets_dai = link_vault.totalAssets()
    # we can't use strategyEstimated Assets because the profits are sent to the vault
    assert new_assets_dai >= old_assets_dai
    print("\nAssets after 2 days: ", new_assets_dai / 1e18)

    # Display estimated APR based on the two days before the pay out
    print(
        "\nEstimated SUSHI APR: ",
        "{:.2%}".format(
            ((new_assets_dai - old_assets_dai) * (365 / 9))
            / (strategy.estimatedTotalAssets())
        ),
    )

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money
    link_vault.withdraw({"from": whale})
    assert link.balanceOf(whale) >= startingWhale
