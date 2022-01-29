import brownie
from brownie import Contract
from brownie import config
import math


def test_odds_and_ends(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    pid,
    StrategyBooStaker,
    amount,
    strategy_name,
    is_slippery,
):

    ## deposit to the vault after approving. turn off health check before each harvest since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # send away all funds, will need to alter this based on strategy
    masterchef = Contract("0x2352b745561e7e6FCD03c093cE7220e3e126ace0")
    strategy_staked = strategy.xbooStakedInMasterchef()
    masterchef.withdraw(pid, strategy_staked, {"from": strategy})
    xboo = Contract("0xa48d959AE2E88f1dAA7D5F611E01908106dE7598")
    to_send = xboo.balanceOf(strategy)
    print("xBoo Balance of Vault", to_send)
    xboo.transfer(gov, to_send, {"from": strategy})
    assert strategy.estimatedTotalAssets() == 0

    chain.sleep(86400 * 4)  # fast forward so our min delay is passed
    chain.mine(1)

    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})

    # we can try to migrate too, lol
    # deploy our new strategy
    new_strategy = strategist.deploy(
        StrategyBooStaker,
        vault,
        pid,
        strategy_name,
    )
    total_old = strategy.estimatedTotalAssets()

    # migrate our old strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # assert that our old strategy is empty
    updated_total_old = strategy.estimatedTotalAssets()
    assert updated_total_old == 0

    # harvest to get funds back in strategy
    chain.sleep(1)
    chain.mine(1)
    new_strategy.harvest({"from": gov})
    new_strat_balance = new_strategy.estimatedTotalAssets()
    # confirm we made money, or at least that we have about the same
    if is_slippery:
        assert math.isclose(new_strat_balance, total_old, abs_tol=10)
    else:
        assert new_strat_balance >= total_old

    startingVault = vault.totalAssets()
    print("\nVault starting assets with new strategy: ", startingVault)

    # simulate one day of earnings
    chain.sleep(86400)
    chain.mine(1)

    # Test out our migrated strategy, confirm we're making a profit
    new_strategy.harvest({"from": gov})
    vaultAssets_2 = vault.totalAssets()
    assert vaultAssets_2 >= startingVault
    print("\nAssets after 1 day harvest: ", vaultAssets_2)

    # check our oracle
    one_eth_in_want = strategy.ethToWant(1e18)
    print("This is how much want one ETH buys:", one_eth_in_want)
    zero_eth_in_want = strategy.ethToWant(0)

    # check our views
    strategy.apiVersion()
    strategy.isActive()

    # tend stuff
    chain.sleep(1)
    strategy.tend({"from": gov})
    chain.sleep(1)
    strategy.tendTrigger(0, {"from": gov})


def test_odds_and_ends_2(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    pid,
    amount,
):

    ## deposit to the vault after approving. turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # send away all funds, will need to alter this based on strategy
    masterchef = Contract("0x2352b745561e7e6FCD03c093cE7220e3e126ace0")
    strategy_staked = strategy.xbooStakedInMasterchef()
    masterchef.withdraw(pid, strategy_staked, {"from": strategy})
    xboo = Contract("0xa48d959AE2E88f1dAA7D5F611E01908106dE7598")
    to_send = xboo.balanceOf(strategy)
    print("xBoo Balance of Vault", to_send)
    xboo.transfer(gov, to_send, {"from": strategy})
    assert strategy.estimatedTotalAssets() == 0

    strategy.setEmergencyExit({"from": gov})

    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})


def test_odds_and_ends_migration(
    StrategyBooStaker,
    gov,
    token,
    vault,
    guardian,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    amount,
    strategy_name,
    pid,
):

    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # deploy our new strategy
    new_strategy = strategist.deploy(
        StrategyBooStaker,
        vault,
        pid,
        strategy_name,
    )
    total_old = strategy.estimatedTotalAssets()

    # sleep for a dau
    chain.sleep(86400)

    # migrate our old strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # assert that our old strategy is empty
    updated_total_old = strategy.estimatedTotalAssets()
    assert updated_total_old == 0

    # harvest to get funds back in strategy
    chain.sleep(1)
    new_strategy.harvest({"from": gov})
    new_strat_balance = new_strategy.estimatedTotalAssets()

    # confirm we made money, or at least that we have about the same
    assert new_strat_balance >= total_old or math.isclose(
        new_strat_balance, total_old, abs_tol=5
    )

    startingVault = vault.totalAssets()
    print("\nVault starting assets with new strategy: ", startingVault)

    # simulate one day of earnings
    chain.sleep(86400)
    chain.mine(1)

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # Test out our migrated strategy, confirm we're making a profit
    new_strategy.harvest({"from": gov})
    vaultAssets_2 = vault.totalAssets()
    # confirm we made money, or at least that we have about the same
    assert vaultAssets_2 >= startingVault or math.isclose(
        vaultAssets_2, startingVault, abs_tol=5
    )
    print("\nAssets after 1 day harvest: ", vaultAssets_2)


