import brownie
from brownie import Wei, accounts, Contract, config

# test passes as of 21-06-26
def test_cloning(
    gov,
    token,
    vault,
    dudesahn,
    strategist,
    whale,
    strategy,
    keeper,
    rewards,
    chain,
    strategist_ms,
    staking,
    shared_setup,
    Strategy,
    rewardscontract
):

    # Shouldn't be able to call initialize again
    with brownie.reverts():
        strategy.initialize(
            vault,
            strategist,
            rewards,
            keeper,
            rewardscontract,
            {"from": gov},
        )
    
    ## clone our strategy
    tx = strategy.clone(vault, strategist, rewards, keeper, rewardscontract)
    newStrategy = Strategy.at(tx.return_value)
    
    # Shouldn't be able to call initialize again
    with brownie.reverts():
        newStrategy.initialize(
            vault,
            strategist,
            rewards,
            keeper,
            rewardscontract,
            {"from": gov},
        )

    vault.revokeStrategy(strategy, {"from": gov})
    vault.addStrategy(newStrategy, 1500, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    user_start_balance = token.balanceOf(whale)
    before_pps = vault.pricePerShare()
    token.approve(vault.address, 1000e18, {"from": whale})
    vault.deposit(1000e18, {"from": whale})

    newStrategy.harvest({"from": gov})

    # simulate 9 days of earnings
    chain.sleep(86400 * 9)
    chain.mine(1)

    # Get profits and withdraw
    newStrategy.harvest({"from": gov})
    chain.sleep(3600 * 10)
    chain.mine(1)

    vault.withdraw({"from": whale})
    user_end_balance = token.balanceOf(whale)

    assert vault.pricePerShare() > before_pps
    assert user_end_balance > user_start_balance
