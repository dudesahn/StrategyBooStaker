import brownie
from brownie import Contract
from brownie import config

# test passes as of
def test_migration(gov, token, vault, dudesahn, strategist, whale, strategy, chain, strategist_ms, rewardsContract):
    # deploy our new strategy
    new_strategy = dudesahn.deploy(strategy, vault)
    total_old = strategy.estimatedTotalAssets()

    # migrate our old strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # assert that our old strategy is empty
    updated_total_old = strategy.estimatedTotalAssets()
    assert updated_total_old == 0

    # harvest to get funds back in strategy
    new_strategy.harvest({"from": gov})
    new_strat_balance = new_strategy.estimatedTotalAssets()
    assert new_strat_balance >= total_old
    
    startingVault = vault.totalAssets()
    print("\nVault starting assets with new strategy: ", startingVault)
    
    # simulate nine days of earnings to make sure we hit at least one epoch of rewards
    chain.sleep(86400*9)
    chain.mine(1)
    
    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)
    
    # Test out our migrated strategy, confirm we're making a profit
    new_strategy.harvest({"from": gov})
    vaultAssets_2 = vault.totalAssets()
    assert vaultAssets_2 > startingVault
    print("\nAssets after 1 day harvest: ", vaultAssets_2)