def test_odds_and_ends_liquidatePosition(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    amount,
    no_profit,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    newWhale = token.balanceOf(whale)

    # harvest, store asset amount
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    old_assets = vault.totalAssets()
    assert old_assets > 0
    assert token.balanceOf(strategy) == 0
    assert strategy.estimatedTotalAssets() > 0
    print("\nStarting Assets: ", old_assets / 1e18)

    # simulate one day of earnings
    chain.sleep(86400)
    chain.mine(1)

    # harvest, store new asset amount
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    new_assets = vault.totalAssets()
    # confirm we made money, or at least that we have about the same
    assert new_assets >= old_assets or math.isclose(new_assets, old_assets, abs_tol=5)
    print("\nAssets after 1 day: ", new_assets / 1e18)

    # Display estimated APR
    print(
        "\nEstimated APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365)) / (strategy.estimatedTotalAssets())
        ),
    )

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # transfer funds to our strategy so we have enough for our withdrawal
    token.transfer(strategy, amount, {"from": whale})

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw({"from": whale})
    if no_profit:
        assert math.isclose(token.balanceOf(whale) + amount, startingWhale, abs_tol=10)
    else:
        assert token.balanceOf(whale) + amount >= startingWhale


def test_odds_and_ends_rekt(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    pid,
    amount,
):
    ## deposit to the vault after approving. turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # send away all funds, will need to alter this based on strategy
    masterchef = Contract("0x2352b745561e7e6FCD03c093cE7220e3e126ace0")
    strategy_staked = strategy.xbooStakedInMasterchef()
    masterchef.withdraw(pid, strategy_staked, {"from": strategy})
    xboo = Contract("0xa48d959AE2E88f1dAA7D5F611E01908106dE7598")
    to_send = xboo.balanceOf(strategy)
    print("xBoo Balance of Vault", to_send)
    xboo.transfer(gov, to_send, {"from": strategy})
    assert strategy.estimatedTotalAssets() == 0
    assert vault.strategies(strategy)[2] == 10000
    print("Strategy Total Debt, this should be >0:", vault.strategies(strategy)[6])
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})

    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(1)

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})


# goal of this one is to hit a withdraw when we don't have any staked assets
def test_odds_and_ends_liquidate_rekt(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    pid,
    amount,
):
    ## deposit to the vault after approving. turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # send away all funds, will need to alter this based on strategy
    masterchef = Contract("0x2352b745561e7e6FCD03c093cE7220e3e126ace0")
    strategy_staked = strategy.xbooStakedInMasterchef()
    masterchef.withdraw(pid, strategy_staked, {"from": strategy})
    xboo = Contract("0xa48d959AE2E88f1dAA7D5F611E01908106dE7598")
    to_send = xboo.balanceOf(strategy)
    print("xBoo Balance of Vault", to_send)
    xboo.transfer(gov, to_send, {"from": strategy})
    assert strategy.estimatedTotalAssets() == 0

    # we can also withdraw from an empty vault as well, but make sure we're okay with losing 100%
    vault.withdraw(amount, whale, 10000, {"from": whale})


def test_weird_reverts_and_trigger(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    other_vault_strategy,
    amount,
):

    # only vault can call this
    with brownie.reverts():
        strategy.migrate(strategist_ms, {"from": gov})

    # can't migrate to a different vault
    with brownie.reverts():
        vault.migrateStrategy(strategy, other_vault_strategy, {"from": gov})

    # can't withdraw from a non-vault address
    with brownie.reverts():
        strategy.withdraw(1e18, {"from": gov})

    # can't do health check with a non-health check contract
    with brownie.reverts():
        strategy.withdraw(1e18, {"from": gov})


# this one makes sure our harvestTrigger doesn't trigger when we don't have assets in the strategy
def test_odds_and_ends_inactive_strat(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    amount,
):
    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    ## move our funds out of the strategy
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    # sleep for a day since univ3 is weird
    chain.sleep(86400)
    strategy.harvest({"from": gov})

    # we shouldn't harvest empty strategies
    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be false.", tx)
    assert tx == False
