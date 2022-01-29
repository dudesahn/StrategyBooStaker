import brownie
from brownie import Contract
from brownie import config
import math


def test_protocol_drains_balance(
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
    masterchef,
    xboo,
):
    ## deposit to the vault after approving.
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # send away all funds from the masterchef itself
    to_send = xboo.balanceOf(masterchef)
    print("Balance of Vault", to_send)
    xboo.transfer(gov, to_send, {"from": masterchef})
    assert xboo.balanceOf(masterchef) == 0
    assert vault.strategies(strategy)[2] == 10000

    # turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})

    # revoke the strategy to get our funds back out
    vault.revokeStrategy(strategy, {"from": gov})
    chain.sleep(1)
    tx_1 = strategy.harvest({"from": gov})
    chain.sleep(1)
    print("\nThis was our vault report:", tx_1.events["Harvested"])

    # we can also withdraw from an empty vault as well
    tx = vault.withdraw(amount, whale, 10000, {"from": whale})
    endingWhale = token.balanceOf(whale)
    print(
        "This is how much our whale lost:",
        (startingWhale - endingWhale) / (10 ** token.decimals()),
    )


def test_protocol_half_rekt(
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
    masterchef,
    xboo,
):
    ## deposit to the vault after approving.
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # send away all funds from the masterchef itself
    to_send = xboo.balanceOf(masterchef) / 2
    starting_chef = xboo.balanceOf(masterchef)
    print("Balance of Vault", to_send)
    xboo.transfer(gov, to_send, {"from": masterchef})
    assert xboo.balanceOf(masterchef) < starting_chef

    # turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})

    # revoke the strategy to get our funds back out
    vault.revokeStrategy(strategy, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(1)
    print("\nThis was our vault report:", tx.events["Harvested"])

    # we can also withdraw from an empty vault as well
    vault.withdraw(amount, whale, 10000, {"from": whale})
    endingWhale = token.balanceOf(whale)
    print(
        "This is how much our whale lost:",
        (startingWhale - endingWhale) / (10 ** token.decimals()),
    )


def test_protocol_dumb_masterchef_dev(
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
    masterchef,
    accounts,
    xboo,
):
    ## deposit to the vault after approving.
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # normal operation
    chain.sleep(86400)
    chain.mine(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    tx_1 = strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.mine(1)

    # try and add a duplicate pool to bork the contract. since our strategist deployed it, he is the owner.
    owner = accounts.at("0x95478C4F7D22D1048F46100001c2C69D2BA57380", force=True)
    with brownie.reverts():
        masterchef.add(
            69, xboo, chain.time(), chain.time() + 696969, owner, {"from": owner}
        )

    # set rewards as high as we can
    masterchef.setRewardPerSecond(pid, 2 ** 256 - 1, {"from": owner})
    chain.sleep(86400)
    chain.mine(1)

    # we need to use emergency withdraw and emergency exit if this happens
    strategy.emergencyWithdraw({"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.setEmergencyExit({"from": gov})
    tx_2 = strategy.harvest({"from": gov})
    chain.sleep(1)
    print("\nThis was our vault report:", tx_2.events["Harvested"])

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})


def test_protocol_dumb_masterchef_dev_pt_2(
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
    masterchef,
    accounts,
    xboo,
):
    ## deposit to the vault after approving.
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # normal operation
    chain.sleep(86400)
    chain.mine(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    tx_1 = strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.mine(1)

    # try and add a duplicate pool to bork the contract. since our strategist deployed it, he is the owner.
    owner = accounts.at("0x95478C4F7D22D1048F46100001c2C69D2BA57380", force=True)
    with brownie.reverts():
        masterchef.add(
            69, xboo, chain.time(), chain.time() + 696969, owner, {"from": owner}
        )

    # check that we're okay if the owner turns back on user limit
    masterchef.changePoolUserLimitEndTime(pid, 2 ** 256 - 1, {"from": owner})

    # this means the most anyone can deposit in any pool is 1 wei. we can't do 0 because otherwise the masterchef will skip this check
    masterchef.changeUserLimit(1, {"from": owner})
    chain.sleep(86400)
    chain.mine(1)

    # we need to emergency exit if this happens so we don't try to redeposit any
    strategy.setEmergencyExit({"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    tx_2 = strategy.harvest({"from": gov})
    chain.sleep(1)
    print("\nThis was our vault report:", tx_2.events["Harvested"])

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})


def test_protocol_turn_off_rewards(
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
    masterchef,
    accounts,
    xboo,
):
    ## deposit to the vault after approving.
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # normal operation
    chain.sleep(86400)
    chain.mine(1)
    strategy.setDoHealthCheck(False, {"from": gov})

    # check that we can still withdraw just fine if owner sets rewards to 0
    owner = accounts.at("0x95478C4F7D22D1048F46100001c2C69D2BA57380", force=True)
    masterchef.setRewardPerSecond(pid, 0, {"from": owner})
    tx_1 = strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.mine(1)
    tx_2 = strategy.harvest({"from": gov})
    chain.sleep(1)
    print("\nThis was our vault report:", tx_2.events["Harvested"])

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})


def test_withdraw_when_done_rewards_over(
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
    masterchef,
):
    ## deposit to the vault after approving.
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # turn off health check since we're doing weird shit
    strategy.setDoHealthCheck(False, {"from": gov})

    # normal operation
    chain.sleep(60 * 86400)
    chain.mine(1)
    tx_1 = strategy.harvest({"from": gov})
    chain.sleep(86400)
    chain.mine(1)

    # check if we can still withdraw normally if this happened, let's revoke
    vault.revokeStrategy(strategy, {"from": gov})
    chain.sleep(1)
    tx_2 = strategy.harvest({"from": gov})
    chain.sleep(1)
    print("\nThis was our vault report:", tx_2.events["Harvested"])

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": whale})
