import brownie
from brownie import Contract
from brownie import config
import math


def test_migration(
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
    healthCheck,
    amount,
    strategy_name,
    pid,
    is_slippery,
    no_profit,
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

    # can we harvest an unactivated strategy? should be no
    # under our new method of using min and maxDelay, this no longer matters or works
    # tx = new_strategy.harvestTrigger(0, {"from": gov})
    # print("\nShould we harvest? Should be False.", tx)
    # assert tx == False

    # simulate 1 day of earnings
    chain.sleep(86400)
    chain.mine(1)

    # migrate our old strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    new_strategy.setHealthCheck(healthCheck, {"from": gov})
    new_strategy.setDoHealthCheck(True, {"from": gov})

    # assert that our old strategy is empty
    updated_total_old = strategy.estimatedTotalAssets()
    assert updated_total_old == 0

    # harvest to get funds back in strategy
    chain.sleep(1)
    new_strategy.harvest({"from": gov})
    new_strat_balance = new_strategy.estimatedTotalAssets()

    # confirm we made money, or at least that we have about the same
    if is_slippery and no_profit:
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

    # confirm we made money, or at least that we have about the same
    if is_slippery and no_profit:
        assert math.isclose(vaultAssets_2, startingVault, abs_tol=10)
    else:
        assert vaultAssets_2 >= startingVault

    print("\nAssets after 1 day harvest: ", vaultAssets_2)
